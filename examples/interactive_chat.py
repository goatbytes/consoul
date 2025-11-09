#!/usr/bin/env python3
"""Interactive chat example demonstrating Consoul's AI provider capabilities.

This example showcases:
- Dynamic provider initialization (OpenAI, Anthropic, Google, Ollama)
- Configuration loading from profiles
- Provider-specific parameters (seed, temperature, etc.)
- Streaming responses (when supported)
- SQLite conversation persistence and resumption
- Error handling and validation

Usage:
    python examples/interactive_chat.py
    python examples/interactive_chat.py --model gpt-4o
    python examples/interactive_chat.py --profile creative
    python examples/interactive_chat.py --resume SESSION_ID  # Resume a previous conversation
    python examples/interactive_chat.py --no-persist  # Disable persistence (in-memory only)
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import argparse
from typing import Any

from consoul.ai import get_chat_model, stream_response
from consoul.ai.exceptions import StreamingError
from consoul.ai.history import ConversationHistory, to_dict_message
from consoul.config import load_config


def print_banner(session_id: str | None = None, resumed: bool = False) -> None:
    """Print welcome banner.

    Args:
        session_id: Current session ID (if persistence enabled)
        resumed: Whether this is a resumed session
    """
    print("\n" + "=" * 60)
    print("  Consoul Interactive Chat Example")
    print("=" * 60)
    print("\nFeatures: Intelligent context trimming, token tracking,")
    print("          conversation persistence and resumption")
    if session_id:
        if resumed:
            print(f"\n✨ Resumed session: {session_id}")
        else:
            print(f"\n📝 Session ID: {session_id}")
        print("    (Use --resume to continue this conversation later)")
    print("\nType 'exit' or 'quit' to end the session")
    print("Type 'help' for available commands\n")


def print_help(session_id: str | None = None) -> None:
    """Print help information.

    Args:
        session_id: Current session ID (if persistence enabled)
    """
    print("\nAvailable commands:")
    print("  exit, quit  - End the chat session")
    print("  help        - Show this help message")
    print("  clear       - Clear conversation history")
    print("  config      - Show current configuration")
    if session_id:
        print("  session     - Show current session ID")
    print()
    print("Note: Conversations are automatically trimmed to fit within")
    print("      the model's context window, preserving recent messages.")
    if session_id:
        print("\nPersistence: Conversations are saved to SQLite database")
        print(f"             Resume with: --resume {session_id}")
    print()


def print_config(model_config: Any, provider_name: str) -> None:
    """Print current configuration."""
    print("\n" + "-" * 60)
    print("Current Configuration:")
    print("-" * 60)
    print(f"Provider: {provider_name}")
    print(f"Model: {model_config.model}")
    print(f"Temperature: {model_config.temperature}")
    if model_config.max_tokens:
        print(f"Max Tokens: {model_config.max_tokens}")
    print("-" * 60 + "\n")


def interactive_chat(
    model_name: str | None = None,
    profile_name: str | None = None,
    temperature: float | None = None,
    show_tokens: bool = False,
    persist: bool = True,
    resume_session: str | None = None,
    summarize: bool | None = None,
    summarize_threshold: int | None = None,
    keep_recent: int | None = None,
    summary_model: str | None = None,
) -> None:
    """Run interactive chat session.

    Args:
        model_name: Optional model name override (e.g., "gpt-4o", "claude-3-5-sonnet")
        profile_name: Optional profile name to load
        temperature: Optional temperature override
        show_tokens: Whether to display token counts (default: False)
        persist: Enable SQLite persistence (default: True)
        resume_session: Session ID to resume (if provided, must exist in database)
        summarize: Enable conversation summarization (default: from config/profile)
        summarize_threshold: Trigger summarization after N messages (default: 20)
        keep_recent: Keep N recent messages verbatim (default: 10)
        summary_model: Model to use for summarization (default: main model)
    """

    try:
        # Load configuration
        config = load_config()

        # Get active profile or specified profile
        if profile_name:
            if profile_name not in config.profiles:
                print(f"❌ Error: Profile '{profile_name}' not found")
                print(f"Available profiles: {', '.join(config.profiles.keys())}")
                return
            profile = config.profiles[profile_name]
        else:
            profile = config.get_active_profile()

        # Use specified model or profile's model
        if model_name:
            # Auto-detect provider and create model
            print(f"🔧 Initializing model: {model_name}")
            if temperature is not None:
                chat_model = get_chat_model(
                    model_name, config=config, temperature=temperature
                )
            else:
                chat_model = get_chat_model(model_name, config=config)
            provider_name = model_name.split("-")[0]  # Simple extraction
        else:
            # Use profile's model configuration
            print(f"🔧 Loading profile: {profile.name}")
            model_config = profile.model

            # Apply temperature override if specified
            if temperature is not None:
                model_config.temperature = temperature

            chat_model = get_chat_model(model_config, config=config)
            provider_name = model_config.provider.value

        print(f"✅ Connected to {provider_name}")
        if model_name:
            # For string models, create a simple display config
            print(f"📝 Model: {model_name}")
            if temperature:
                print(f"🌡️  Temperature: {temperature}")
        else:
            print_config(profile.model, provider_name)

        # Get summarization settings from config/profile or CLI overrides
        use_summarize = (
            summarize if summarize is not None else profile.conversation.summarize
        )
        use_threshold = (
            summarize_threshold
            if summarize_threshold is not None
            else profile.conversation.summarize_threshold
        )
        use_keep_recent = (
            keep_recent if keep_recent is not None else profile.conversation.keep_recent
        )

        # Initialize summary model if specified
        summary_chat_model = None
        if summary_model:
            summary_chat_model = get_chat_model(summary_model, config=config)
        elif profile.conversation.summary_model:
            summary_chat_model = get_chat_model(
                profile.conversation.summary_model, config=config
            )

        # Initialize conversation history with intelligent trimming and persistence
        history = ConversationHistory(
            model_name=model_name or profile.model.model,
            model=chat_model,  # Pass model instance for accurate token counting
            persist=persist,
            session_id=resume_session,  # Resume existing session if provided
            summarize=use_summarize,
            summarize_threshold=use_threshold,
            keep_recent=use_keep_recent,
            summary_model=summary_chat_model,
        )

        # Show summarization status if enabled
        if use_summarize:
            print(
                f"📊 Summarization enabled: threshold={use_threshold}, keep_recent={use_keep_recent}"
            )

        # Print banner with session info
        print_banner(
            session_id=history.session_id if persist else None,
            resumed=resume_session is not None,
        )

        # Show loaded message count if resuming
        if resume_session and len(history) > 0:
            print(f"📚 Loaded {len(history)} messages from previous session\n")

        # Main chat loop
        while True:
            try:
                # Get user input
                user_input = input("You: ").strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.lower() in ("exit", "quit"):
                    print("\n👋 Goodbye!\n")
                    break

                if user_input.lower() == "help":
                    print_help(session_id=history.session_id if persist else None)
                    continue

                if user_input.lower() == "clear":
                    history.clear()
                    print("🗑️  Conversation history cleared\n")
                    continue

                if user_input.lower() == "config":
                    if model_name:
                        print(f"\nModel: {model_name}")
                        if temperature:
                            print(f"Temperature: {temperature}")
                    else:
                        print_config(profile.model, provider_name)
                    continue

                if user_input.lower() == "session" and persist:
                    print(f"\n📝 Current session ID: {history.session_id}")
                    print(f"   Messages: {len(history)}")
                    print(f"   Tokens: {history.count_tokens():,}")
                    print(f"\n   Resume command: --resume {history.session_id}\n")
                    continue

                # Add user message to history
                history.add_user_message(user_input)

                # Get trimmed messages (intelligent context window management)
                # This ensures we stay within the model's context limits
                trimmed_messages = history.get_trimmed_messages(reserve_tokens=1000)

                # Convert trimmed messages to dict format for streaming
                # Uses to_dict_message() to properly map roles (ai→assistant, human→user)
                messages_dict = [to_dict_message(msg) for msg in trimmed_messages]

                # Stream AI response
                print()  # Newline before streaming starts

                try:
                    assistant_message = stream_response(chat_model, messages_dict)

                    # Add assistant message to history
                    history.add_assistant_message(assistant_message)

                    # Display token count if requested
                    if show_tokens:
                        current_tokens = history.count_tokens()
                        max_tokens = history.max_tokens
                        percentage = (current_tokens / max_tokens) * 100
                        msg_count = len(history)
                        print(
                            f"\n📊 Messages: {msg_count} | Tokens: {current_tokens:,} / {max_tokens:,} ({percentage:.1f}%)\n"
                        )

                except StreamingError as e:
                    # Handle both interrupts and errors - partial response is always available
                    if "interrupted by user" in str(e).lower():
                        # User pressed Ctrl+C
                        print("\n⚠️  Streaming interrupted\n")
                    else:
                        # Actual streaming error
                        print(f"\n❌ Error getting response: {e}\n")

                    # Always save partial response if available
                    if e.partial_response:
                        history.add_assistant_message(e.partial_response)
                    else:
                        # Remove user message if we got no response at all
                        if (
                            len(history) > 0
                            and isinstance(history.messages[-1].__class__.__name__, str)
                            and history.messages[-1].type == "human"
                        ):
                            # Remove last message if it was the user's unanswered question
                            history.messages.pop()

                except Exception as e:
                    print(f"\n❌ Unexpected error: {e}\n")
                    # Remove the user message since we couldn't get a response
                    if (
                        len(history) > 0
                        and history.messages
                        and history.messages[-1].type == "human"
                    ):
                        history.messages.pop()

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!\n")
                break
            except EOFError:
                print("\n\n👋 Goodbye!\n")
                break

    except Exception as e:
        print(f"\n❌ Fatal error: {e}\n")
        import traceback

        traceback.print_exc()
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Interactive chat with AI providers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default profile with persistence (default)
  python examples/interactive_chat.py

  # Use specific model with auto-detection
  python examples/interactive_chat.py --model gpt-4o
  python examples/interactive_chat.py --model claude-3-5-sonnet-20241022
  python examples/interactive_chat.py --model llama3  # Requires Ollama

  # Use specific profile
  python examples/interactive_chat.py --profile creative

  # Override temperature
  python examples/interactive_chat.py --temperature 0.9
  python examples/interactive_chat.py --model gpt-4o --temperature 0.5

  # Resume a previous conversation
  python examples/interactive_chat.py --resume abc123-def456-...
  python examples/interactive_chat.py --model gpt-4o --resume abc123-def456-...

  # Disable persistence (in-memory only)
  python examples/interactive_chat.py --no-persist

  # Enable conversation summarization (reduces token usage by 70-90%)
  python examples/interactive_chat.py --summarize
  python examples/interactive_chat.py --summarize --summarize-threshold 15
  python examples/interactive_chat.py --summarize --summary-model gpt-4o-mini

Persistence:
  Conversations are automatically saved to ~/.consoul/history.db by default.
  Type 'session' in the chat to see the current session ID.
  Use --resume SESSION_ID to continue a previous conversation.

Summarization:
  Enable with --summarize to automatically compress long conversations.
  Older messages are summarized while recent messages are kept verbatim.
  This reduces token usage by 70-90% in long conversations.
  Use --summary-model to specify a cheaper model for summarization.

Supported providers:
  OpenAI    - gpt-4o, gpt-3.5-turbo, o1-preview (requires OPENAI_API_KEY)
  Anthropic - claude-3-5-sonnet-20241022, claude-3-opus (requires ANTHROPIC_API_KEY)
  Google    - gemini-pro, gemini-1.5-pro (requires GOOGLE_API_KEY)
  Ollama    - llama3, mistral, codellama (local, no API key needed)

For Ollama:
  1. Install: https://ollama.com
  2. Start service: ollama serve
  3. Pull model: ollama pull llama3
  4. See ollama_chat.py for dedicated Ollama example
        """,
    )

    parser.add_argument(
        "--model",
        "-m",
        help="Model name (e.g., gpt-4o, claude-3-5-sonnet-20241022)",
    )
    parser.add_argument(
        "--profile",
        "-p",
        help="Profile name to use (e.g., default, creative, code-review)",
    )
    parser.add_argument(
        "--temperature",
        "-t",
        type=float,
        help="Temperature override (0.0-2.0)",
    )
    parser.add_argument(
        "--show-tokens",
        action="store_true",
        help="Display token count after each turn (advanced feature)",
    )
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Disable SQLite persistence (in-memory only)",
    )
    parser.add_argument(
        "--resume",
        "-r",
        metavar="SESSION_ID",
        help="Resume a previous conversation by session ID",
    )
    parser.add_argument(
        "--summarize",
        action="store_true",
        help="Enable conversation summarization for context compression",
    )
    parser.add_argument(
        "--no-summarize",
        action="store_true",
        help="Disable conversation summarization (override profile setting)",
    )
    parser.add_argument(
        "--summarize-threshold",
        type=int,
        metavar="N",
        help="Trigger summarization after N messages (default: 20)",
    )
    parser.add_argument(
        "--keep-recent",
        type=int,
        metavar="N",
        help="Keep N recent messages verbatim when summarizing (default: 10)",
    )
    parser.add_argument(
        "--summary-model",
        metavar="MODEL",
        help="Model to use for summarization (e.g., gpt-4o-mini for cost savings)",
    )

    args = parser.parse_args()

    # Validate temperature if provided
    if args.temperature is not None and not 0.0 <= args.temperature <= 2.0:
        print("❌ Error: Temperature must be between 0.0 and 2.0")
        sys.exit(1)

    # Validate --no-persist and --resume are not used together
    if args.no_persist and args.resume:
        print("❌ Error: Cannot use --no-persist with --resume")
        print("   (Resuming requires persistence to be enabled)")
        sys.exit(1)

    # Validate --summarize and --no-summarize are not used together
    if args.summarize and args.no_summarize:
        print("❌ Error: Cannot use --summarize and --no-summarize together")
        sys.exit(1)

    # Validate summarization threshold
    if args.summarize_threshold is not None and args.summarize_threshold <= 0:
        print("❌ Error: --summarize-threshold must be positive")
        sys.exit(1)

    # Validate keep_recent
    if args.keep_recent is not None and args.keep_recent <= 0:
        print("❌ Error: --keep-recent must be positive")
        sys.exit(1)

    # Determine summarize value (None means use config default)
    summarize_value = None
    if args.summarize:
        summarize_value = True
    elif args.no_summarize:
        summarize_value = False

    interactive_chat(
        model_name=args.model,
        profile_name=args.profile,
        temperature=args.temperature,
        show_tokens=args.show_tokens,
        persist=not args.no_persist,
        resume_session=args.resume,
        summarize=summarize_value,
        summarize_threshold=args.summarize_threshold,
        keep_recent=args.keep_recent,
        summary_model=args.summary_model,
    )


if __name__ == "__main__":
    main()
