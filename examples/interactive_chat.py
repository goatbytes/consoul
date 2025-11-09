#!/usr/bin/env python3
"""Interactive chat example demonstrating Consoul's AI provider capabilities.

This example showcases:
- Dynamic provider initialization (OpenAI, Anthropic, Google, Ollama)
- Configuration loading from profiles
- Provider-specific parameters (seed, temperature, etc.)
- Streaming responses (when supported)
- Error handling and validation

Usage:
    python examples/interactive_chat.py
    python examples/interactive_chat.py --model gpt-4o
    python examples/interactive_chat.py --profile creative
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import argparse
from typing import Any

from consoul.ai import get_chat_model, stream_response
from consoul.ai.context import count_message_tokens, get_model_token_limit
from consoul.ai.exceptions import StreamingError
from consoul.ai.history import to_langchain_message
from consoul.config import load_config


def print_banner() -> None:
    """Print welcome banner."""
    print("\n" + "=" * 60)
    print("  Consoul Interactive Chat Example")
    print("=" * 60)
    print("\nType 'exit' or 'quit' to end the session")
    print("Type 'help' for available commands\n")


def print_help() -> None:
    """Print help information."""
    print("\nAvailable commands:")
    print("  exit, quit  - End the chat session")
    print("  help        - Show this help message")
    print("  clear       - Clear conversation history")
    print("  config      - Show current configuration")
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
) -> None:
    """Run interactive chat session.

    Args:
        model_name: Optional model name override (e.g., "gpt-4o", "claude-3-5-sonnet")
        profile_name: Optional profile name to load
        temperature: Optional temperature override
        show_tokens: Whether to display token counts (default: False)
    """
    print_banner()

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

        # Conversation history
        messages: list[dict[str, str]] = []

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
                    print_help()
                    continue

                if user_input.lower() == "clear":
                    messages.clear()
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

                # Add user message to history
                messages.append({"role": "user", "content": user_input})

                # Stream AI response
                print()  # Newline before streaming starts

                try:
                    assistant_message = stream_response(chat_model, messages)

                    # Add assistant message to history
                    messages.append({"role": "assistant", "content": assistant_message})

                    # Display token count if requested
                    if show_tokens:
                        # Convert dict messages to LangChain format for counting
                        lc_messages = [
                            to_langchain_message(msg["role"], msg["content"])
                            for msg in messages
                        ]
                        current_tokens = count_message_tokens(
                            lc_messages, model_name or profile.model.model
                        )
                        max_tokens = get_model_token_limit(
                            model_name or profile.model.model
                        )
                        percentage = (current_tokens / max_tokens) * 100
                        print(
                            f"\n📊 Tokens: {current_tokens:,} / {max_tokens:,} ({percentage:.1f}%)\n"
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
                        messages.append(
                            {"role": "assistant", "content": e.partial_response}
                        )
                    else:
                        # Remove user message if we got no response at all
                        if messages and messages[-1]["role"] == "user":
                            messages.pop()

                except Exception as e:
                    print(f"\n❌ Unexpected error: {e}\n")
                    # Remove the user message since we couldn't get a response
                    if messages and messages[-1]["role"] == "user":
                        messages.pop()

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
  # Use default profile
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

    args = parser.parse_args()

    # Validate temperature if provided
    if args.temperature is not None and not 0.0 <= args.temperature <= 2.0:
        print("❌ Error: Temperature must be between 0.0 and 2.0")
        sys.exit(1)

    interactive_chat(
        model_name=args.model,
        profile_name=args.profile,
        temperature=args.temperature,
        show_tokens=args.show_tokens,
    )


if __name__ == "__main__":
    main()
