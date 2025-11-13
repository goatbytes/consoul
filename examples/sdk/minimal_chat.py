#!/usr/bin/env python3
"""Minimal Consoul SDK Example - Just 20 lines!

The absolute simplest way to add AI chat to your Python app.

Usage:
    python examples/sdk/minimal_chat.py

Requirements:
    pip install consoul
    export ANTHROPIC_API_KEY=your-key-here
"""

from consoul import Consoul

# That's it! One line to create a chat session
console = Consoul()

# Start chatting
console.chat("What is 2+2?")
console.chat("What files are in the current directory?")
