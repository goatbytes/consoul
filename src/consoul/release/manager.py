"""Release workflow orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from pathlib import Path

from consoul.release import changelog, gira, git_ops, github, quality, version


class ReleaseResult(str, Enum):
    """Result of release operation."""

    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ReleaseConfig:
    """Configuration for release workflow."""

    version_bump: version.VersionBump = version.VersionBump.AUTO
    skip_tests: bool = False
    skip_docs: bool = False
    dry_run: bool = False
    force: bool = False
    main_branch: str = "main"
    develop_branch: str = "develop"
    create_gira_ticket: bool = True
    create_github_release: bool = True


class ReleaseManager:
    """Manages the complete release workflow."""

    def __init__(self, config: ReleaseConfig | None = None):
        """
        Initialize release manager.

        Args:
            config: Release configuration
        """
        self.config = config or ReleaseConfig()
        self.ticket_id: str | None = None
        self.tag_created: bool = False
        self.version_str: str = ""

    def verify_preconditions(self) -> tuple[bool, str]:
        """
        Verify all preconditions for release.

        Returns:
            Tuple of (success, error_message)
        """
        # Check clean working tree
        if not git_ops.is_clean_working_tree():
            return False, "Working tree has uncommitted changes"

        # Check on develop branch
        current_branch = git_ops.get_current_branch()
        if current_branch != self.config.develop_branch:
            return (
                False,
                f"Must be on {self.config.develop_branch} branch (currently on {current_branch})",
            )

        # Check synced with remote
        if not git_ops.is_branch_synced_with_remote(self.config.develop_branch):
            return False, f"{self.config.develop_branch} branch not synced with remote"

        return True, ""

    def determine_version(self) -> tuple[version.Version, version.VersionBump]:
        """
        Determine next version number.

        Returns:
            Tuple of (version, bump_type)
        """
        return version.determine_next_version(bump_type=self.config.version_bump)

    def update_files(self, new_version: version.Version) -> None:
        """
        Update version in project files.

        Args:
            new_version: New version number
        """
        version_str = str(new_version)

        # Update pyproject.toml
        pyproject_path = Path("pyproject.toml")
        content = pyproject_path.read_text(encoding="utf-8")

        # Replace both [project] and [tool.poetry] versions
        content = content.replace(
            'version = "', f'version = "{version_str}" # PLACEHOLDER\nversion = "'
        )
        content = content.replace(" # PLACEHOLDER\n", "")

        # Proper replacement
        import re

        content = re.sub(
            r'^version\s*=\s*"[^"]+"',
            f'version = "{version_str}"',
            content,
            flags=re.MULTILINE,
        )

        pyproject_path.write_text(content, encoding="utf-8")

    def generate_changelog(self, new_version: version.Version) -> str:
        """
        Generate and update CHANGELOG.

        Args:
            new_version: New version number

        Returns:
            Generated changelog section
        """
        section = changelog.generate_changelog_section(str(new_version), date.today())

        if not self.config.dry_run:
            changelog.update_changelog(str(new_version), section)

        return section

    def run_quality_checks(self) -> bool:
        """
        Run all quality checks.

        Returns:
            True if all checks passed
        """
        results = quality.run_all_checks(skip_tests=self.config.skip_tests)

        all_passed = all(r.passed for r in results)

        return all_passed

    def execute_release(self) -> tuple[ReleaseResult, str]:
        """
        Execute the complete release workflow.

        Returns:
            Tuple of (result, message)
        """
        try:
            # 1. Verify preconditions
            ok, error = self.verify_preconditions()
            if not ok:
                return ReleaseResult.FAILED, error

            # 2. Determine version
            new_version, bump_type = self.determine_version()
            self.version_str = str(new_version)

            if self.config.dry_run:
                return (
                    ReleaseResult.SUCCESS,
                    f"Would release v{self.version_str} ({bump_type.value} bump)",
                )

            # 3. Create Gira ticket
            if self.config.create_gira_ticket:
                self.ticket_id = gira.create_release_ticket(self.version_str)

            # 4. Update files
            self.update_files(new_version)
            self.generate_changelog(new_version)

            # 5. Quality checks
            if not self.run_quality_checks():
                self.rollback()
                return ReleaseResult.FAILED, "Quality checks failed"

            # 6. Commit changes
            git_ops.commit_changes(
                f"chore: bump version to {self.version_str}\n\nRelease Consoul v{self.version_str}",
                ["CHANGELOG.md", "pyproject.toml", ".gira/"],
            )

            # 7. Merge to main
            git_ops.checkout_branch(self.config.main_branch)
            git_ops.merge_branch(
                self.config.develop_branch,
                message=f"Merge {self.config.develop_branch} for v{self.version_str} release",
            )

            # 8. Create tag
            git_ops.create_tag(f"v{self.version_str}", f"Release v{self.version_str}")
            self.tag_created = True

            # 9. Push changes
            git_ops.push_changes(branch=self.config.main_branch, tags=True)

            # 10. Create GitHub release
            if self.config.create_github_release:
                if github.is_gh_cli_installed():
                    section = changelog.generate_changelog_section(self.version_str)
                    github.create_release(f"v{self.version_str}", section)

            # 11. Merge back to develop
            git_ops.checkout_branch(self.config.develop_branch)
            git_ops.merge_branch(
                self.config.main_branch,
                message=f"Merge {self.config.main_branch} after v{self.version_str} release",
            )
            git_ops.push_changes(branch=self.config.develop_branch)

            # 12. Update Gira ticket
            if self.ticket_id:
                gira.update_ticket(self.ticket_id, self.version_str)

            return (
                ReleaseResult.SUCCESS,
                f"Successfully released v{self.version_str}",
            )

        except Exception as e:
            self.rollback()
            return ReleaseResult.FAILED, f"Release failed: {e!s}"

    def rollback(self) -> None:
        """Rollback failed release attempt."""
        try:
            # Reset to HEAD
            git_ops.reset_to_commit(hard=True)

            # Delete tag if created
            if self.tag_created:
                git_ops.delete_tag(f"v{self.version_str}")

            # Switch back to develop
            current = git_ops.get_current_branch()
            if current != self.config.develop_branch:
                git_ops.checkout_branch(self.config.develop_branch)

        except Exception:
            pass  # Best effort rollback
