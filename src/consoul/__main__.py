"""CLI entry point for Consoul."""

from __future__ import annotations

import sys
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
    # Build CLI overrides BEFORE loading config
    cli_overrides: dict[str, Any] = {}
    if temperature is not None or model is not None or max_tokens is not None:
        model_overrides: dict[str, Any] = {}
        if temperature is not None:
            model_overrides["temperature"] = temperature
        if model is not None:
            model_overrides["model"] = model
        if max_tokens is not None:
            model_overrides["max_tokens"] = max_tokens

        # We need to determine the active profile to apply overrides
        # Profile name from CLI has highest precedence, otherwise we need to load config first
        # to know the active profile from files/env vars
        if profile != "default":
            # CLI specified a profile, use it
            active_profile_name = profile
        else:
            # Need to load config to determine active profile
            temp_config = load_config()
            active_profile_name = temp_config.active_profile

        cli_overrides = {"profiles": {active_profile_name: {"model": model_overrides}}}

    # Load configuration with CLI overrides applied
    config = load_config(profile_name=profile, cli_overrides=cli_overrides)

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


@cli.group()  # type: ignore[misc]
@click.pass_context  # type: ignore[misc]
def history(ctx: click.Context) -> None:
    """Manage conversation history."""
    pass


@history.command("list")  # type: ignore[misc]
@click.option(  # type: ignore[misc]
    "--limit",
    "-n",
    type=int,
    default=10,
    help="Number of conversations to show (default: 10)",
)
@click.option(  # type: ignore[misc]
    "--db-path",
    type=click.Path(path_type=Path),
    help="Path to history database (default: ~/.consoul/history.db)",
)
def list_history(limit: int, db_path: Path | None) -> None:
    """List recent conversation sessions."""
    from consoul.ai.database import ConversationDatabase, DatabaseError

    try:
        db = ConversationDatabase(db_path or "~/.consoul/history.db")
        conversations = db.list_conversations(limit=limit)

        if not conversations:
            click.echo("No conversations found.")
            return

        click.echo(f"\nRecent conversations (showing {len(conversations)}):\n")
        for conv in conversations:
            session_id = conv["session_id"]
            model = conv["model"]
            created = conv["created_at"]
            updated = conv["updated_at"]
            msg_count = conv["message_count"]

            click.echo(f"Session ID: {session_id}")
            click.echo(f"  Model:    {model}")
            click.echo(f"  Messages: {msg_count}")
            click.echo(f"  Created:  {created}")
            click.echo(f"  Updated:  {updated}")
            click.echo()

    except DatabaseError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@history.command("show")  # type: ignore[misc]
@click.argument("session_id")  # type: ignore[misc]
@click.option(  # type: ignore[misc]
    "--db-path",
    type=click.Path(path_type=Path),
    help="Path to history database (default: ~/.consoul/history.db)",
)
def show_history(session_id: str, db_path: Path | None) -> None:
    """Show conversation details for a specific session."""
    from consoul.ai.database import (
        ConversationDatabase,
        ConversationNotFoundError,
        DatabaseError,
    )

    try:
        db = ConversationDatabase(db_path or "~/.consoul/history.db")

        # Get metadata
        meta = db.get_conversation_metadata(session_id)

        click.echo(f"\nConversation: {session_id}\n")
        click.echo(f"Model:    {meta['model']}")
        click.echo(f"Messages: {meta['message_count']}")
        click.echo(f"Created:  {meta['created_at']}")
        click.echo(f"Updated:  {meta['updated_at']}")
        click.echo()

        # Get messages
        messages = db.load_conversation(session_id)

        if messages:
            click.echo("Messages:")
            click.echo("-" * 60)
            for i, msg in enumerate(messages, 1):
                role = msg["role"]
                content = msg["content"]
                tokens = msg.get("tokens", "?")

                # Truncate long messages
                if len(content) > 100:
                    content = content[:97] + "..."

                click.echo(f"{i}. {role.upper()} [{tokens} tokens]")
                click.echo(f"   {content}")
                click.echo()

    except ConversationNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except DatabaseError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@history.command("summary")  # type: ignore[misc]
@click.argument("session_id")  # type: ignore[misc]
@click.option(  # type: ignore[misc]
    "--db-path",
    type=click.Path(path_type=Path),
    help="Path to history database (default: ~/.consoul/history.db)",
)
def summary_history(session_id: str, db_path: Path | None) -> None:
    """Show conversation summary for a specific session."""
    from consoul.ai.database import (
        ConversationDatabase,
        ConversationNotFoundError,
        DatabaseError,
    )

    try:
        db = ConversationDatabase(db_path or "~/.consoul/history.db")

        # Get metadata
        meta = db.get_conversation_metadata(session_id)

        click.echo(f"\nConversation: {session_id}\n")
        click.echo(f"Model:    {meta['model']}")
        click.echo(f"Messages: {meta['message_count']}")
        click.echo(f"Created:  {meta['created_at']}")
        click.echo(f"Updated:  {meta['updated_at']}")
        click.echo()

        # Get summary
        summary = db.load_summary(session_id)

        if summary:
            click.echo("Summary:")
            click.echo("-" * 60)
            click.echo(summary)
            click.echo()
        else:
            click.echo("No summary available for this conversation.")
            click.echo(
                "Summaries are created automatically when using --summarize flag.\n"
            )

    except ConversationNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except DatabaseError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@history.command("delete")  # type: ignore[misc]
