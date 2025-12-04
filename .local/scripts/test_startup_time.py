#!/usr/bin/env python3
"""Test TUI startup time with different providers."""

import time


def test_config_load(provider_name: str):
    """Test config loading time for a specific provider."""
    print(f"\nTesting with provider: {provider_name}")

    # Change provider
    from pathlib import Path

    from consoul.config import load_config, save_config
    from consoul.config.models import Provider

    config = load_config()
    original_provider = config.current_provider
    original_model = config.current_model

    try:
        # Set test provider
        if provider_name == "huggingface":
            config.current_provider = Provider.HUGGINGFACE
            config.current_model = "gpt2"
        elif provider_name == "ollama":
            config.current_provider = Provider.OLLAMA
            config.current_model = "llama3.2"
        else:
            config.current_provider = Provider.OPENAI
            config.current_model = "gpt-4o"

        save_config(config, Path.home() / ".consoul" / "config.yaml")

        # Measure get_current_model_config time
        start = time.time()
        model_config = config.get_current_model_config()
        elapsed = (time.time() - start) * 1000

        print(f"  get_current_model_config(): {elapsed:.0f}ms")
        if hasattr(model_config, "local"):
            print(f"  local={model_config.local}")

    finally:
        # Restore original
        config.current_provider = original_provider
        config.current_model = original_model
        save_config(config, Path.home() / ".consoul" / "config.yaml")


def main():
    """Test startup time with different providers."""
    print("=" * 60)
    print("TUI STARTUP TIME TEST")
    print("=" * 60)

    test_config_load("openai")
    test_config_load("ollama")
    test_config_load("huggingface")

    print("\n" + "=" * 60)
    print("If HuggingFace shows >1000ms, the cache scan is still happening!")
    print("=" * 60)


if __name__ == "__main__":
    main()
