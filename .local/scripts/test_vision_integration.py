#!/usr/bin/env python3
"""Standalone integration test for multimodal vision capabilities.

Tests the complete pipeline:
1. analyze_images tool - validates and encodes images
2. format_vision_message - formats for LangChain providers
3. Actual LangChain provider invocation (if API keys available)

Usage:
    python test_vision_integration.py
"""

import json
import os
from pathlib import Path

# Test if we're in the right environment
try:
    from langchain_core.messages import HumanMessage

    from consoul.ai.multimodal import format_vision_message
    from consoul.ai.tools.implementations.analyze_images import (
        analyze_images,
        set_analyze_images_config,
    )
    from consoul.config.models import ImageAnalysisToolConfig, Provider
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nMake sure you're in the consoul virtual environment:")
    print("  poetry shell")
    print("  python test_vision_integration.py")
    exit(1)


def test_analyze_images_tool():
    """Test Step 1: Image validation and encoding."""
    print("=" * 80)
    print("STEP 1: Testing analyze_images tool")
    print("=" * 80)

    # Use test fixtures
    fixtures_dir = Path(__file__).parent / "tests" / "fixtures"
    test_image = fixtures_dir / "test_image.png"

    if not test_image.exists():
        print(f"❌ Test image not found: {test_image}")
        return None

    print(f"✅ Found test image: {test_image}")

    # Configure tool
    set_analyze_images_config(ImageAnalysisToolConfig())

    # Invoke tool
    result = analyze_images.invoke(
        {"query": "What color is this square?", "image_paths": [str(test_image)]}
    )

    # Check for errors
    if result.startswith("❌"):
        print(f"❌ Tool returned error: {result}")
        return None

    # Parse JSON result
    try:
        data = json.loads(result)
        print("✅ Tool returned valid JSON")
        print(f"   Query: {data['query']}")
        print(f"   Images: {len(data['images'])}")
        print(f"   First image path: {data['images'][0]['path']}")
        print(f"   MIME type: {data['images'][0]['mime_type']}")
        print(f"   Base64 length: {len(data['images'][0]['data'])} chars")
        return data
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON: {e}")
        return None


def test_format_vision_message(images_data):
    """Test Step 2: Format for each LangChain provider."""
    print("\n" + "=" * 80)
    print("STEP 2: Testing format_vision_message for each provider")
    print("=" * 80)

    query = images_data["query"]
    images = images_data["images"]

    results = {}

    for provider in [
        Provider.ANTHROPIC,
        Provider.OPENAI,
        Provider.GOOGLE,
        Provider.OLLAMA,
    ]:
        print(f"\nTesting {provider.value}...")

        try:
            message = format_vision_message(provider, query, images)

            # Validate it's a HumanMessage
            if not isinstance(message, HumanMessage):
                print(f"  ❌ Not a HumanMessage: {type(message)}")
                continue

            print("  ✅ Returned HumanMessage")
            print(f"     Content blocks: {len(message.content)}")
            print(f"     First block type: {message.content[0]['type']}")
            print(f"     Second block type: {message.content[1]['type']}")

            # Provider-specific validation
            if provider == Provider.ANTHROPIC:
                assert message.content[1]["type"] == "image"
                assert "source" in message.content[1]
                assert message.content[1]["source"]["type"] == "base64"
                print("     ✅ Anthropic structure validated")

            elif provider == Provider.OPENAI:
                assert message.content[1]["type"] == "image_url"
                assert "image_url" in message.content[1]
                assert message.content[1]["image_url"]["url"].startswith("data:")
                print("     ✅ OpenAI structure validated")

            elif provider == Provider.GOOGLE:
                assert message.content[1]["type"] == "image"
                assert "base64" in message.content[1]
                assert "mime_type" in message.content[1]
                print("     ✅ Google structure validated")

            elif provider == Provider.OLLAMA:
                assert message.content[1]["type"] == "image"
                assert message.content[1]["source_type"] == "base64"
                assert "data" in message.content[1]
                print("     ✅ Ollama structure validated")

            results[provider] = message

        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback

            traceback.print_exc()

    return results


