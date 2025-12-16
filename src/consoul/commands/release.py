"""Release command for creating new versions."""

from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm

from consoul.release.manager import ReleaseConfig, ReleaseManager, ReleaseResult
from consoul.release.version import VersionBump

console = Console()


@click.command()
@click.option(
    "--type",
    "bump_type",
    type=click.Choice(["major", "minor", "patch", "auto"]),
    default="auto",
    help="Version bump type (auto-detected from commits by default)",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would happen without making changes",
)
@click.option(
    "--skip-tests",
    is_flag=True,
    help="Skip running test suite (not recommended)",
)
@click.option(
    "--skip-docs",
    is_flag=True,
    help="Skip publishing documentation",
)
@click.option(
    "--force",
    is_flag=True,
    help="Skip confirmation prompts",
)
def release(
    bump_type: str,
    dry_run: bool,
    skip_tests: bool,
    skip_docs: bool,
    force: bool,
) -> None:
    """Create and publish a new release.

    This command automates the complete release workflow:

    \b
    1. Determines next version from commits (or uses --type)
    2. Updates CHANGELOG.md with commit history
    3. Updates version in pyproject.toml
    4. Runs quality checks (tests, linting, type checking)
    5. Commits changes to develop branch
    6. Merges develop to main
    7. Creates git tag
    8. Pushes to GitHub
    9. Creates GitHub release (triggers PyPI publish)
    10. Merges back to develop
    11. Creates/updates Gira ticket

    Examples:

    \b
        # Auto-detect version from commits
        consoul release

    \b
        # Force minor version bump
        consoul release --type minor

    \b
        # Preview without making changes
        consoul release --dry-run

    \b
        # Skip tests (use with caution)
        consoul release --skip-tests --force
    """
    console.print(
        Panel.fit(
            "🚀 [bold]Consoul Release Manager[/bold]",
            border_style="blue",
        )
    )

    # Create configuration
    config = ReleaseConfig(
        version_bump=VersionBump(bump_type),
        skip_tests=skip_tests,
        skip_docs=skip_docs,
        dry_run=dry_run,
        force=force,
    )

    # Create manager
    manager = ReleaseManager(config)

    # Verify preconditions
    console.print("\n[yellow]Checking preconditions...[/yellow]")
    ok, error = manager.verify_preconditions()

    if not ok:
        console.print(f"[red]✗[/red] {error}")
        raise click.Abort()

    console.print("[green]✓[/green] All preconditions met")

    # Determine version
    new_version, bump_type_used = manager.determine_version()

    console.print(
        f"\n[cyan]Version:[/cyan] {new_version} ([dim]{bump_type_used.value} bump[/dim])"
    )

    if dry_run:
        console.print("\n[yellow]Dry run mode - no changes will be made[/yellow]")

    # Confirm release
    if not force and not dry_run:
        if not Confirm.ask(f"\n[bold]Proceed with release v{new_version}?[/bold]"):
            console.print("[yellow]Release cancelled[/yellow]")
            raise click.Abort()

    # Execute release
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Executing release workflow...", total=None)

        result, message = manager.execute_release()

        progress.update(task, completed=True)

    # Display result
    if result == ReleaseResult.SUCCESS:
        console.print(f"\n[green]✓[/green] {message}")

        if not dry_run:
            console.print(
                f"\n[dim]Next steps:[/dim]\n"
                f"1. Wait 2-5 minutes for GitHub Actions to publish to PyPI\n"
                f"2. Verify: https://pypi.org/project/consoul/\n"
                f"3. Test: pip install consoul=={new_version} --upgrade\n"
            )

    elif result == ReleaseResult.FAILED:
        console.print(f"\n[red]✗[/red] {message}")
        console.print("[yellow]Changes have been rolled back[/yellow]")
        raise click.Abort()

    else:  # CANCELLED
        console.print(f"\n[yellow]{message}[/yellow]")
