#!/usr/bin/env python3
"""Tool Discovery Examples.

This example demonstrates automatic tool discovery from the .consoul/tools/ directory.
The SDK can auto-load custom tools from Python files without explicit registration.

Setup:
    1. Create .consoul/tools/ directory in your project
    2. Add Python files with tool definitions
    3. Enable discovery with discover_tools=True

Run this example:
    python 04_tool_discovery.py
"""

import shutil
import tempfile
from pathlib import Path

from consoul import Consoul


def setup_example_tools_directory() -> Path:
    """Create a temporary tools directory with example tools.

    This simulates a real .consoul/tools/ directory structure.

    Returns:
        Path to the temporary tools directory
    """
    # Create temp directory
    temp_dir = Path(tempfile.mkdtemp())
    tools_dir = temp_dir / ".consoul" / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)

    # Create example tool file 1: Simple @tool decorator
    simple_tools = '''"""Simple utility tools."""

from langchain_core.tools import tool


@tool
def extract_emails(text: str) -> str:
    """Extract email addresses from text.

    Args:
        text: Text containing email addresses

    Returns:
        Comma-separated list of email addresses
    """
    import re

    pattern = r'\\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b'
    emails = re.findall(pattern, text)
    return ", ".join(emails) if emails else "No emails found"


@tool
def slugify(text: str) -> str:
    """Convert text to URL-friendly slug.

    Args:
        text: Text to slugify

    Returns:
        URL-friendly slug
    """
    import re

    # Convert to lowercase and replace spaces with hyphens
    slug = text.lower().strip()
    slug = re.sub(r'[^\\w\\s-]', '', slug)
    slug = re.sub(r'[-\\s]+', '-', slug)
    return slug
'''

    # Create example tool file 2: BaseTool class
    advanced_tools = '''"""Advanced utility tools using BaseTool."""

from langchain_core.tools import BaseTool


class MarkdownTableGenerator(BaseTool):
    """Generate markdown tables from CSV data."""

    name: str = "markdown_table"
    description: str = "Convert CSV data to markdown table format"

    def _run(self, csv_data: str) -> str:
        """Convert CSV to markdown table."""
        lines = csv_data.strip().split("\\n")
        if not lines:
            return "Empty input"

        # Header
        headers = lines[0].split(",")
        table = "| " + " | ".join(headers) + " |\\n"
        table += "| " + " | ".join(["---"] * len(headers)) + " |\\n"

        # Rows
        for line in lines[1:]:
            cells = line.split(",")
            table += "| " + " | ".join(cells) + " |\\n"

        return table


# IMPORTANT: BaseTool subclasses must be instantiated to be discovered
markdown_table = MarkdownTableGenerator()
'''

    # Write tool files
    (tools_dir / "simple_tools.py").write_text(simple_tools)
    (tools_dir / "advanced_tools.py").write_text(advanced_tools)

    # Create subdirectory with more tools (tests recursive discovery)
    sub_dir = tools_dir / "text_processing"
    sub_dir.mkdir(exist_ok=True)

    sub_tools = '''"""Text processing tools in subdirectory."""

from langchain_core.tools import tool


@tool
def word_frequency(text: str) -> str:
    """Count word frequencies in text.

    Args:
        text: Text to analyze

    Returns:
        Top 5 most common words with counts
    """
    from collections import Counter

    words = text.lower().split()
    counter = Counter(words)
    top_5 = counter.most_common(5)

    result = "Top 5 words:\\n"
    for word, count in top_5:
        result += f"  {word}: {count}\\n"
    return result
'''

    (sub_dir / "frequency.py").write_text(sub_tools)

    return temp_dir


def cleanup_example_directory(temp_dir: Path) -> None:
    """Remove temporary tools directory."""
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


def example_basic_discovery():
    """Basic tool discovery with default settings."""
    print("\n" + "=" * 60)
    print("Example 1: Basic Discovery (Recursive)")
    print("=" * 60)

    # Setup example tools
    temp_dir = setup_example_tools_directory()
    tools_dir = temp_dir / ".consoul" / "tools"

    try:
        # Change to temp directory so discovery finds .consoul/tools/
        import os

        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        # Enable discovery (recursive by default)
        console = Consoul(
            model="llama",
            tools=True,  # Include built-in tools
            discover_tools=True,  # Auto-discover from .consoul/tools/
            persist=False,
        )

        os.chdir(original_cwd)

        print(f"Tools enabled: {console.tools_enabled}")
        print("Discovery enabled: True")
        print(f"Discovery path: {tools_dir}")

        if console.registry:
            all_tools = console.registry.list_tools()

            # Separate discovered from built-in
            discovered_names = {
                "extract_emails",
                "slugify",
                "markdown_table",
                "word_frequency",
            }
            discovered = [t for t in all_tools if t.name in discovered_names]
            builtin = [t for t in all_tools if t not in discovered]

            print(f"\nTotal tools: {len(all_tools)}")
            print(f"  Built-in: {len(builtin)}")
            print(f"  Discovered: {len(discovered)}")

            print("\nDiscovered tools from .consoul/tools/:")
            for tool_meta in discovered:
                print(f"  - {tool_meta.name} ({tool_meta.risk_level.value})")

            print("\n✓ Discovered tools from both root and subdirectories")

    finally:
        cleanup_example_directory(temp_dir)


