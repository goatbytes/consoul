"""Describe command for programmatic CLI schema discovery."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import click


def get_command_info(cmd: click.Command, parent_path: str = "") -> dict[str, Any]:
    """
    Extract metadata from a Click command.

    Args:
        cmd: Click Command object
        parent_path: Parent command path (e.g., "consoul")

    Returns:
        Dictionary containing command metadata
    """
    full_name = (
        f"{parent_path} {cmd.name}".strip() if parent_path else cmd.name or "consoul"
    )

    # Get command description
    description = ""
    if cmd.help:
        # Take first line of help text
        description = cmd.help.split("\n")[0].strip()

    # Build command info
    info: dict[str, Any] = {
        "name": full_name,
        "description": description,
        "type": "group" if isinstance(cmd, click.Group) else "command",
        "arguments": [],
        "options": [],
    }

    # Extract parameters
    for param in cmd.params:
        if isinstance(param, click.Argument):
            arg_info = {
                "name": param.name,
                "description": getattr(param, "help", "") or "",
                "required": param.required,
                "type": param.type.name if param.type else "string",
            }
            # Skip non-serializable defaults
            if param.default is not None and not param.required:
                try:
                    import json as _json

                    _json.dumps(param.default)
                    arg_info["default"] = param.default
                except (TypeError, ValueError):
                    pass
            info["arguments"].append(arg_info)

        elif isinstance(param, click.Option):
            # Skip help option
            if param.name == "help":
                continue

            opt_info: dict[str, Any] = {
                "name": param.name,
                "description": param.help or "",
                "type": param.type.name if param.type else "string",
            }

            # Add flags
            if param.opts:
                opt_info["flags"] = param.opts

            # Add short name if available
            short_flags = [
                f
                for f in (param.opts or [])
                if f.startswith("-") and not f.startswith("--")
            ]
            if short_flags:
                opt_info["short_name"] = short_flags[0]

            # Add default value (skip None, (), and Click internal sentinel values)
            if param.default is not None and param.default != ():
                # Check if it's a serializable value
                try:
                    import json

                    json.dumps(param.default)
                    opt_info["default"] = param.default
                except (TypeError, ValueError):
                    # Skip non-serializable defaults (like Click sentinels)
                    pass

            # Add choices if available
            if isinstance(param.type, click.Choice):
                opt_info["choices"] = param.type.choices

            # Boolean flags
            if param.is_flag or (param.type and param.type.name == "BOOL"):
                opt_info["type"] = "boolean"

            info["options"].append(opt_info)

    # For groups, process subcommands
    if isinstance(cmd, click.Group):
        info["commands"] = []
        for subcmd_name in sorted(cmd.list_commands(click.Context(cmd))):
            subcmd = cmd.get_command(click.Context(cmd), subcmd_name)
            if subcmd:
                info["commands"].append(get_command_info(subcmd, full_name))

    return info


def get_app_schema(cli_app: click.Group) -> dict[str, Any]:
    """
    Get the complete schema for the Consoul CLI application.

    Args:
        cli_app: The main Click group

    Returns:
        Complete CLI schema
    """
    schema: dict[str, Any] = {
        "name": "consoul",
        "description": "AI-powered conversational CLI tool",
        "type": "application",
        "commands": [],
        "options": [],
    }

    # Add global options
    for param in cli_app.params:
        if isinstance(param, click.Option) and param.name != "help":
            opt_info: dict[str, Any] = {
                "name": param.name,
                "description": param.help or "",
                "type": param.type.name if param.type else "string",
            }
            if param.opts:
                opt_info["flags"] = param.opts
            # Skip non-serializable defaults
            if param.default is not None:
                try:
                    import json as _json

                    _json.dumps(param.default)
                    opt_info["default"] = param.default
                except (TypeError, ValueError):
                    pass
            schema["options"].append(opt_info)

    # Process all commands
    ctx = click.Context(cli_app)
    for cmd_name in sorted(cli_app.list_commands(ctx)):
        cmd = cli_app.get_command(ctx, cmd_name)
        if cmd:
            schema["commands"].append(get_command_info(cmd, "consoul"))

    return schema


@click.command()
@click.argument("command_path", nargs=-1)
@click.option(
    "--format",
    "-f",
    type=click.Choice(["json", "markdown"], case_sensitive=False),
    default="json",
    help="Output format (default: json)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Write output to file instead of stdout",
)
@click.option(
    "--indent",
    type=int,
    default=2,
    help="JSON indentation spaces (default: 2)",
)
@click.option(
    "--compact",
    is_flag=True,
    help="Compact JSON output (no indentation)",
)
@click.pass_context
def describe(
    ctx: click.Context,
    command_path: tuple[str, ...],
    format: str,
    output: Path | None,
    indent: int,
    compact: bool,
) -> None:
    """Describe Consoul CLI commands and their schemas.

    By default, outputs CLI structure as JSON for compatibility with
    documentation generators and AI agents.

    Examples:

        \b
        # Show all commands structure
        consoul describe

        \b
        # Describe specific command
        consoul describe tui

        \b
        # Output to file
        consoul describe --output cli-schema.json

        \b
        # Markdown format
        consoul describe --format markdown
    """
    # Get the main CLI app from parent context
    cli_app = ctx.parent.command if ctx.parent else None
    if not cli_app or not isinstance(cli_app, click.Group):
        click.echo("Error: Could not access CLI application", err=True)
        sys.exit(1)

    # Get schema for specific command or entire app
    if command_path:
        # Navigate to specific command
        current: click.Command | click.Group = cli_app
        full_path = "consoul"

        for cmd_name in command_path:
            if not isinstance(current, click.Group):
                click.echo(f"Error: '{full_path}' is not a group command", err=True)
                sys.exit(1)

            cmd = current.get_command(click.Context(current), cmd_name)
            if not cmd:
                click.echo(
                    f"Error: Command '{cmd_name}' not found in '{full_path}'", err=True
                )
                sys.exit(1)

            current = cmd
            full_path = f"{full_path} {cmd_name}"

        schema = get_command_info(
            current,
            " ".join(["consoul", *command_path[:-1]]) if len(command_path) > 1 else "",
        )
    else:
        schema = get_app_schema(cli_app)

    # Format output
    if format.lower() == "json":
        if compact:
            json_str = json.dumps(schema, ensure_ascii=False, separators=(",", ":"))
        else:
            json_str = json.dumps(schema, indent=indent, ensure_ascii=False)

        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json_str, encoding="utf-8")
            click.echo(f"Schema written to: {output}")
        else:
            click.echo(json_str)

    elif format.lower() == "markdown":
        # Basic markdown output (will be enhanced with templates later)
        from consoul.utils.docs_generator import generate_markdown_from_schema

        markdown = generate_markdown_from_schema(schema)

        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(markdown, encoding="utf-8")
            click.echo(f"Documentation written to: {output}")
        else:
            click.echo(markdown)
