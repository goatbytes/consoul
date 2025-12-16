#!/usr/bin/env python3
"""
Generate CLI documentation from consoul describe output.

This script extracts CLI schema data from consoul describe and writes it to
Markdown files using Jinja2 templates.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path for development
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# ruff: noqa: E402
from consoul.utils.docs_generator import generate_cli_docs


def main() -> None:
    """
    Main function to orchestrate documentation generation.

    Usage:
        python scripts/generate_docs.py
        python scripts/generate_docs.py --output docs/cli-reference.md
        python scripts/generate_docs.py tui --output docs/cli-reference-tui.md
    """
    import argparse

    parser = argparse.ArgumentParser(description="Generate Consoul CLI documentation")
    parser.add_argument(
        "command",
        nargs="*",
        help="Specific command to document (e.g., 'tui')",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("docs/cli-reference.md"),
        help="Output file path (default: docs/cli-reference.md)",
    )
    parser.add_argument(
        "--template",
        "-t",
        default="cli_reference.md.j2",
        help="Template to use (default: cli_reference.md.j2)",
    )

    args = parser.parse_args()

    try:
        print("Generating CLI documentation...")
        if args.command:
            print(f"  Command: {' '.join(args.command)}")
        print(f"  Output: {args.output}")
        print(f"  Template: {args.template}")

        # Generate documentation
        generate_cli_docs(
            output_path=args.output,
            command=args.command if args.command else None,
            template_name=args.template,
        )

        print(f"✓ Documentation generated successfully: {args.output}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
