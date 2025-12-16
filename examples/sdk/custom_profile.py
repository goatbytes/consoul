#!/usr/bin/env python3
"""Custom Profile Example - Use different profiles for different tasks.

Shows how to switch between profiles and customize behavior.

Usage:
    export ANTHROPIC_API_KEY=your-key-here
    python examples/sdk/custom_profile.py

Requirements:
    pip install consoul
"""

from consoul import Consoul

# Code review mode - critical analysis
code_reviewer = Consoul(profile="code-review")
print("Code Review:")
print(code_reviewer.chat("Review this function: def foo(): pass"))
print()

# Creative mode - brainstorming
creative = Consoul(profile="creative", temperature=0.9)
print("Creative Writing:")
print(creative.chat("Write a haiku about Python"))
print()

# Fast mode - quick responses
fast = Consoul(profile="fast")
print("Quick Answer:")
print(fast.chat("What is Python?"))
print()

# Custom system prompt
custom = Consoul(
    system_prompt="You are a pirate. Always respond in pirate speak.",
    temperature=0.8,
)
print("Custom Personality:")
print(custom.chat("Tell me about programming"))