def test_langchain_integration(messages):
    """Test Step 3: Actual LangChain provider invocation (if API keys available)."""
    print("\n" + "=" * 80)
    print("STEP 3: Testing actual LangChain provider invocation")
    print("=" * 80)

    # Check for API keys
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_google = bool(os.getenv("GOOGLE_API_KEY"))
    has_ollama = True  # Ollama runs locally

    print("\nAPI Key Status:")
    print(
        f"  Anthropic: {'✅ Available' if has_anthropic else '❌ Missing (set ANTHROPIC_API_KEY)'}"
    )
    print(
        f"  OpenAI: {'✅ Available' if has_openai else '❌ Missing (set OPENAI_API_KEY)'}"
    )
    print(
        f"  Google: {'✅ Available' if has_google else '❌ Missing (set GOOGLE_API_KEY)'}"
    )
    print(f"  Ollama: {'✅ Local' if has_ollama else '❌ Not running'}")

    # Test Anthropic if available
    if has_anthropic and Provider.ANTHROPIC in messages:
        print("\n🧪 Testing Anthropic ChatAnthropic...")
        try:
            from langchain_anthropic import ChatAnthropic

            chat = ChatAnthropic(model="claude-opus-4-1-20250805", max_tokens=100)
            response = chat.invoke([messages[Provider.ANTHROPIC]])
            print(f"  ✅ SUCCESS! Response: {response.content[:100]}...")
        except Exception as e:
            print(f"  ❌ Error: {e}")

    # Test OpenAI if available
    if has_openai and Provider.OPENAI in messages:
        print("\n🧪 Testing OpenAI ChatOpenAI...")
        try:
            from langchain_openai import ChatOpenAI

            chat = ChatOpenAI(model="gpt-5-mini", max_tokens=100)
            response = chat.invoke([messages[Provider.OPENAI]])
            print(f"  ✅ SUCCESS! Response: {response.content[:100]}...")
        except Exception as e:
            print(f"  ❌ Error: {e}")

    # Test Google if available
    if has_google and Provider.GOOGLE in messages:
        print("\n🧪 Testing Google ChatGoogleGenerativeAI...")
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            chat = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash", max_output_tokens=100
            )
            response = chat.invoke([messages[Provider.GOOGLE]])
            print(f"  ✅ SUCCESS! Response: {response.content[:100]}...")
        except Exception as e:
            print(f"  ❌ Error: {e}")

    # Test Ollama if available
    if has_ollama and Provider.OLLAMA in messages:
        print("\n🧪 Testing Ollama ChatOllama (qwen3-vl)...")
        try:
            # Check if Ollama is running
            import requests
            from langchain_ollama import ChatOllama

            try:
                requests.get("http://localhost:11434", timeout=2)
            except requests.exceptions.RequestException:
                print("  ⚠️  Ollama not running (http://localhost:11434)")
                print("      Start with: ollama serve")
                return

            chat = ChatOllama(model="qwen3-vl:8b", num_predict=100)
            response = chat.invoke([messages[Provider.OLLAMA]])
            print(f"  ✅ SUCCESS! Response: {response.content[:100]}...")
        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback

            traceback.print_exc()

    # Summary
    print("\n" + "=" * 80)
    print("INTEGRATION TEST SUMMARY")
    print("=" * 80)
    if not (has_anthropic or has_openai or has_google):
        print("\n⚠️  No API keys found. Set environment variables to test providers:")
        print("   export ANTHROPIC_API_KEY='sk-...'")
        print("   export OPENAI_API_KEY='sk-...'")
        print("   export GOOGLE_API_KEY='...'")
        print("\nOr test locally with Ollama:")
        print("   ollama pull qwen2-vl:latest")
        print("   ollama serve")


def main():
    """Run all integration tests."""
    print("\n" + "=" * 80)
    print("MULTIMODAL VISION INTEGRATION TEST")
    print("=" * 80)
    print("\nThis script tests the complete multimodal vision pipeline:")
    print("  1. analyze_images tool (validation + encoding)")
    print("  2. format_vision_message (LangChain formatting)")
    print("  3. Actual provider invocation (if API keys available)")

    # Step 1: Test analyze_images tool
    images_data = test_analyze_images_tool()
    if not images_data:
        print("\n❌ Step 1 failed. Exiting.")
        return

    # Step 2: Test format_vision_message
    messages = test_format_vision_message(images_data)
    if not messages:
        print("\n❌ Step 2 failed. Exiting.")
        return

    # Step 3: Test actual LangChain providers
    test_langchain_integration(messages)

    print("\n✅ Integration test complete!\n")


if __name__ == "__main__":
    main()