def example_discovery_with_specific_tools():
    """Combine discovery with specific tool selection."""
    print("\n" + "=" * 60)
    print("Example 2: Discovery + Specific Tools")
    print("=" * 60)

    temp_dir = setup_example_tools_directory()

    try:
        import os

        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        # Discover custom tools + only specific built-in tools
        console = Consoul(
            model="llama",
            tools=["bash", "grep"],  # Only these built-in tools
            discover_tools=True,  # Plus discovered tools
            persist=False,
        )

        os.chdir(original_cwd)

        if console.registry:
            all_tools = console.registry.list_tools()

            discovered_names = {
                "extract_emails",
                "slugify",
                "markdown_table",
                "word_frequency",
            }
            discovered = [t for t in all_tools if t.name in discovered_names]
            builtin = [t for t in all_tools if t not in discovered]

            print(f"\nBuilt-in tools ({len(builtin)}):")
            for tool_meta in builtin:
                print(f"  - {tool_meta.name}")

            print(f"\nDiscovered tools ({len(discovered)}):")
            for tool_meta in discovered:
                print(f"  - {tool_meta.name}")

            print("\nUse case: Controlled built-in tools + all custom tools")

    finally:
        cleanup_example_directory(temp_dir)


def example_discovery_with_categories():
    """Combine discovery with category filtering."""
    print("\n" + "=" * 60)
    print("Example 3: Discovery + Categories")
    print("=" * 60)

    temp_dir = setup_example_tools_directory()

    try:
        import os

        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        # Discover custom tools + category-filtered built-in tools
        console = Consoul(
            model="llama",
            tools="search",  # Only search category
            discover_tools=True,  # Plus discovered tools
            persist=False,
        )

        os.chdir(original_cwd)

        if console.registry:
            all_tools = console.registry.list_tools()

            discovered_names = {
                "extract_emails",
                "slugify",
                "markdown_table",
                "word_frequency",
            }
            discovered = [t for t in all_tools if t.name in discovered_names]
            search_tools = [t for t in all_tools if t not in discovered]

            print(f"\nSearch category tools ({len(search_tools)}):")
            for tool_meta in search_tools:
                print(f"  - {tool_meta.name}")

            print(f"\nDiscovered tools ({len(discovered)}):")
            for tool_meta in discovered:
                print(f"  - {tool_meta.name}")

            print("\nUse case: Specific built-in capabilities + custom extensions")

    finally:
        cleanup_example_directory(temp_dir)


def example_discovery_only():
    """Only use discovered tools (no built-in tools)."""
    print("\n" + "=" * 60)
    print("Example 4: Discovery Only (No Built-in)")
    print("=" * 60)

    temp_dir = setup_example_tools_directory()

    try:
        import os

        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        # Only discovered tools, no built-in tools
        console = Consoul(
            model="llama",
            tools=[],  # No built-in tools
            discover_tools=True,  # Only discovered tools
            persist=False,
        )

        os.chdir(original_cwd)

        if console.registry:
            tools = console.registry.list_tools()
            print(f"\nOnly discovered tools ({len(tools)}):")
            for tool_meta in tools:
                print(f"  - {tool_meta.name} ({tool_meta.risk_level.value})")

            print("\nUse case: Pure custom toolset with no built-in tools")
            print("Note: All discovered tools default to CAUTION risk level")

    finally:
        cleanup_example_directory(temp_dir)


def example_no_discovery():
    """Disable discovery explicitly."""
    print("\n" + "=" * 60)
    print("Example 5: Discovery Disabled")
    print("=" * 60)

    temp_dir = setup_example_tools_directory()

    try:
        import os

        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        # Explicitly disable discovery
        console = Consoul(
            model="llama",
            tools=True,  # All built-in tools
            discover_tools=False,  # No discovery
            persist=False,
        )

        os.chdir(original_cwd)

        if console.registry:
            tools = console.registry.list_tools()
            print(f"\nOnly built-in tools ({len(tools)}):")
            print("No custom tools discovered")
            print("\nUse case: Reproducible environment, no auto-discovery")

    finally:
        cleanup_example_directory(temp_dir)


def main():
    """Run all discovery examples."""
    print("\n" + "=" * 60)
    print("TOOL DISCOVERY EXAMPLES")
    print("=" * 60)
    print("\nThis example demonstrates automatic tool discovery from .consoul/tools/")

    try:
        # Run each example
        example_basic_discovery()
        example_discovery_with_specific_tools()
        example_discovery_with_categories()
        example_discovery_only()
        example_no_discovery()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)
        print("\nKey Takeaways:")
        print("  - discover_tools=True enables auto-discovery from .consoul/tools/")
        print("  - Discovery is recursive by default (includes subdirectories)")
        print("  - Discovered tools work with all tool specifications")
        print("  - Can combine discovery with built-in tools, categories, or lists")
        print("  - Discovered tools default to CAUTION risk level")
        print("\nImportant:")
        print("  - @tool decorated functions are auto-discovered")
        print("  - BaseTool subclasses MUST be instantiated to be discovered")
        print("  - Files starting with _ are skipped (e.g., __init__.py)")
        print("\nDirectory structure:")
        print("  .consoul/tools/")
        print("    ├── my_tools.py        # Discovered")
        print("    ├── utils/             # Subdirectory (recursive)")
        print("    │   └── helpers.py     # Discovered")
        print("    └── _private.py        # Skipped (starts with _)")
        print("\nSee docs/sdk-tools.md for complete documentation.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
