"""CLI entry point for Consoul."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from consoul.config.loader import load_config
from consoul.config.profiles import get_builtin_profiles, get_profile_description


@click.group(invoke_without_command=True)  # type: ignore[misc]
@click.option(  # type: ignore[misc]
    "--profile",
    "-p",
    default="default",
    help="Configuration profile to use",
)
@click.option(  # type: ignore[misc]
    "--list-profiles",
    is_flag=True,
    help="List all available profiles and exit",
)
@click.option(  # type: ignore[misc]
    "--temperature",
    type=float,
    help="Override model temperature (0.0-2.0)",
)
@click.option(  # type: ignore[misc]
    "--model",
    help="Override model name",
)
@click.option(  # type: ignore[misc]
    "--max-tokens",
    type=int,
    help="Override maximum tokens to generate",
)
@click.pass_context  # type: ignore[misc]
def cli(
    ctx: click.Context,
    profile: str,
    list_profiles: bool,
    temperature: float | None,
    model: str | None,
    max_tokens: int | None,
) -> None:
    """Consoul - AI-powered conversational CLI tool."""
    # Load configuration
    config = load_config(profile_name=profile)

    # Handle --list-profiles
    if list_profiles:
        click.echo("Available profiles:\n")
        builtin = set(get_builtin_profiles().keys())

        for profile_name in sorted(config.profiles.keys()):
            description = get_profile_description(profile_name, config)
            marker = " (built-in)" if profile_name in builtin else " (custom)"
            active = " [active]" if profile_name == config.active_profile else ""
            click.echo(f"  {profile_name}{marker}{active}")
            click.echo(f"    {description}")
        ctx.exit(0)

    # Build CLI overrides
    cli_overrides: dict[str, Any] = {}
    if temperature is not None or model is not None or max_tokens is not None:
        model_overrides: dict[str, Any] = {}
        if temperature is not None:
            model_overrides["temperature"] = temperature
        if model is not None:
            model_overrides["model"] = model
        if max_tokens is not None:
            model_overrides["max_tokens"] = max_tokens

        # Apply overrides to active profile's model config
        active_profile_name = config.active_profile
        cli_overrides = {"profiles": {active_profile_name: {"model": model_overrides}}}

    # Store in context for subcommands
    ctx.ensure_object(dict)
    ctx.obj["config"] = config
    ctx.obj["cli_overrides"] = cli_overrides

    # If no subcommand, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.command()  # type: ignore[misc]
@click.pass_context  # type: ignore[misc]
def chat(ctx: click.Context) -> None:
    """Start an interactive chat session."""
    click.echo("Chat functionality - Coming Soon!")
    config = ctx.obj["config"]
    active_profile = config.get_active_profile()
    click.echo(f"Using profile: {active_profile.name}")
    click.echo(f"Model: {active_profile.model.provider} - {active_profile.model.model}")


@cli.command()  # type: ignore[misc]
@click.argument("config_path", type=click.Path(path_type=Path))  # type: ignore[misc]
@click.pass_context  # type: ignore[misc]
def init(ctx: click.Context, config_path: Path) -> None:
    """Initialize a new Consoul configuration file."""
    click.echo(f"Initializing config at: {config_path}")
    click.echo("Init functionality - Coming Soon!")


def main() -> None:
    """Main entry point for Consoul CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
