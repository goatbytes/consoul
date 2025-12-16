#!/usr/bin/env python3
"""Minimal Consoul SDK Example - Just 5 lines!

The absolute simplest way to add AI chat to your Python app.

Usage:
    export ANTHROPIC_API_KEY=your-key-here  # Or OPENAI_API_KEY, etc.
    python examples/sdk/minimal_chat.py

Requirements:
    pip install consoul
"""

from consoul import Consoul

console = Consoul()
print(console.settings)
print(console.chat("What is 2+2?"))
print(console.chat("What files are in the current directory?"))
