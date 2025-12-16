"""Git operations for release workflow."""

from __future__ import annotations

import subprocess


class GitOperationError(Exception):
    """Raised when a git operation fails."""

    pass


def run_git_command(
    cmd: list[str], check: bool = True
) -> subprocess.CompletedProcess[str]:
    """
    Run a git command and return result.

    Args:
        cmd: Git command as list of arguments
        check: Raise exception on non-zero exit code

    Returns:
        Completed process

    Raises:
        GitOperationError: If command fails and check=True
    """
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=check)
        return result
    except subprocess.CalledProcessError as e:
        raise GitOperationError(
            f"Git command failed: {' '.join(cmd)}\n{e.stderr}"
        ) from e


def is_clean_working_tree() -> bool:
    """
    Check if working tree is clean (no uncommitted changes).

    Returns:
        True if working tree is clean
    """
    result = run_git_command(["git", "status", "--porcelain"], check=False)
    return not result.stdout.strip()


def get_current_branch() -> str:
    """
    Get name of current git branch.

    Returns:
        Branch name

    Raises:
        GitOperationError: If not in a git repository
    """
    result = run_git_command(["git", "branch", "--show-current"])
    return result.stdout.strip()


def is_branch_synced_with_remote(branch: str = "develop") -> bool:
    """
    Check if local branch is synced with remote.

    Args:
        branch: Branch name to check

    Returns:
        True if synced with remote
    """
    # Fetch latest
    run_git_command(["git", "fetch", "origin", branch], check=False)

    # Compare local and remote
    result = run_git_command(
        ["git", "rev-list", "--left-right", "--count", f"{branch}...origin/{branch}"],
        check=False,
    )

    if result.returncode != 0:
        # Remote branch doesn't exist or other error
        return True

    # Parse output: "0\t0" means synced
    behind, ahead = result.stdout.strip().split("\t")
    return behind == "0" and ahead == "0"


def commit_changes(message: str, files: list[str] | None = None) -> None:
    """
    Stage and commit changes.

    Args:
        message: Commit message
        files: Specific files to stage (None for all changes)

    Raises:
        GitOperationError: If commit fails
    """
    # Stage files
    if files:
        run_git_command(["git", "add"] + files)
    else:
        run_git_command(["git", "add", "-A"])

    # Commit
    run_git_command(["git", "commit", "-m", message])


def create_tag(tag: str, message: str) -> None:
    """
    Create an annotated git tag.

    Args:
        tag: Tag name (e.g., "v0.4.0")
        message: Tag annotation message

    Raises:
        GitOperationError: If tag creation fails
    """
    run_git_command(["git", "tag", "-a", tag, "-m", message])


def delete_tag(tag: str, remote: bool = False) -> None:
    """
    Delete a git tag.

    Args:
        tag: Tag name to delete
        remote: Also delete from remote

    Raises:
        GitOperationError: If deletion fails
    """
    run_git_command(["git", "tag", "-d", tag], check=False)

    if remote:
        run_git_command(["git", "push", "origin", f":refs/tags/{tag}"], check=False)


def checkout_branch(branch: str, create: bool = False) -> None:
    """
    Checkout a git branch.

    Args:
        branch: Branch name
        create: Create branch if it doesn't exist

    Raises:
        GitOperationError: If checkout fails
    """
    if create:
        run_git_command(["git", "checkout", "-b", branch])
    else:
        run_git_command(["git", "checkout", branch])


def merge_branch(branch: str, no_ff: bool = True, message: str | None = None) -> None:
    """
    Merge a branch into current branch.

    Args:
        branch: Branch to merge from
        no_ff: Use --no-ff (create merge commit)
        message: Merge commit message

    Raises:
        GitOperationError: If merge fails
    """
    cmd = ["git", "merge", branch]

    if no_ff:
        cmd.append("--no-ff")

    if message:
        cmd.extend(["-m", message])

    run_git_command(cmd)


def push_changes(
    remote: str = "origin", branch: str | None = None, tags: bool = False
) -> None:
    """
    Push commits and optionally tags to remote.

    Args:
        remote: Remote name
        branch: Branch to push (None for current)
        tags: Also push tags

    Raises:
        GitOperationError: If push fails
    """
    cmd = ["git", "push", remote]

    if branch:
        cmd.append(branch)

    run_git_command(cmd)

    if tags:
        run_git_command(["git", "push", remote, "--tags"])


def stash_changes() -> str:
    """
    Stash current changes.

    Returns:
        Stash identifier

    Raises:
        GitOperationError: If stash fails
    """
    result = run_git_command(["git", "stash", "push", "-m", "Release workflow backup"])
    return result.stdout.strip()


def pop_stash() -> None:
    """
    Pop the most recent stash.

    Raises:
        GitOperationError: If pop fails
    """
    run_git_command(["git", "stash", "pop"], check=False)


def reset_to_commit(commit: str = "HEAD", hard: bool = False) -> None:
    """
    Reset to a specific commit.

    Args:
        commit: Commit reference
        hard: Use --hard (discard changes)

    Raises:
        GitOperationError: If reset fails
    """
    cmd = ["git", "reset"]

    if hard:
        cmd.append("--hard")

    cmd.append(commit)

    run_git_command(cmd)


def get_remote_url(remote: str = "origin") -> str | None:
    """
    Get URL of remote repository.

    Args:
        remote: Remote name

    Returns:
        Remote URL or None if remote doesn't exist
    """
    result = run_git_command(["git", "remote", "get-url", remote], check=False)

    if result.returncode == 0:
        return result.stdout.strip()

    return None


def extract_github_repo() -> tuple[str, str] | None:
    """
    Extract GitHub owner/repo from remote URL.

    Returns:
        Tuple of (owner, repo) or None if not a GitHub repo

    Example:
        >>> extract_github_repo()
        ('goatbytes', 'consoul')
    """
    url = get_remote_url()

    if not url:
        return None

    # Match both HTTPS and SSH formats
    # HTTPS: https://github.com/owner/repo.git
    # SSH: git@github.com:owner/repo.git
    import re

    match = re.search(r"github\.com[:/]([^/]+)/([^/]+?)(\.git)?$", url)

    if match:
        owner = match.group(1)
        repo = match.group(2)
        return (owner, repo)

    return None
