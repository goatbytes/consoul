#!/usr/bin/env python3
"""Quick Start Consoul SDK Example - Profile-free customization in ~15 lines.

Shows how to customize the SDK for common use cases using explicit parameters.

Usage:
    export ANTHROPIC_API_KEY=your-key-here
    python examples/sdk/quick_start.py

Requirements:
    pip install consoul
"""

from consoul import Consoul

# Customize with explicit parameters (RECOMMENDED)
console = Consoul(
    model="gpt-4o",  # Auto-detect provider
    temperature=0.7,
    system_prompt="You are a helpful coding assistant.",
    tools=True,  # Enable all built-in tools with approval
    persist=True,  # Save conversation history
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

# Note: The 'profile' parameter is deprecated as of v0.5.0
# OLD (deprecated): Consoul(profile="default", model="gpt-4o")
# NEW (recommended): Consoul(model="gpt-4o", system_prompt="...", temperature=0.7)
