#!/usr/bin/env python3
"""Quick Start Consoul SDK Example - Customization in ~15 lines.

Shows how to customize the SDK for common use cases.

Usage:
    export ANTHROPIC_API_KEY=your-key-here
    python examples/sdk/quick_start.py

Requirements:
    pip install consoul
"""

from consoul import Consoul

# Customize as needed
console = Consoul(
    model="gpt-4o",  # Auto-detect provider
    profile="default",  # Use built-in profile
    tools=True,  # Enable bash execution with approval
    temperature=0.7,
)

# Stateful conversation - history is maintained
console.chat("List all Python files in this directory")
console.chat("Show me the first one")

# Rich response with metadata
response = console.ask("Summarize this project", show_tokens=True)
print(f"\nResponse: {response.content}")
print(f"Tokens used: {response.tokens}")
print(f"Model: {response.model}")

# Introspection
print(f"\nSettings: {console.settings}")
print(f"Last cost: {console.last_cost}")
