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


@history.command("search")  # type: ignore[misc]
@click.argument("query")  # type: ignore[misc]
@click.option(  # type: ignore[misc]
    "--limit",
    "-n",
    type=int,
    default=20,
    help="Maximum number of results to return (default: 20)",
)
@click.option(  # type: ignore[misc]
    "--model",
    help="Filter results by model name",
)
@click.option(  # type: ignore[misc]
    "--after",
    help="Filter results after this date (ISO format: YYYY-MM-DD)",
)
@click.option(  # type: ignore[misc]
    "--before",
    help="Filter results before this date (ISO format: YYYY-MM-DD)",
)
@click.option(  # type: ignore[misc]
    "--context",
    "-c",
    type=int,
    default=2,
    help="Number of surrounding messages to show (default: 2)",
)
@click.option(  # type: ignore[misc]
    "--format",
    "-f",
    type=click.Choice(["text", "json"], case_sensitive=False),
    default="text",
    help="Output format (default: text)",
)
@click.option(  # type: ignore[misc]
    "--db-path",
    type=click.Path(path_type=Path),
    help="Path to history database (default: ~/.consoul/history.db)",
)
def search_history(
    query: str,
    limit: int,
    model: str | None,
    after: str | None,
    before: str | None,
    context: int,
    format: str,
    db_path: Path | None,
) -> None:
    """Search conversation history using full-text search.

    Query supports FTS5 syntax:
      - Basic: 'authentication bug'
      - Phrase: '"token limit exceeded"'
      - Prefix: 'auth*'
      - Boolean: 'bug AND NOT feature'

    Examples:
      consoul history search "authentication error"
      consoul history search '"token limit"' --model gpt-4o
      consoul history search "bug" --after 2025-01-01 --limit 10
    """
    import json

    from consoul.ai.database import ConversationDatabase, DatabaseError

    try:
        db = ConversationDatabase(db_path or "~/.consoul/history.db")
        results = db.search_messages(
            query=query,
            limit=limit,
            model_filter=model,
            after_date=after,
            before_date=before,
        )

        if not results:
            click.echo(f"No results found for: {query}")
            return

        if format == "json":
            # JSON output
            output = {
                "query": query,
                "total_results": len(results),
                "results": results,
            }
            click.echo(json.dumps(output, indent=2))
        else:
            # Text output
            click.echo(f"\nFound {len(results)} result(s) for: {query}\n")

            for i, result in enumerate(results, 1):
                click.echo("=" * 70)
                click.echo(
                    f"#{i} | Session: {result['session_id']} | Model: {result['model']}"
                )
                click.echo(f"    Timestamp: {result['timestamp']}")
                click.echo("-" * 70)

                # Show context if requested
                if context > 0:
                    try:
                        context_msgs = db.get_message_context(result["id"], context)
                        for msg in context_msgs:
                            role_label = msg["role"].upper()
                            is_match = msg["id"] == result["id"]
                            prefix = ">>> " if is_match else "    "
                            click.echo(f"{prefix}{role_label}:")

                            # Show snippet for matched message, full content for context
                            content = (
                                result["snippet"]
                                .replace("<mark>", "**")
                                .replace("</mark>", "**")
                                if is_match
                                else msg["content"][:200]
                            )
                            click.echo(f"{prefix}{content}")
                            click.echo()
                    except DatabaseError:
                        # Fallback to just showing the match
                        click.echo(f">>> {result['role'].upper()}:")
                        snippet = (
                            result["snippet"]
                            .replace("<mark>", "**")
                            .replace("</mark>", "**")
                        )
                        click.echo(f">>> {snippet}")
                        click.echo()
                else:
                    # Just show the snippet
                    click.echo(f">>> {result['role'].upper()}:")
                    snippet = (
                        result["snippet"]
                        .replace("<mark>", "**")
                        .replace("</mark>", "**")
                    )
                    click.echo(f">>> {snippet}")
                    click.echo()

                click.echo(
                    f"[View full conversation: consoul history show {result['session_id']}]"
                )
                click.echo()

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
@click.argument("session_id", required=False)  # type: ignore[misc]
@click.argument("output_file", type=click.Path(path_type=Path))  # type: ignore[misc]
@click.option(  # type: ignore[misc]
    "--format",
    "-f",
    type=click.Choice(["json", "markdown", "html", "csv"], case_sensitive=False),
    default="json",
    help="Output format (default: json)",
)
@click.option(  # type: ignore[misc]
    "--all",
    is_flag=True,
    help="Export all conversations (JSON format only)",
)
@click.option(  # type: ignore[misc]
    "--db-path",
    type=click.Path(path_type=Path),
    help="Path to history database (default: ~/.consoul/history.db)",
)
def export_history(
    session_id: str | None,
    output_file: Path,
    format: str,
    all: bool,
    db_path: Path | None,
) -> None:
    """Export conversation(s) to a file.

    Supported formats:
        - json: Structured JSON with full metadata (supports round-trip import)
        - markdown: Human-readable Markdown with formatting
        - html: Standalone HTML file with embedded styling
        - csv: CSV format for analytics (one row per message)

    Examples:
        consoul history export SESSION-ID output.json --format json
        consoul history export SESSION-ID output.md --format markdown
        consoul history export --all backup.json  # Export all conversations
    """
    from consoul.ai.database import (
        ConversationDatabase,
        ConversationNotFoundError,
        DatabaseError,
    )
    from consoul.formatters import get_formatter
    from consoul.formatters.json_formatter import JSONFormatter

    try:
        # Validate arguments
        if all and session_id:
            click.echo("Error: Cannot specify both SESSION_ID and --all", err=True)
            sys.exit(1)

        if not all and not session_id:
            click.echo("Error: Must specify SESSION_ID or use --all", err=True)
            sys.exit(1)

        if all and format != "json":
            click.echo(
                "Error: --all flag only supports JSON format for consolidated backups",
                err=True,
            )
            sys.exit(1)

        db = ConversationDatabase(db_path or "~/.consoul/history.db")

        if all:
            # Export all conversations
            conversations = db.list_conversations(limit=10000)  # High limit for backup

            if not conversations:
                click.echo("No conversations found to export", err=True)
                sys.exit(1)

            # Fetch all conversation data
            conversations_data = []
            for conv in conversations:
                meta = db.get_conversation_metadata(conv["session_id"])
                messages = db.load_conversation(conv["session_id"])
                conversations_data.append((meta, messages))

            # Export using multi-conversation format
            json_output = JSONFormatter.export_multiple(conversations_data)
            output_file.write_text(json_output, encoding="utf-8")

            click.echo(f"Exported {len(conversations)} conversations to: {output_file}")

        else:
            # Export single conversation
            meta = db.get_conversation_metadata(session_id)  # type: ignore[arg-type]
            messages = db.load_conversation(session_id)  # type: ignore[arg-type]

            # Get formatter and export
            formatter = get_formatter(format)
            formatter.export_to_file(meta, messages, output_file)

            click.echo(f"Exported conversation to: {output_file}")

    except ConversationNotFoundError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except DatabaseError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error exporting conversation: {e}", err=True)
        sys.exit(1)


