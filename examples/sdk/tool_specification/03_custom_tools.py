#!/usr/bin/env python3
"""Custom Tool Examples.

This example demonstrates how to create and use custom tools with Consoul SDK.
Shows two approaches:
1. Using @tool decorator (simple functions)
2. Using BaseTool class (advanced control)

Run this example:
    python 03_custom_tools.py
"""

from langchain_core.tools import BaseTool, tool

from consoul import Consoul

# ============================================================================
# Example 1: Simple @tool decorator
# ============================================================================


@tool
def calculate_sum(numbers: str) -> str:
    """Calculate the sum of comma-separated numbers.

    Args:
        numbers: Comma-separated numbers (e.g., "1,2,3,4,5")

    Returns:
        The sum as a string
    """
    nums = [float(n.strip()) for n in numbers.split(",")]
    total = sum(nums)
    return f"Sum of {numbers} = {total}"


@tool
def reverse_text(text: str) -> str:
    """Reverse the input text.

    Args:
        text: Text to reverse

    Returns:
        Reversed text
    """
    return text[::-1]


@tool
def count_words(text: str) -> str:
    """Count words in the input text.

    Args:
        text: Text to analyze

    Returns:
        Word count and character count
    """
    words = text.split()
    chars = len(text)
    return f"Words: {len(words)}, Characters: {chars}"


# ============================================================================
# Example 2: BaseTool class (advanced)
# ============================================================================


class TemperatureConverter(BaseTool):
    """Convert temperatures between Celsius and Fahrenheit."""

    name: str = "temperature_converter"
    description: str = """Convert temperatures between Celsius and Fahrenheit.
    Input format: "32F" or "0C" (number followed by F or C)"""

    def _run(self, temperature: str) -> str:
        """Convert temperature."""
        temp = temperature.strip().upper()

        if temp.endswith("F"):
            # Fahrenheit to Celsius
            fahrenheit = float(temp[:-1])
            celsius = (fahrenheit - 32) * 5 / 9
            return f"{fahrenheit}°F = {celsius:.2f}°C"
        elif temp.endswith("C"):
            # Celsius to Fahrenheit
            celsius = float(temp[:-1])
            fahrenheit = celsius * 9 / 5 + 32
            return f"{celsius}°C = {fahrenheit:.2f}°F"
        else:
            return "Invalid format. Use '32F' or '0C'"


class JsonFormatter(BaseTool):
    """Format and validate JSON strings."""

    name: str = "json_formatter"
    description: str = "Format and validate JSON strings, making them readable"

    def _run(self, json_string: str) -> str:
        """Format JSON string."""
        import json

        try:
            # Parse and re-format with indentation
            data = json.loads(json_string)
            formatted = json.dumps(data, indent=2, sort_keys=True)
            return f"Valid JSON:\n{formatted}"
        except json.JSONDecodeError as e:
            return f"Invalid JSON: {e}"


# ============================================================================
# Example usage
# ============================================================================


def example_decorator_tools():
    """Use simple @tool decorated functions."""
    print("\n" + "=" * 60)
    print("Example 1: @tool Decorator (Simple Functions)")
    print("=" * 60)

    # Mix custom tools with built-in tools
    console = Consoul(
        model="llama",
        tools=[calculate_sum, reverse_text, count_words, "bash"],
        persist=False,
    )

    print(f"Tools enabled: {console.tools_enabled}")

    if console.registry:
        tools = console.registry.list_tools()
        print(f"\nRegistered tools ({len(tools)}):")
        for tool_meta in tools:
            print(f"  - {tool_meta.name}")

    print("\nDemo - Testing tools directly:")
    print(f"  calculate_sum('10,20,30') = {calculate_sum.invoke('10,20,30')}")
    print(f"  reverse_text('Hello') = {reverse_text.invoke('Hello')}")
    print(
        f"  count_words('The quick brown fox') = {count_words.invoke('The quick brown fox')}"
    )


def example_basetools():
    """Use BaseTool classes for advanced control."""
    print("\n" + "=" * 60)
    print("Example 2: BaseTool Classes (Advanced Control)")
    print("=" * 60)

    # Instantiate custom tools
    temp_converter = TemperatureConverter()
    json_formatter = JsonFormatter()

    console = Consoul(
        model="llama", tools=[temp_converter, json_formatter, "grep"], persist=False
    )

    print(f"Tools enabled: {console.tools_enabled}")

    if console.registry:
        tools = console.registry.list_tools()
        print(f"\nRegistered tools ({len(tools)}):")
        for tool_meta in tools:
            print(f"  - {tool_meta.name}")

    print("\nDemo - Testing tools directly:")
    print(f"  temperature_converter('32F') = {temp_converter._run('32F')}")
    print(f"  temperature_converter('100C') = {temp_converter._run('100C')}")
    test_json = '{"name":"test"}'
    print(f"  json_formatter('{test_json}') = {json_formatter._run(test_json)}")


def example_only_custom_tools():
    """Use only custom tools (no built-in tools)."""
    print("\n" + "=" * 60)
    print("Example 3: Only Custom Tools")
    print("=" * 60)

    console = Consoul(
        model="llama",
        tools=[calculate_sum, reverse_text, TemperatureConverter()],
        persist=False,
    )

    print(f"Tools enabled: {console.tools_enabled}")

    if console.registry:
        tools = console.registry.list_tools()
        print(f"\nCustom-only tools ({len(tools)}):")
        for tool_meta in tools:
            print(f"  - {tool_meta.name}")
        print("\nNo built-in tools enabled - pure custom toolset")


def example_custom_with_categories():
    """Mix custom tools with category-based built-in tools."""
    print("\n" + "=" * 60)
    print("Example 4: Custom Tools + Categories")
    print("=" * 60)

    console = Consoul(
        model="llama",
        tools=[
            "search",  # Category: all search tools
            calculate_sum,  # Custom tool
            TemperatureConverter(),  # Custom tool
        ],
        persist=False,
    )

    print(f"Tools enabled: {console.tools_enabled}")

    if console.registry:
        tools = console.registry.list_tools()
        print(f"\nMixed tools ({len(tools)}):")

        # Separate custom from built-in
        custom = [
            t for t in tools if t.name in ["calculate_sum", "temperature_converter"]
        ]
        builtin = [t for t in tools if t not in custom]

        print(f"\n  Built-in (search category): {len(builtin)}")
        for tool_meta in builtin:
            print(f"    - {tool_meta.name}")

        print(f"\n  Custom tools: {len(custom)}")
        for tool_meta in custom:
            print(f"    - {tool_meta.name}")


def main():
    """Run all custom tool examples."""
    print("\n" + "=" * 60)
    print("CUSTOM TOOL EXAMPLES")
    print("=" * 60)
    print("\nThis example shows how to create and use custom tools with Consoul SDK.")

    try:
        # Run each example
        example_decorator_tools()
        example_basetools()
        example_only_custom_tools()
        example_custom_with_categories()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)
        print("\nKey Takeaways:")
        print("  - @tool decorator: Simple functions become tools")
        print("  - BaseTool class: Advanced control with custom logic")
        print("  - Mix custom tools with built-in tools or categories")
        print("  - Custom tools integrate seamlessly with tool specification")
        print("\nBest Practices:")
        print("  - Use @tool for simple, stateless operations")
        print("  - Use BaseTool for complex logic or stateful tools")
        print("  - Provide clear docstrings - AI uses them for tool selection")
        print("  - Type hints help with parameter validation")
        print("\nSee docs/sdk-tools.md for complete documentation.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
