#!/usr/bin/env python3
"""Basic Tool Specification Patterns.

This example demonstrates the fundamental ways to specify tools in Consoul SDK:
- Boolean values (True/False)
- Risk level filtering
- Specific tool lists

Run this example:
    python 01_basic_patterns.py
"""

from consoul import Consoul


def example_all_tools():
    """Enable all built-in tools (default behavior)."""
    print("\n" + "=" * 60)
    print("Example 1: All Tools Enabled")
    print("=" * 60)

    console = Consoul(model="llama", tools=True, persist=False)

    print(f"Tools enabled: {console.tools_enabled}")
    print(
        f"Number of tools: {len(console.registry.list_tools()) if console.registry else 0}"
    )

    # Show which tools are available
    if console.registry:
        tools = console.registry.list_tools()
        print(f"\nAvailable tools ({len(tools)}):")
        for tool_meta in tools:
            print(f"  - {tool_meta.name} ({tool_meta.risk_level.value})")


def example_no_tools():
    """Disable all tools."""
    print("\n" + "=" * 60)
    print("Example 2: No Tools (Disabled)")
    print("=" * 60)

    console = Consoul(model="llama", tools=False, persist=False)

    print(f"Tools enabled: {console.tools_enabled}")
    print("Chat-only mode - AI cannot execute any tools")


def example_safe_tools():
    """Only enable SAFE risk level tools (read-only operations)."""
    print("\n" + "=" * 60)
    print("Example 3: Safe Tools Only (Risk Level Filtering)")
    print("=" * 60)

    console = Consoul(model="llama", tools="safe", persist=False)

    print(f"Tools enabled: {console.tools_enabled}")

    if console.registry:
        tools = console.registry.list_tools()
        print(f"\nSafe tools ({len(tools)}):")
        for tool_meta in tools:
            print(f"  - {tool_meta.name} ({tool_meta.risk_level.value})")
        print(
            "\nThese tools are read-only and cannot modify files or execute commands."
        )


def example_caution_tools():
    """Enable SAFE + CAUTION risk level tools."""
    print("\n" + "=" * 60)
    print("Example 4: Caution Tools (SAFE + CAUTION)")
    print("=" * 60)

    console = Consoul(model="llama", tools="caution", persist=False)

    print(f"Tools enabled: {console.tools_enabled}")

    if console.registry:
        tools = console.registry.list_tools()
        print(f"\nSafe + Caution tools ({len(tools)}):")
        for tool_meta in tools:
            print(f"  - {tool_meta.name} ({tool_meta.risk_level.value})")
        print("\nIncludes file operations and command execution.")


def example_specific_tools():
    """Specify exact tools by name."""
    print("\n" + "=" * 60)
    print("Example 5: Specific Tools by Name")
    print("=" * 60)

    # Only bash and grep
    console = Consoul(model="llama", tools=["bash", "grep"], persist=False)

    print(f"Tools enabled: {console.tools_enabled}")

    if console.registry:
        tools = console.registry.list_tools()
        print(f"\nSpecific tools ({len(tools)}):")
        for tool_meta in tools:
            print(f"  - {tool_meta.name}")
        print("\nOnly the exact tools specified are available.")


def main():
    """Run all basic pattern examples."""
    print("\n" + "=" * 60)
    print("BASIC TOOL SPECIFICATION PATTERNS")
    print("=" * 60)
    print("\nThis example shows different ways to configure tools in Consoul SDK.")

    try:
        # Run each example
        example_all_tools()
        example_no_tools()
        example_safe_tools()
        example_caution_tools()
        example_specific_tools()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)
        print("\nKey Takeaways:")
        print("  - tools=True enables all built-in tools")
        print("  - tools=False disables all tools (chat-only mode)")
        print("  - tools='safe' filters by risk level (safe, caution, dangerous)")
        print("  - tools=['bash', 'grep'] specifies exact tools")
        print("\nSee docs/sdk-tools.md for complete documentation.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