@click.argument("session_id")  # type: ignore[misc]
@click.option(  # type: ignore[misc]
    "--db-path",
    type=click.Path(path_type=Path),
    help="Path to history database (default: ~/.consoul/history.db)",
)
@click.confirmation_option(prompt="Are you sure you want to delete this conversation?")  # type: ignore[misc]
def delete_history(session_id: str, db_path: Path | None) -> None:
    """Delete a conversation session."""
    from consoul.ai.database import (
        ConversationDatabase,
        ConversationNotFoundError,
        DatabaseError,
    )

    try:
        db = ConversationDatabase(db_path or "~/.consoul/history.db")
        db.delete_conversation(session_id)
        click.echo(f"Deleted conversation: {session_id}")

    except ConversationNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except DatabaseError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@history.command("clear")  # type: ignore[misc]
@click.option(  # type: ignore[misc]
    "--db-path",
    type=click.Path(path_type=Path),
    help="Path to history database (default: ~/.consoul/history.db)",
)
@click.confirmation_option(  # type: ignore[misc]
    prompt="Are you sure you want to delete ALL conversations? This cannot be undone!"
)
def clear_history(db_path: Path | None) -> None:
    """Delete all conversation history."""
    from consoul.ai.database import ConversationDatabase, DatabaseError

    try:
        db = ConversationDatabase(db_path or "~/.consoul/history.db")
        count = db.clear_all_conversations()
        click.echo(f"Cleared {count} conversation(s)")

    except DatabaseError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@history.command("stats")  # type: ignore[misc]
@click.option(  # type: ignore[misc]
    "--db-path",
    type=click.Path(path_type=Path),
    help="Path to history database (default: ~/.consoul/history.db)",
)
def stats_history(db_path: Path | None) -> None:
    """Show conversation history statistics."""
    from consoul.ai.database import ConversationDatabase, DatabaseError

    try:
        db = ConversationDatabase(db_path or "~/.consoul/history.db")
        stats = db.get_stats()

        click.echo("\nConversation History Statistics\n")
        click.echo(f"Total conversations: {stats['total_conversations']}")
        click.echo(f"Total messages:      {stats['total_messages']}")
        click.echo(f"Database size:       {stats['db_size_bytes']:,} bytes")

        if stats["oldest_conversation"]:
            click.echo(f"Oldest conversation: {stats['oldest_conversation']}")
        if stats["newest_conversation"]:
            click.echo(f"Newest conversation: {stats['newest_conversation']}")

        click.echo()

    except DatabaseError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@history.command("export")  # type: ignore[misc]
@click.argument("session_id")  # type: ignore[misc]
@click.argument("output_file", type=click.Path(path_type=Path))  # type: ignore[misc]
@click.option(  # type: ignore[misc]
    "--format",
    "-f",
    type=click.Choice(["json", "txt"], case_sensitive=False),
    default="json",
    help="Output format (default: json)",
)
@click.option(  # type: ignore[misc]
    "--db-path",
    type=click.Path(path_type=Path),
    help="Path to history database (default: ~/.consoul/history.db)",
)
def export_history(
    session_id: str, output_file: Path, format: str, db_path: Path | None
) -> None:
    """Export a conversation to a file."""
    import json

    from consoul.ai.database import (
        ConversationDatabase,
        ConversationNotFoundError,
        DatabaseError,
    )

    try:
        db = ConversationDatabase(db_path or "~/.consoul/history.db")

        # Get metadata and messages
        meta = db.get_conversation_metadata(session_id)
        messages = db.load_conversation(session_id)

        # Export based on format
        if format == "json":
            data = {"metadata": meta, "messages": messages}
            with open(output_file, "w") as f:
                json.dump(data, f, indent=2)
        else:  # txt
            with open(output_file, "w") as f:
                f.write(f"Conversation: {session_id}\n")
                f.write(f"Model: {meta['model']}\n")
                f.write(f"Created: {meta['created_at']}\n")
                f.write(f"Updated: {meta['updated_at']}\n")
                f.write(f"Messages: {meta['message_count']}\n")
                f.write("=" * 60 + "\n\n")

                for msg in messages:
                    role = msg["role"].upper()
                    content = msg["content"]
                    f.write(f"{role}:\n{content}\n\n")

        click.echo(f"Exported conversation to: {output_file}")

    except ConversationNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except DatabaseError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error writing file: {e}", err=True)
        sys.exit(1)


def main() -> None:
    """Main entry point for Consoul CLI."""
    cli(obj={})


if __name__ == "__main__":
    main()