@history.command("import")  # type: ignore[misc]
@click.argument("import_file", type=click.Path(exists=True, path_type=Path))  # type: ignore[misc]
@click.option(  # type: ignore[misc]
    "--dry-run",
    is_flag=True,
    help="Validate import file without importing",
)
@click.option(  # type: ignore[misc]
    "--db-path",
    type=click.Path(path_type=Path),
    help="Path to history database (default: ~/.consoul/history.db)",
)
def import_history(import_file: Path, dry_run: bool, db_path: Path | None) -> None:
    """Import conversations from Consoul JSON export.

    Supports both single conversation (v1.0) and multi-conversation (v1.0-multi) formats.
    This command restores conversations from backups created with the export command.

    Examples:
        consoul history import backup.json
        consoul history import backup.json --dry-run  # validate only
    """
    import json

    from consoul.ai.database import ConversationDatabase, DatabaseError
    from consoul.formatters.json_formatter import JSONFormatter

    try:
        # Read and parse import file
        try:
            data = json.loads(import_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            click.echo(f"Error: Invalid JSON file: {e}", err=True)
            sys.exit(1)

        # Validate structure
        try:
            JSONFormatter.validate_import_data(data)
        except ValueError as e:
            click.echo(f"Error: Invalid export format: {e}", err=True)
            sys.exit(1)

        version = data["version"]
        is_multi = version == JSONFormatter.VERSION_MULTI

        if dry_run:
            click.echo("✓ Validation successful")
            click.echo(f"  Version: {version}")
            click.echo(f"  Exported: {data['exported_at']}")

            if is_multi:
                click.echo(f"  Conversations: {data['conversation_count']}")
                for i, conv_data in enumerate(data["conversations"]):
                    conv = conv_data["conversation"]
                    click.echo(
                        f"    [{i + 1}] {conv['session_id']} - "
                        f"{conv['model']} - "
                        f"{len(conv_data['messages'])} messages"
                    )
            else:
                click.echo(f"  Session ID: {data['conversation']['session_id']}")
                click.echo(f"  Model: {data['conversation']['model']}")
                click.echo(f"  Messages: {len(data['messages'])}")
            return

        # Import conversation(s)
        db = ConversationDatabase(db_path or "~/.consoul/history.db")

        if is_multi:
            # Import multiple conversations
            imported_count = 0
            skipped_count = 0

            for conv_data in data["conversations"]:
                conv = conv_data["conversation"]
                session_id = conv["session_id"]

                # Check if conversation already exists
                try:
                    existing = db.get_conversation_metadata(session_id)
                    click.echo(
                        f"Warning: Conversation {session_id} already exists. Skipping."
                    )
                    skipped_count += 1
                    continue
                except Exception:
                    # Conversation doesn't exist, proceed with import
                    pass

                # Create conversation with original session_id
                db.create_conversation(model=conv["model"], session_id=session_id)

                # Import messages
                for msg in conv_data["messages"]:
                    db.save_message(
                        session_id=session_id,
                        role=msg["role"],
                        content=msg["content"],
                        tokens=msg.get("tokens"),
                    )

                imported_count += 1

            click.echo("✓ Import complete")
            click.echo(f"  Imported: {imported_count} conversations")
            if skipped_count > 0:
                click.echo(f"  Skipped: {skipped_count} (already exist)")

        else:
            # Import single conversation
            conv = data["conversation"]
            session_id = conv["session_id"]

            # Check if conversation already exists
            try:
                existing = db.get_conversation_metadata(session_id)
                click.echo(
                    f"Warning: Conversation {session_id} already exists. Skipping import.",
                    err=True,
                )
                click.echo(
                    f"  Existing: created {existing['created_at']}, "
                    f"{existing['message_count']} messages"
                )
                sys.exit(1)
            except Exception:
                # Conversation doesn't exist, proceed with import
                pass

            # Create conversation with original session_id
            db.create_conversation(model=conv["model"], session_id=session_id)

            # Import messages
            for msg in data["messages"]:
                db.save_message(
                    session_id=session_id,
                    role=msg["role"],
                    content=msg["content"],
                    tokens=msg.get("tokens"),
                )

            click.echo(f"✓ Imported conversation: {session_id}")
            click.echo(f"  Model: {conv['model']}")
            click.echo(f"  Messages: {len(data['messages'])}")

    except DatabaseError as e:
        click.echo(f"Error: Database error: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error importing conversation: {e}", err=True)
        sys.exit(1)


def main() -> None:
    """Main entry point for Consoul CLI."""
    # Register TUI command if Textual is available
    try:
        from consoul.tui.cli import tui

        cli.add_command(tui)
    except ImportError:
        # TUI dependencies not installed, CLI will work without TUI subcommand
        pass

    cli(obj={})


if __name__ == "__main__":
    main()
