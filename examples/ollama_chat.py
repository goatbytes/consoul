#!/usr/bin/env python3
"""Ollama local chat example demonstrating offline AI capabilities.

This example showcases:
- Local Ollama model usage (no API keys required)
- Offline operation (works without internet)
- Ollama service detection and helpful error messages
- Model availability checking
- Popular open-source models (Llama 3, Mistral, CodeLlama, Phi, Qwen)
- Interactive chat with conversation history

Prerequisites:
    1. Install Ollama: https://ollama.com
    2. Start Ollama service: ollama serve
    3. Pull a model: ollama pull llama3

Usage:
    # Use default model (llama3)
    python examples/ollama_chat.py

    # Use specific model
    python examples/ollama_chat.py --model mistral
    python examples/ollama_chat.py --model codellama
    python examples/ollama_chat.py --model phi

    # Adjust temperature
    python examples/ollama_chat.py --model llama3 --temperature 0.9
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import argparse

from langchain_core.messages import AIMessage, HumanMessage

from consoul.ai import get_chat_model, stream_response
from consoul.ai.exceptions import OllamaServiceError, StreamingError
from consoul.ai.providers import is_ollama_running


def print_banner() -> None:
    """Print welcome banner."""
    print("\n" + "=" * 60)
    print("  Consoul Ollama Chat - Local AI Assistant")
    print("=" * 60)
    print("\n✨ Running locally with no API keys required!")
    print("🔒 All data stays on your machine\n")
    print("Type 'exit' or 'quit' to end the session")
    print("Type 'help' for available commands\n")


def print_help() -> None:
    """Print help information."""
    print("\nAvailable commands:")
    print("  exit, quit  - End the chat session")
    print("  help        - Show this help message")
    print("  clear       - Clear conversation history")
    print("  models      - Show popular Ollama models")
    print("  status      - Check Ollama service status")
    print()


def print_popular_models() -> None:
    """Print information about popular Ollama models."""
    print("\n" + "-" * 60)
    print("Popular Ollama Models:")
    print("-" * 60)
    print("  llama3        - Meta's Llama 3 (8B/70B) - General purpose")
    print("  mistral       - Mistral 7B - Fast and efficient")
    print("  codellama     - Code Llama - Specialized for coding")
    print("  phi           - Microsoft Phi-2 - Compact but capable")
    print("  qwen          - Alibaba Qwen - Multilingual support")
    print("  gemma         - Google Gemma - Lightweight model")
    print("\nTo download a model:")
    print("  ollama pull <model-name>")
    print("\nTo list installed models:")
    print("  ollama list")
    print("-" * 60 + "\n")


def check_ollama_status() -> None:
    """Check and display Ollama service status."""
    from consoul.config.env import get_ollama_api_base

    base_url = get_ollama_api_base()
    if not base_url:
        base_url = "http://localhost:11434"

    print("\n" + "-" * 60)
    print("Ollama Service Status:")
    print("-" * 60)

    if is_ollama_running(base_url):
        print("✅ Ollama service is running")
        print(f"   Endpoint: {base_url}")

        # Try to get list of models
        try:
            import requests

            response = requests.get(f"{base_url}/api/tags", timeout=2)
            if response.status_code == 200:
                models = response.json().get("models", [])
                if models:
                    print(f"\n📦 Installed models ({len(models)}):")
                    for model in models:
                        name = model.get("name", "unknown")
                        size_bytes = model.get("size", 0)
                        size_gb = size_bytes / (1024**3)
                        print(f"   • {name} ({size_gb:.1f} GB)")
                else:
                    print("\n⚠️  No models installed yet")
                    print("   Install a model: ollama pull llama3")
        except Exception as e:
            print(f"\n⚠️  Could not fetch model list: {e}")
    else:
        print("❌ Ollama service is not running")
        print("\n   To start Ollama:")
        print("   1. Install from: https://ollama.com")
        print("   2. Run: ollama serve")

    print("-" * 60 + "\n")


def ollama_chat(
    model_name: str = "llama3",
    temperature: float = 0.7,
) -> None:
    """Run interactive Ollama chat session.

    Args:
        model_name: Ollama model name (e.g., "llama3", "mistral")
        temperature: Temperature for response randomness (0.0-2.0)
    """
    print_banner()

    # Get Ollama base URL from config/env
    from consoul.config.env import get_ollama_api_base

    base_url = get_ollama_api_base()
    if not base_url:
        base_url = "http://localhost:11434"

    # Check Ollama service status first
    if not is_ollama_running(base_url):
        print("❌ Ollama service is not running!\n")
        print(f"Expected endpoint: {base_url}")
        print("\nTo use Ollama:")
        print("1. Install Ollama: https://ollama.com")
        print("2. Start service: ollama serve")
        print("3. Pull a model: ollama pull llama3")
        if base_url != "http://localhost:11434":
            print(f"\nNote: Using custom endpoint from OLLAMA_API_BASE: {base_url}")
        print("\nRun 'ollama --help' for more information.\n")
        return

    try:
        # Initialize Ollama chat model
        print(f"🔧 Initializing model: {model_name}")
        print(f"🌡️  Temperature: {temperature}")

        chat_model = get_chat_model(
            model_name,
            temperature=temperature,
        )

        print("✅ Model loaded successfully")
        print("💾 Running locally - no internet required!")
        print()

        # Conversation history (use LangChain BaseMessage objects)
        messages: list[HumanMessage | AIMessage] = []

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

                if user_input.lower() == "models":
                    print_popular_models()
                    continue

                if user_input.lower() == "status":
                    check_ollama_status()
                    continue

                # Add user message to history
                messages.append(HumanMessage(content=user_input))

                # Stream AI response
                print()  # Newline before streaming starts

                try:
                    # stream_response now returns (text, ai_message) tuple
                    # Pass BaseMessage objects directly (not dicts)
                    _, ai_message = stream_response(chat_model, messages)

                    # Add assistant message to history
                    messages.append(ai_message)

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
                        messages.append(AIMessage(content=e.partial_response))
                    else:
                        # Remove user message if we got no response at all
                        if messages and isinstance(messages[-1], HumanMessage):
                            messages.pop()

                except Exception as e:
                    print(f"\n❌ Unexpected error: {e}\n")
                    # Remove the user message since we couldn't get a response
                    if messages and isinstance(messages[-1], HumanMessage):
                        messages.pop()

            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!\n")
                break
            except EOFError:
                print("\n\n👋 Goodbye!\n")
                break

    except OllamaServiceError as e:
        print(f"\n❌ Ollama Error:\n{e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}\n")
        import traceback

        traceback.print_exc()
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Interactive chat with local Ollama models",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Use default model (llama3)
  python examples/ollama_chat.py

  # Use Mistral model
  python examples/ollama_chat.py --model mistral

  # Use CodeLlama for coding assistance
  python examples/ollama_chat.py --model codellama

  # Adjust temperature for more creative responses
  python examples/ollama_chat.py --model llama3 --temperature 0.9

Popular models:
  llama3       - Meta's Llama 3 (general purpose)
  mistral      - Mistral 7B (fast and efficient)
  codellama    - Code Llama (coding assistance)
  phi          - Microsoft Phi-2 (compact)
  qwen         - Alibaba Qwen (multilingual)

Getting started:
  1. Install Ollama: https://ollama.com
  2. Start service: ollama serve
  3. Pull a model: ollama pull llama3
  4. Run this script!
        """,
    )

    parser.add_argument(
        "--model",
        "-m",
        default="llama3",
        help="Ollama model name (default: llama3)",
    )
    parser.add_argument(
        "--temperature",
        "-t",
        type=float,
        default=0.7,
        help="Temperature for response randomness (0.0-2.0, default: 0.7)",
    )
    parser.add_argument(
        "--check-status",
        action="store_true",
        help="Check Ollama status and exit",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="Show popular models and exit",
    )

    args = parser.parse_args()

    # Handle info commands
    if args.check_status:
        check_ollama_status()
        return

    if args.list_models:
        print_popular_models()
        return

    # Validate temperature
    if not 0.0 <= args.temperature <= 2.0:
        print("❌ Error: Temperature must be between 0.0 and 2.0")
        sys.exit(1)

    ollama_chat(
        model_name=args.model,
        temperature=args.temperature,
    )


if __name__ == "__main__":
    main()
