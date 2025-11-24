#!/usr/bin/env python3
"""Tool Category Filtering Examples.

This example demonstrates how to use tool categories to enable groups of
related tools without listing each tool individually.

Categories available:
- search: grep, code_search, find_references
- file-edit: create_file, edit_file_lines, edit_file_search_replace, append_to_file, delete_file
- web: read_url, web_search
- execute: bash

Run this example:
    python 02_categories.py
"""

from consoul import Consoul


def example_single_category():
    """Enable all tools in the 'search' category."""
    print("\n" + "=" * 60)
    print("Example 1: Single Category - Search Tools")
    print("=" * 60)

    console = Consoul(model="llama", tools="search", persist=False)

    print(f"Tools enabled: {console.tools_enabled}")

    if console.registry:
        tools = console.registry.list_tools()
        print(f"\nSearch category tools ({len(tools)}):")
        for tool_meta in tools:
            print(f"  - {tool_meta.name}")
        print("\nUse case: Read-only code exploration and analysis")


def example_multiple_categories():
    """Enable multiple categories at once."""
    print("\n" + "=" * 60)
    print("Example 2: Multiple Categories - Search + Web")
    print("=" * 60)

    console = Consoul(model="llama", tools=["search", "web"], persist=False)

    print(f"Tools enabled: {console.tools_enabled}")

    if console.registry:
        tools = console.registry.list_tools()
        print(f"\nSearch + Web tools ({len(tools)}):")

        # Group by category for clarity
        search_tools = [
            t
            for t in tools
            if "search" in t.name
            or t.name == "grep"
            or "code" in t.name
            or "references" in t.name
        ]
        web_tools = [t for t in tools if "url" in t.name or "web" in t.name]

        print(f"\n  Search tools ({len(search_tools)}):")
        for tool_meta in search_tools:
            print(f"    - {tool_meta.name}")

        print(f"\n  Web tools ({len(web_tools)}):")
        for tool_meta in web_tools:
            print(f"    - {tool_meta.name}")

        print("\nUse case: Research assistant with code analysis and web access")


def example_category_plus_specific_tool():
    """Mix categories with specific tool names."""
    print("\n" + "=" * 60)
    print("Example 3: Category + Specific Tool")
    print("=" * 60)

    # Enable all search tools + bash execution
    console = Consoul(model="llama", tools=["search", "bash"], persist=False)

    print(f"Tools enabled: {console.tools_enabled}")

    if console.registry:
        tools = console.registry.list_tools()
        print(f"\nSearch + bash tools ({len(tools)}):")
        for tool_meta in tools:
            print(f"  - {tool_meta.name}")
        print("\nUse case: Code analysis with ability to run commands")


def example_file_edit_category():
    """Enable all file editing tools."""
    print("\n" + "=" * 60)
    print("Example 4: File Edit Category")
    print("=" * 60)

    console = Consoul(model="llama", tools="file-edit", persist=False)

    print(f"Tools enabled: {console.tools_enabled}")

    if console.registry:
        tools = console.registry.list_tools()
        print(f"\nFile editing tools ({len(tools)}):")
        for tool_meta in tools:
            print(f"  - {tool_meta.name} ({tool_meta.risk_level.value})")
        print("\nUse case: Code modification and refactoring")


def example_web_category():
    """Enable all web tools."""
    print("\n" + "=" * 60)
    print("Example 5: Web Category")
    print("=" * 60)

    console = Consoul(model="llama", tools="web", persist=False)

    print(f"Tools enabled: {console.tools_enabled}")

    if console.registry:
        tools = console.registry.list_tools()
        print(f"\nWeb tools ({len(tools)}):")
        for tool_meta in tools:
            print(f"  - {tool_meta.name} ({tool_meta.risk_level.value})")
        print("\nUse case: Research and information gathering from the web")


def example_execute_category():
    """Enable execution tools."""
    print("\n" + "=" * 60)
    print("Example 6: Execute Category")
    print("=" * 60)

    console = Consoul(model="llama", tools="execute", persist=False)

    print(f"Tools enabled: {console.tools_enabled}")

    if console.registry:
        tools = console.registry.list_tools()
        print(f"\nExecution tools ({len(tools)}):")
        for tool_meta in tools:
            print(f"  - {tool_meta.name} ({tool_meta.risk_level.value})")
        print("\nUse case: System automation and command execution")
        print("⚠️  Note: bash is CAUTION level - use with appropriate safeguards")


def example_complex_combination():
    """Complex combination of categories and tools."""
    print("\n" + "=" * 60)
    print("Example 7: Complex Combination")
    print("=" * 60)

    # Search + web categories, plus specific file editing tools
    console = Consoul(
        model="llama",
        tools=["search", "web", "edit_file_lines", "create_file"],
        persist=False,
    )

    print(f"Tools enabled: {console.tools_enabled}")

    if console.registry:
        tools = console.registry.list_tools()
        print(f"\nCustom tool set ({len(tools)}):")
        for tool_meta in tools:
            print(f"  - {tool_meta.name}")
        print("\nUse case: Research assistant that can create and edit files")


def main():
    """Run all category filtering examples."""
    print("\n" + "=" * 60)
    print("TOOL CATEGORY FILTERING EXAMPLES")
    print("=" * 60)
    print(
        "\nThis example shows how to use categories to enable groups of related tools."
    )

    try:
        # Run each example
        example_single_category()
        example_multiple_categories()
        example_category_plus_specific_tool()
        example_file_edit_category()
        example_web_category()
        example_execute_category()
        example_complex_combination()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)
        print("\nKey Takeaways:")
        print("  - tools='search' enables all search-related tools")
        print("  - tools=['search', 'web'] enables multiple categories")
        print("  - tools=['search', 'bash'] mixes categories with specific tools")
        print(
            "  - Categories group tools by function (search, file-edit, web, execute)"
        )
        print("\nAvailable categories:")
        print("  - search: grep, code_search, find_references")
        print("  - file-edit: create_file, edit_file_lines, edit_file_search_replace,")
        print("              append_to_file, delete_file")
        print("  - web: read_url, web_search")
        print("  - execute: bash")
        print("\nSee docs/sdk-tools.md for complete documentation.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
