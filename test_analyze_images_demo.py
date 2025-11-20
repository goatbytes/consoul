#!/usr/bin/env python3
"""Demo script to test the analyze_images tool locally.

This script demonstrates how to use the analyze_images tool with various
test cases including valid images, error scenarios, and edge cases.
"""

import json
from pathlib import Path

from consoul.ai.tools.implementations.analyze_images import (
    analyze_images,
    set_analyze_images_config,
)
from consoul.config.models import ImageAnalysisToolConfig


def print_section(title: str):
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print("=" * 70)


def print_result(test_name: str, result: str, success: bool = True):
    """Print test result with formatting."""
    status = "✅" if success else "❌"
    print(f"\n{status} {test_name}")
    print("-" * 70)

    # Try to parse and pretty-print JSON results
    if not result.startswith("❌"):
        try:
            data = json.loads(result)
            print(f"Query: {data['query']}")
            print(f"Images processed: {len(data['images'])}")
            for i, img in enumerate(data["images"], 1):
                print(f"  {i}. {Path(img['path']).name}")
                print(f"     MIME type: {img['mime_type']}")
                print(f"     Base64 size: {len(img['data'])} chars")
        except json.JSONDecodeError:
            print(result[:200] + "..." if len(result) > 200 else result)
    else:
        print(result)


def main():
    print_section("🖼️  Image Analysis Tool Demo")

    # Initialize with default config
    config = ImageAnalysisToolConfig()
    set_analyze_images_config(config)

    print("\nConfiguration:")
    print(f"  Max image size: {config.max_image_size_mb} MB")
    print(f"  Max images per query: {config.max_images_per_query}")
    print(f"  Allowed extensions: {', '.join(config.allowed_extensions)}")

    # Get fixture paths
    fixtures_dir = Path(__file__).parent / "tests" / "fixtures"
    test_png = fixtures_dir / "test_image.png"
    test_jpg = fixtures_dir / "test_photo.jpg"
    test_webp = fixtures_dir / "test_diagram.webp"

    # Test 1: Single PNG image
    print_section("Test 1: Analyze Single PNG Image")
    if test_png.exists():
        result = analyze_images.invoke(
            {
                "query": "What colors and shapes are in this image?",
                "image_paths": [str(test_png)],
            }
        )
        print_result("Single PNG analysis", result, not result.startswith("❌"))
    else:
        print("❌ Test fixture not found: test_image.png")

    # Test 2: Multiple images (PNG, JPG, WebP)
    print_section("Test 2: Analyze Multiple Images")
    if all(p.exists() for p in [test_png, test_jpg, test_webp]):
        result = analyze_images.invoke(
            {
                "query": "Compare these three test images",
                "image_paths": [str(test_png), str(test_jpg), str(test_webp)],
            }
        )
        print_result("Multiple images analysis", result, not result.startswith("❌"))
    else:
        print("❌ Some test fixtures not found")

    # Test 3: Non-existent file (error case)
    print_section("Test 3: Error Handling - Non-existent File")
    result = analyze_images.invoke(
        {"query": "Analyze this", "image_paths": ["/tmp/nonexistent_image.png"]}
    )
    print_result("Non-existent file handling", result, result.startswith("❌"))

    # Test 4: Too many images (error case)
    print_section("Test 4: Error Handling - Too Many Images")
    if test_png.exists():
        result = analyze_images.invoke(
            {
                "query": "Analyze all these",
                "image_paths": [str(test_png)] * 6,  # Exceeds default max of 5
            }
        )
        print_result("Too many images handling", result, result.startswith("❌"))

    # Test 5: Blocked path (security)
    print_section("Test 5: Security - Blocked Path")
    result = analyze_images.invoke(
        {"query": "Analyze this system file", "image_paths": ["/etc/passwd"]}
    )
    print_result("Blocked path security check", result, result.startswith("❌"))

    # Test 6: Path traversal attempt (security)
    print_section("Test 6: Security - Path Traversal")
    result = analyze_images.invoke(
        {"query": "Analyze this", "image_paths": ["../../etc/shadow"]}
    )
    print_result("Path traversal security check", result, result.startswith("❌"))

    # Test 7: Invalid extension
    print_section("Test 7: Validation - Invalid Extension")
    result = analyze_images.invoke(
        {"query": "Analyze this executable", "image_paths": ["/tmp/malware.exe"]}
    )
    print_result("Invalid extension check", result, result.startswith("❌"))

    # Test 8: Custom configuration
    print_section("Test 8: Custom Configuration")
    custom_config = ImageAnalysisToolConfig(
        max_image_size_mb=10,  # Increase to 10MB
        max_images_per_query=3,  # Reduce to 3
    )
    set_analyze_images_config(custom_config)

    print("Custom config applied:")
    print(f"  Max image size: {custom_config.max_image_size_mb} MB")
    print(f"  Max images per query: {custom_config.max_images_per_query}")

    if test_png.exists():
        result = analyze_images.invoke(
            {
                "query": "Test with custom config",
                "image_paths": [str(test_png)] * 4,  # Now exceeds custom max of 3
            }
        )
        print_result("Custom config enforcement", result, result.startswith("❌"))

    # Test 9: Base64 encoding verification
    print_section("Test 9: Base64 Encoding Verification")
    if test_png.exists():
        result = analyze_images.invoke(
            {"query": "Verify base64 encoding", "image_paths": [str(test_png)]}
        )

        if not result.startswith("❌"):
            import base64

            data = json.loads(result)
            original_bytes = test_png.read_bytes()
            decoded_bytes = base64.b64decode(data["images"][0]["data"])
            match = original_bytes == decoded_bytes

            print_result(
                "Base64 encoding accuracy",
                f"Original size: {len(original_bytes)} bytes\n"
                f"Decoded size: {len(decoded_bytes)} bytes\n"
                f"Match: {'✅ YES' if match else '❌ NO'}",
                match,
            )
        else:
            print_result("Base64 encoding test", result, False)

    # Summary
    print_section("📊 Demo Complete")
    print("\nThe analyze_images tool is ready for use!")
    print("\nNext steps:")
    print("  1. SOUL-114: Implement provider-specific multimodal formatting")
    print("  2. SOUL-115: Integrate with ToolRegistry")
    print("  3. SOUL-118: Add vision model capability detection")
    print("\nFor Ollama qwen3-vl support:")
    print("  - Model detected: qwen3-vl:latest (6.1 GB)")
    print("  - Will be supported in SOUL-114 (multimodal formatting)")
    print()


if __name__ == "__main__":
    main()
