#!/usr/bin/env python3
"""Image Analysis Examples for Consoul.

This module demonstrates various use cases for the image analysis feature,
including programmatic usage, configuration, and advanced workflows.

Requirements:
    pip install consoul

Usage:
    # Run all examples
    python image-analysis-example.py

    # Run specific example
    python image-analysis-example.py --example debug_screenshot
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for direct imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


def example_basic_single_image():
    """Example 1: Analyze a single image."""
    print("\n" + "=" * 80)
    print("EXAMPLE 1: Basic Single Image Analysis")
    print("=" * 80)

    from consoul.sdk import Consoul

    # Initialize with vision-capable model
    consoul = Consoul(model="claude-3-5-sonnet-20241022", provider="anthropic")

    # Analyze a screenshot
    response = consoul.chat(
        "What error is shown in this screenshot? Suggest a fix.",
        image_paths=["~/screenshots/terminal_error.png"],
    )

    print(f"\nResponse:\n{response}")


def example_multiple_images():
    """Example 2: Analyze multiple images for comparison."""
    print("\n" + "=" * 80)
    print("EXAMPLE 2: Multiple Image Comparison")
    print("=" * 80)

    from consoul.sdk import Consoul

    consoul = Consoul(model="gpt-4o", provider="openai")

    # Compare two UI designs
    response = consoul.chat(
        "Compare these two designs. Which one is better for mobile users?",
        image_paths=["designs/version_a.png", "designs/version_b.png"],
    )

    print(f"\nComparison:\n{response}")


def example_custom_configuration():
    """Example 3: Custom image analysis configuration."""
    print("\n" + "=" * 80)
    print("EXAMPLE 3: Custom Configuration")
    print("=" * 80)

    from consoul.config.models import (
        ConsoulConfig,
        ImageAnalysisToolConfig,
        ToolsConfig,
    )
    from consoul.sdk import Consoul

    # Create custom config with larger file size limit
    config = ConsoulConfig(
        tools=ToolsConfig(
            image_analysis=ImageAnalysisToolConfig(
                enabled=True,
                max_image_size_mb=10.0,  # Allow larger images
                max_images_per_query=3,  # Limit to 3 images
                auto_detect_in_messages=True,
                allowed_extensions=[".png", ".jpg", ".jpeg", ".webp"],
                blocked_paths=["~/.ssh", "/etc", "~/.aws"],
            )
        )
    )

    consoul = Consoul(config=config)

    response = consoul.chat(
        "Analyze this high-resolution architecture diagram",
        image_paths=["diagrams/system_architecture.png"],
    )

    print(f"\nAnalysis:\n{response}")


def example_ui_accessibility_review():
    """Example 4: Automated UI accessibility review."""
    print("\n" + "=" * 80)
    print("EXAMPLE 4: UI Accessibility Review")
    print("=" * 80)

    from consoul.sdk import Consoul

    consoul = Consoul(model="claude-3-5-sonnet-20241022")

    # Detailed accessibility audit
    response = consoul.chat(
        """Review this interface for WCAG 2.1 compliance.

        Check for:
        - Color contrast ratios
        - Text readability
        - Button sizes
        - Keyboard navigation indicators
        - Screen reader compatibility
        - Focus states

        Provide specific recommendations for improvements.""",
        image_paths=["ui_mockups/login_screen.png"],
    )

    print(f"\nAccessibility Report:\n{response}")


def example_code_extraction():
    """Example 5: Extract code from screenshots."""
    print("\n" + "=" * 80)
    print("EXAMPLE 5: Code Extraction from Screenshot")
    print("=" * 80)

    from consoul.sdk import Consoul

    consoul = Consoul(model="gpt-4o")

    # Extract and explain code from screenshot
    response = consoul.chat(
        """Extract the code from this screenshot and:
        1. Explain what it does
        2. Identify any potential bugs
        3. Suggest improvements
        4. Provide the extracted code in markdown format""",
        image_paths=["screenshots/code_snippet.png"],
    )

    print(f"\nCode Analysis:\n{response}")


def example_batch_processing():
    """Example 6: Batch process multiple screenshots."""
    print("\n" + "=" * 80)
    print("EXAMPLE 6: Batch Processing Screenshots")
    print("=" * 80)

    from pathlib import Path

    from consoul.sdk import Consoul

    consoul = Consoul(model="claude-3-5-sonnet-20241022")

    # Process all error screenshots in a directory
    screenshots_dir = Path("screenshots/errors")
    results = []

    for screenshot in screenshots_dir.glob("*.png"):
        print(f"\nProcessing: {screenshot.name}")

        response = consoul.chat(
            f"Analyze this error and provide a fix: {screenshot.name}",
            image_paths=[str(screenshot)],
        )

        results.append({"file": screenshot.name, "analysis": response})

    # Generate summary report
    print("\n" + "-" * 80)
    print("SUMMARY REPORT")
    print("-" * 80)

    for result in results:
        print(f"\n{result['file']}:")
        print(f"  {result['analysis'][:100]}...")


def example_design_workflow():
    """Example 7: Complete design review workflow."""
    print("\n" + "=" * 80)
    print("EXAMPLE 7: Design Review Workflow")
    print("=" * 80)

    from consoul.sdk import Consoul

    consoul = Consoul(model="claude-3-5-sonnet-20241022")

    # Step 1: Initial design review
    print("\n[Step 1] Initial Review")
    initial_review = consoul.chat(
        """Review this mobile app mockup for:
        - Visual hierarchy
        - Color scheme
        - Typography
        - Layout consistency
        - User flow clarity""",
        image_paths=["designs/mobile_app_v1.png"],
    )
    print(initial_review)

    # Step 2: Comparison with updated version
    print("\n[Step 2] Compare with Updated Version")
    comparison = consoul.chat(
        "Compare the original design with this updated version. What improved?",
        image_paths=["designs/mobile_app_v1.png", "designs/mobile_app_v2.png"],
    )
    print(comparison)

    # Step 3: Final recommendations
    print("\n[Step 3] Final Recommendations")
    recommendations = consoul.chat(
        "Based on the updated design, provide final recommendations before development."
    )
    print(recommendations)


def example_diagram_documentation():
    """Example 8: Generate documentation from diagrams."""
    print("\n" + "=" * 80)
    print("EXAMPLE 8: Diagram Documentation Generation")
    print("=" * 80)

    from consoul.sdk import Consoul

    consoul = Consoul(model="gemini-2.0-flash", provider="google")

    # Generate markdown documentation from architecture diagram
    response = consoul.chat(
        """Analyze this system architecture diagram and generate markdown documentation including:

        # System Architecture

        ## Overview
        [Brief description]

        ## Components
        [List and describe each component]

        ## Data Flow
        [Explain how data moves through the system]

        ## Technologies
        [Identify technologies shown]

        ## Integration Points
        [Describe how components integrate]

        Use proper markdown formatting with headers, lists, and code blocks.""",
        image_paths=["diagrams/architecture.png"],
    )

    # Save to file
    output_path = Path("docs/architecture.md")
    output_path.write_text(response)
    print(f"\nDocumentation saved to: {output_path}")
    print(f"\nPreview:\n{response[:500]}...")


def example_error_handling():
    """Example 9: Proper error handling for image analysis."""
    print("\n" + "=" * 80)
    print("EXAMPLE 9: Error Handling")
    print("=" * 80)

    from consoul.exceptions import ConsoulError

    from consoul.sdk import Consoul

    consoul = Consoul(model="claude-3-5-sonnet-20241022")

    # Example 1: Handle missing file
    try:
        consoul.chat("Analyze this image", image_paths=["nonexistent.png"])
    except FileNotFoundError as e:
        print(f"✗ File not found: {e}")

    # Example 2: Handle file too large
    try:
        from consoul.ai.tools.implementations.analyze_images import (
            set_analyze_images_config,
        )
        from consoul.config.models import ImageAnalysisToolConfig

        # Set strict size limit
        config = ImageAnalysisToolConfig(max_image_size_mb=0.1)
        set_analyze_images_config(config)

        consoul.chat("Analyze this large image", image_paths=["large_image.png"])
    except ValueError as e:
        print(f"✗ File too large: {e}")

    # Example 3: Handle invalid model
    try:
        consoul_text = Consoul(model="gpt-3.5-turbo")  # Not vision-capable
        consoul_text.chat("Analyze this image", image_paths=["screenshot.png"])
    except ConsoulError as e:
        print(f"✗ Model doesn't support vision: {e}")
        print("  Suggestion: Use gpt-4o, claude-3-5-sonnet, or gemini-2.0-flash")


def example_local_model():
    """Example 10: Use local Ollama model for privacy."""
    print("\n" + "=" * 80)
    print("EXAMPLE 10: Local Vision Model (Ollama)")
    print("=" * 80)

    from consoul.sdk import Consoul

    # Use local LLaVA model (fully private, no cloud)
    consoul = Consoul(model="llava:latest", provider="ollama")

    print("Using local Ollama model - no data sent to cloud")

    response = consoul.chat(
        "Describe this image in detail", image_paths=["~/Pictures/photo.jpg"]
    )

    print(f"\nLocal Analysis:\n{response}")


def example_streaming_response():
    """Example 11: Stream image analysis responses."""
    print("\n" + "=" * 80)
    print("EXAMPLE 11: Streaming Response")
    print("=" * 80)

    from consoul.sdk import Consoul

    consoul = Consoul(model="claude-3-5-sonnet-20241022")

    print("\nAnalyzing image (streaming)...\n")

    # Stream the response token by token
    for chunk in consoul.chat_stream(
        "Provide a detailed analysis of this UI design",
        image_paths=["designs/dashboard.png"],
    ):
        print(chunk, end="", flush=True)

    print("\n")


def main():
    """Run all examples or a specific one."""
    import argparse

    parser = argparse.ArgumentParser(description="Consoul Image Analysis Examples")
    parser.add_argument(
        "--example",
        choices=[
            "basic",
            "multiple",
            "config",
            "accessibility",
            "code",
            "batch",
            "workflow",
            "documentation",
            "errors",
            "local",
            "streaming",
        ],
        help="Run a specific example",
    )

    args = parser.parse_args()

    examples = {
        "basic": example_basic_single_image,
        "multiple": example_multiple_images,
        "config": example_custom_configuration,
        "accessibility": example_ui_accessibility_review,
        "code": example_code_extraction,
        "batch": example_batch_processing,
        "workflow": example_design_workflow,
        "documentation": example_diagram_documentation,
        "errors": example_error_handling,
        "local": example_local_model,
        "streaming": example_streaming_response,
    }

    if args.example:
        examples[args.example]()
    else:
        print("Running all examples...\n")
        for name, func in examples.items():
            try:
                func()
            except Exception as e:
                print(f"\n✗ Example '{name}' failed: {e}")
                continue


if __name__ == "__main__":
    main()
