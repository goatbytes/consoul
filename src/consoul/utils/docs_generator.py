"""Documentation generation utilities for Consoul."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, PackageLoader, select_autoescape


def run_consoul_describe(command: list[str] | None = None) -> dict[str, Any]:
    """
    Execute consoul describe command and return JSON output.

    Args:
        command: Optional command path to describe (e.g., ['tui'])

    Returns:
        Parsed JSON output from consoul describe

    Raises:
        subprocess.CalledProcessError: If consoul describe fails
        json.JSONDecodeError: If output is not valid JSON
    """
    cmd = ["consoul", "describe"]
    if command:
        cmd.extend(command)

    # Run the command and capture output
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=True,
    )

    # Parse and return JSON output
    parsed: dict[str, Any] = json.loads(result.stdout)
    return parsed


def parse_command_schema(schema: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Parse command schema and extract relevant information.

    Args:
        schema: JSON schema from consoul describe

    Returns:
        List of parsed command information
    """
    commands = []

    def extract_command(cmd: dict[str, Any]) -> None:
        """Recursively extract command information."""
        # The name already comes with the full path from describe command
        full_name = cmd["name"]

        if cmd["type"] == "command" or cmd["type"] == "group":
            # Extract command details
            command_info = {
                "name": full_name,
                "description": cmd.get("description", ""),
                "type": cmd["type"],
                "arguments": cmd.get("arguments", []),
                "options": cmd.get("options", []),
            }

            # Add subcommands if it's a group
            if cmd["type"] == "group":
                command_info["commands"] = []
                for subcmd in cmd.get("commands", []):
                    # For groups, we want to include subcommands in the info
                    # but also process them recursively
                    # Extract simple command name, handling edge cases
                    parts = subcmd["name"].split()
                    subcmd_info = {
                        "name": parts[-1]
                        if parts
                        else subcmd["name"],  # Just the command name
                        "description": subcmd.get("description", ""),
                        "type": subcmd["type"],
                        "arguments": subcmd.get("arguments", []),
                        "options": subcmd.get("options", []),
                    }
                    command_info["commands"].append(subcmd_info)

            commands.append(command_info)

            # Process nested commands as separate top-level entries
            if cmd["type"] == "group":
                for subcmd in cmd.get("commands", []):
                    extract_command(subcmd)

    # Handle top-level application
    if schema["type"] == "application":
        # Process all top-level commands
        for cmd in schema.get("commands", []):
            extract_command(cmd)
    else:
        # Single command
        extract_command(schema)

    return commands


def get_jinja_env() -> Environment:
    """Get configured Jinja2 environment."""
    # Try to use PackageLoader for installed package
    try:
        env = Environment(
            loader=PackageLoader("consoul", "templates"),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=False,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )
    except Exception:
        # Fallback to FileSystemLoader for development
        template_dir = Path(__file__).parent.parent / "templates"
        env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=False,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )

    # Add custom filter to clean up empty lines
    def cleanup_empty_lines(text: str) -> str:
        """Remove excessive empty lines from text."""
        if not text:
            return text
        # Split into lines, remove empty lines that are surrounded by empty lines
        lines = text.split("\n")
        cleaned = []
        prev_empty = False

        for line in lines:
            is_empty = not line.strip()
            # Keep the line if it's not empty, or if previous line wasn't empty
            if not is_empty or not prev_empty:
                cleaned.append(line)
            prev_empty = is_empty

        return "\n".join(cleaned)

    env.filters["cleanup_empty_lines"] = cleanup_empty_lines
    return env


def format_command_docs(
    commands: list[dict[str, Any]], template_name: str = "cli_reference.md.j2"
) -> str:
    """
    Format command information using Jinja2 templates.

    Args:
        commands: List of parsed command information
        template_name: Name of the template to use

    Returns:
        Formatted Markdown content
    """
    env = get_jinja_env()
    template = env.get_template(template_name)
    content = template.render(commands=commands)
    # Apply cleanup filter to the entire output
    result: str = env.filters["cleanup_empty_lines"](content)
    return result


def format_single_command(
    command: dict[str, Any], template_name: str = "command.md.j2"
) -> str:
    """
    Format a single command using Jinja2 template.

    Args:
        command: Command information dict
        template_name: Name of the template to use

    Returns:
        Formatted Markdown content
    """
    env = get_jinja_env()
    template = env.get_template(template_name)
    content = template.render(command=command)
    # Apply cleanup filter to the entire output
    result: str = env.filters["cleanup_empty_lines"](content)
    return result


def generate_cli_docs(
    output_path: Path,
    command: list[str] | None = None,
    template_name: str = "cli_reference.md.j2",
) -> None:
    """
    Generate CLI documentation.

    Args:
        output_path: Where to write the documentation
        command: Optional specific command to document
        template_name: Template to use
    """
    schema = run_consoul_describe(command)
    commands = parse_command_schema(schema)

    # If single command and using command template, format differently
    if len(commands) == 1 and template_name == "command.md.j2":
        content = format_single_command(commands[0], template_name)
    else:
        content = format_command_docs(commands, template_name)

    # Write the content
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def generate_markdown_from_schema(schema: dict[str, Any]) -> str:
    """
    Generate markdown documentation from a schema dict.

    Args:
        schema: Schema dictionary from consoul describe

    Returns:
        Markdown formatted documentation
    """
    commands = parse_command_schema(schema)

    # Check if it's a single command or multiple
    if len(commands) == 1 and schema.get("type") != "application":
        return format_single_command(commands[0])
    else:
        return format_command_docs(commands)
