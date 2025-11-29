#!/usr/bin/env python3
"""Interactive test script for the analyze_images tool.

Run this script to interactively test the analyze_images tool with your own images.
"""

import json
import sys
from pathlib import Path

from consoul.ai.tools.implementations.analyze_images import (
    analyze_images,
    set_analyze_images_config,
)
from consoul.config.models import ImageAnalysisToolConfig


def main():
    print("🖼️  Interactive Image Analysis Tool Test")
    print("=" * 70)

    # Initialize config
    config = ImageAnalysisToolConfig()
    set_analyze_images_config(config)

    print("\nConfiguration:")
    print(f"  Max image size: {config.max_image_size_mb} MB")
    print(f"  Max images per query: {config.max_images_per_query}")
    print(f"  Allowed extensions: {', '.join(config.allowed_extensions)}")

    # Get image path(s) from command line or prompt
    if len(sys.argv) > 1:
        image_paths = sys.argv[1:]
        print(f"\nUsing images from command line: {image_paths}")
    else:
        print("\n" + "=" * 70)
        print(
            "Usage: python3 test_analyze_images_interactive.py <image_path> [<image_path2> ...]"
        )
        print("\nOr use test fixtures:")
        print(
            "  python3 test_analyze_images_interactive.py tests/fixtures/test_image.png"
        )
        print("=" * 70)

        image_input = input("\nEnter image path(s) separated by spaces: ").strip()
        if not image_input:
            print("No images provided. Exiting.")
            return

        image_paths = image_input.split()

    # Get query
    query = input("\nEnter your query about the image(s): ").strip()
    if not query:
        query = "Describe this image in detail"
        print(f"Using default query: '{query}'")

    # Invoke the tool
    print("\n" + "=" * 70)
    print("Processing...")
    print("=" * 70)

    try:
        result = analyze_images.invoke({"query": query, "image_paths": image_paths})

        # Display results
        if result.startswith("❌"):
            print(f"\n❌ Error: {result[2:]}")
            return

        # Parse and display JSON
        data = json.loads(result)

        print("\n✅ Success!")
        print(f"\nQuery: {data['query']}")
        print(f"Images processed: {len(data['images'])}")

        for i, img in enumerate(data["images"], 1):
            path = Path(img["path"])
            print(f"\n  Image {i}:")
            print(f"    Path: {path}")
            print(f"    Name: {path.name}")
            print(f"    MIME type: {img['mime_type']}")
            print(f"    Base64 encoded: {len(img['data'])} characters")
            print(f"    Estimated size: {len(img['data']) * 3 // 4} bytes")

        # Show how to use the result
        print("\n" + "=" * 70)
        print("📝 Next Steps:")
        print("=" * 70)
        print("\nThis JSON output is ready to be sent to a vision-capable LLM:")
        print("  • Anthropic Claude 3+ (Opus, Sonnet, Haiku, 3.5 Sonnet)")
        print("  • OpenAI GPT-4o, GPT-4o-mini, GPT-4V")
        print("  • Google Gemini 2.0 Flash, Gemini 1.5 Pro")
        print("  • Ollama qwen3-vl, llava, bakllava")

        print("\n📋 Raw JSON Output (first 500 chars):")
        print("-" * 70)
        result_preview = result[:500] + "..." if len(result) > 500 else result
        print(result_preview)

        # Ask if user wants to save JSON
        save = input("\nSave full JSON to file? (y/N): ").strip().lower()
        if save == "y":
            output_file = "analyze_images_output.json"
            Path(output_file).write_text(result)
            print(f"✅ Saved to {output_file}")

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
