#!/usr/bin/env python3
"""Utility to update model pricing data from provider websites.

This script helps maintain accurate pricing by scraping official provider
pricing pages and generating updated pricing dictionaries for consoul/pricing.py.

Usage:
    # Interactive mode - prompts for provider
    python scripts/update_pricing.py

    # Specific provider
    python scripts/update_pricing.py --provider openai
    python scripts/update_pricing.py --provider anthropic
    python scripts/update_pricing.py --provider google

    # From markdown (copied from pricing page)
    python scripts/update_pricing.py --from-markdown pricing.md

    # Output Python dict directly
    python scripts/update_pricing.py --provider openai --format python
"""

import argparse
import json
import re
import sys
from pathlib import Path


def parse_openai_markdown(markdown: str) -> dict[str, dict[str, float]]:
    """Parse OpenAI pricing from markdown format.

    Expected format (from openai.com/api/pricing):
        | Model | Input | Output |
        |-------|-------|--------|
        | gpt-4o | $5.00 / 1M tokens | $20.00 / 1M tokens |
    """
    pricing = {}

    # Match table rows with pricing
    # Pattern: | model-name | $X.XX / 1M tokens | $Y.YY / 1M tokens |
    pattern = r"\|\s*([a-z0-9-]+)\s*\|\s*\$?([\d.]+)\s*(?:/\s*1M?)?\s*(?:tokens?)?\s*\|\s*\$?([\d.]+)\s*(?:/\s*1M?)?\s*(?:tokens?)?\s*\|"

    for match in re.finditer(pattern, markdown, re.MULTILINE | re.IGNORECASE):
        model = match.group(1).strip()
        input_price = float(match.group(2))
        output_price = float(match.group(3))

        pricing[model] = {
            "input": input_price,
            "output": output_price,
        }

    return pricing


def parse_anthropic_markdown(markdown: str) -> dict[str, dict[str, float]]:
    """Parse Anthropic pricing from markdown format.

    Expected format (from claude.com/pricing):
        | Model | Input | Output | Cache Write | Cache Read |
    """
    pricing = {}

    # More flexible pattern for Anthropic
    lines = markdown.split("\n")
    current_model = None

    for line in lines:
        # Look for model names
        if "claude" in line.lower():
            # Extract model identifier
            model_match = re.search(r"claude[- ][\w.-]+", line, re.IGNORECASE)
            if model_match:
                current_model = model_match.group(0).lower().replace(" ", "-")

        # Look for pricing in format: $X / MTok or $X per million
        prices = re.findall(
            r"\$?([\d.]+)\s*(?:/|per)\s*(?:MTok|million|1M)", line, re.IGNORECASE
        )

        if current_model and len(prices) >= 2:
            input_price = float(prices[0])
            output_price = float(prices[1])

            model_entry = {
                "input": input_price,
                "output": output_price,
            }

            # Check for cache pricing (4 prices total)
            if len(prices) >= 4:
                model_entry["cache_write"] = float(prices[2])
                model_entry["cache_read"] = float(prices[3])

            pricing[current_model] = model_entry
            current_model = None  # Reset

    return pricing


def parse_google_markdown(markdown: str) -> dict[str, dict[str, float]]:
    """Parse Google Gemini pricing from markdown format.

    Expected format (from ai.google.dev/pricing):
        | Model | Input price | Output price |
    """
    pricing = {}

    # Pattern for Gemini models
    pattern = r"gemini[- ][\w.-]+"

    lines = markdown.split("\n")
    for i, line in enumerate(lines):
        model_match = re.search(pattern, line, re.IGNORECASE)
        if model_match:
            model = model_match.group(0).lower().replace(" ", "-")

            # Look for prices in this line or next few lines
            search_text = "\n".join(lines[i : i + 3])
            prices = re.findall(
                r"\$?([\d.]+)\s*(?:/|per)\s*(?:MTok|million|1M)",
                search_text,
                re.IGNORECASE,
            )

            if len(prices) >= 2:
                pricing[model] = {
                    "input": float(prices[0]),
                    "output": float(prices[1]),
                }

                # Check for cache pricing
                if len(prices) >= 3:
                    pricing[model]["cache_read"] = float(prices[2])

    return pricing


def format_as_python_dict(pricing: dict[str, dict[str, float]], provider: str) -> str:
    """Format pricing data as Python dictionary for pricing.py."""
    lines = [
        f"# {provider.title()} pricing (updated {__import__('datetime').date.today()})"
    ]
    lines.append(f"{provider.upper()}_PRICING = {{")

    for model, prices in sorted(pricing.items()):
        lines.append(f'    "{model}": {{')
        for key, value in prices.items():
            lines.append(f'        "{key}": {value:.2f},  # ${value:.2f} per MTok')
        lines.append("    },")

    lines.append("}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Update model pricing data")
    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic", "google"],
        help="Provider to update pricing for",
    )
    parser.add_argument(
        "--from-markdown",
        type=Path,
        help='Path to markdown file (from "Copy page" feature)',
    )
    parser.add_argument(
        "--format", choices=["json", "python"], default="json", help="Output format"
    )

    args = parser.parse_args()

    if args.from_markdown:
        # Read markdown from file
        markdown = args.from_markdown.read_text()

        # Try to detect provider
        if "openai" in markdown.lower() or "gpt" in markdown.lower():
            pricing = parse_openai_markdown(markdown)
            provider = "openai"
        elif "anthropic" in markdown.lower() or "claude" in markdown.lower():
            pricing = parse_anthropic_markdown(markdown)
            provider = "anthropic"
        elif "google" in markdown.lower() or "gemini" in markdown.lower():
            pricing = parse_google_markdown(markdown)
            provider = "google"
        else:
            print("Error: Could not detect provider from markdown", file=sys.stderr)
            sys.exit(1)

    elif args.provider:
        # Interactive: paste markdown
        print(f"Paste {args.provider.title()} pricing markdown (Ctrl+D when done):")
        markdown = sys.stdin.read()

        if args.provider == "openai":
            pricing = parse_openai_markdown(markdown)
        elif args.provider == "anthropic":
            pricing = parse_anthropic_markdown(markdown)
        else:  # google
            pricing = parse_google_markdown(markdown)

        provider = args.provider

    else:
        parser.print_help()
        sys.exit(1)

    # Output
    if args.format == "json":
        print(json.dumps(pricing, indent=2))
    else:  # python
        print(format_as_python_dict(pricing, provider))

    # Print summary
    print(f"\n# Found {len(pricing)} {provider} models", file=sys.stderr)
    for model in sorted(pricing.keys()):
        print(f"#   - {model}", file=sys.stderr)


if __name__ == "__main__":
    main()
