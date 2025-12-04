#!/usr/bin/env python3
"""Test script for local HuggingFace model chat functionality."""

import sys

from consoul.ai.providers import get_chat_model
from consoul.config.models import HuggingFaceModelConfig


def test_local_huggingface():
    """Test basic chat with a local HuggingFace model."""
    print("Testing local HuggingFace model initialization...")
    print("-" * 60)

    # Use gpt2 - smallest model for testing
    model_name = "gpt2"

    # Create local model config
    print(f"\n1. Creating model config for '{model_name}' (local=True)")
    model_config = HuggingFaceModelConfig(
        model=model_name,
        local=True,
        temperature=0.7,
        max_tokens=100,
    )

    print(f"   ✓ Model config created: {model_config.model}")
    print(f"   ✓ Local execution: {model_config.local}")
    print(f"   ✓ Temperature: {model_config.temperature}")
    print(f"   ✓ Max tokens: {model_config.max_tokens}")

    # Initialize the model
    print("\n2. Initializing chat model...")
    try:
        chat_model = get_chat_model(model_config)
        print("   ✓ Model initialized successfully!")
        print(f"   ✓ Model type: {type(chat_model).__name__}")
    except Exception as e:
        print(f"   ✗ Failed to initialize model: {e}")
        import traceback

        traceback.print_exc()
        return False

    # Test a simple chat message
    print("\n3. Testing chat interaction...")
    test_prompt = "Hello! How are you?"
    print(f"   Prompt: '{test_prompt}'")

    try:
        from langchain_core.messages import HumanMessage

        messages = [HumanMessage(content=test_prompt)]
        print("   Generating response... (this may take a moment)")

        response = chat_model.invoke(messages)

        print("\n   ✓ Response received!")
        print(f"   Response: {response.content}")
        print(f"   Response type: {type(response).__name__}")

        return True

    except Exception as e:
        print(f"   ✗ Chat failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_dependency_check():
    """Verify all required dependencies are available."""
    print("\nChecking dependencies...")
    print("-" * 60)

    dependencies = {
        "transformers": None,
        "torch": None,
        "accelerate": None,
        "langchain_huggingface": None,
    }

    for dep in dependencies:
        try:
            mod = __import__(dep)
            version = getattr(mod, "__version__", "unknown")
            dependencies[dep] = version
            print(f"   ✓ {dep}: {version}")
        except ImportError:
            dependencies[dep] = "NOT INSTALLED"
            print(f"   ✗ {dep}: NOT INSTALLED")

    all_installed = all(v != "NOT INSTALLED" for v in dependencies.values())

    if not all_installed:
        print("\n   ⚠ Some dependencies are missing!")
        print("   Install with: poetry install --extras huggingface-local")
        return False

    print("\n   ✓ All dependencies are installed!")
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("LOCAL HUGGINGFACE MODEL TEST")
    print("=" * 60)

    # Check dependencies first
    if not test_dependency_check():
        print("\n❌ Test aborted: missing dependencies")
        sys.exit(1)

    print("\n" + "=" * 60)

    # Test local model
    success = test_local_huggingface()

    print("\n" + "=" * 60)
    if success:
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ TESTS FAILED")
    print("=" * 60)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
