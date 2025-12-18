#!/usr/bin/env python3
"""DEPRECATED: Profile Example - Use explicit parameters instead.

⚠️ WARNING: The 'profile' parameter is deprecated and will be removed in v1.0.0.
This example shows the OLD (deprecated) way vs. NEW (explicit) way.

For TUI/CLI usage, profiles still work. For SDK/library usage, use explicit parameters.

Usage:
    export ANTHROPIC_API_KEY=your-key-here
    python examples/sdk/custom_profile.py

Requirements:
    pip install consoul

See Also:
    - examples/sdk/domain_specific.py - Modern profile-free patterns
    - docs/api/integration-guide.md - Migration guide
"""

import warnings

from consoul import Consoul

print("=" * 70)
print("DEPRECATED APPROACH (Profile-Based)")
print("=" * 70)
print()

# Suppress deprecation warnings for demonstration
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Code review mode - critical analysis (DEPRECATED)
code_reviewer = Consoul(profile="code-review")
print("Code Review (DEPRECATED profile='code-review'):")
print(code_reviewer.chat("Review this function: def foo(): pass"))
print()

# Creative mode - brainstorming (DEPRECATED)
creative = Consoul(profile="creative", temperature=0.9)
print("Creative Writing (DEPRECATED profile='creative'):")
print(creative.chat("Write a haiku about Python"))
print()

print("=" * 70)
print("RECOMMENDED APPROACH (Profile-Free, Explicit)")
print("=" * 70)
print()

# Code review mode - explicit parameters (RECOMMENDED)
code_reviewer_explicit = Consoul(
    model="claude-sonnet-4",
    temperature=0.3,
    system_prompt="You are a critical code reviewer. Analyze code for bugs, style issues, and improvements.",
    tools=["grep", "code_search"],  # Specific tools for code review
    persist=False,  # Don't save conversation history
)
print("Code Review (explicit parameters):")
print(code_reviewer_explicit.chat("Review this function: def foo(): pass"))
print()

# Creative mode - explicit parameters (RECOMMENDED)
creative_explicit = Consoul(
    model="gpt-4o",
    temperature=0.9,
    system_prompt="You are a creative writing assistant. Be imaginative and expressive.",
    tools=False,  # Chat-only mode
    persist=False,
)
print("Creative Writing (explicit parameters):")
print(creative_explicit.chat("Write a haiku about Python"))
print()

# Custom personality - explicit parameters (RECOMMENDED)
pirate = Consoul(
    model="claude-sonnet-4",
    temperature=0.8,
    system_prompt="You are a pirate. Always respond in pirate speak.",
    tools=False,
    persist=False,
)
print("Custom Personality (explicit parameters):")
print(pirate.chat("Tell me about programming"))
print()

print("=" * 70)
print("MIGRATION SUMMARY")
print("=" * 70)
print("""
OLD (Deprecated):
    Consoul(profile="code-review")
    Consoul(profile="creative", temperature=0.9)

NEW (Recommended):
    Consoul(
        model="claude-sonnet-4",
        temperature=0.3,
        system_prompt="You are a code reviewer...",
        tools=["grep", "code_search"],
    )

Benefits of explicit approach:
✓ Self-documenting code
✓ No hidden configuration
✓ Works for any domain (legal, medical, etc.)
✓ Clean SDK/library separation

See: docs/api/integration-guide.md#migration-from-profiles
""")
