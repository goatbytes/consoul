"""Consoul - AI-powered terminal assistant with rich TUI.

Brings the power of modern AI assistants directly to your terminal with a rich,
interactive TUI. Built on Textual's reactive framework and LangChain's provider
abstraction.

Quick Start:
    >>> from consoul import Consoul
    >>> console = Consoul()
    >>> console.chat("Hello!")
    'Hi! How can I help you?'
"""

# ruff: noqa: E402
# Apply macOS PyTorch fixes BEFORE any other imports
# This prevents segfaults when using HuggingFace models locally
import platform as _platform

if _platform.system() == "Darwin":
    from consoul.ai.macos_fixes import apply_macos_pytorch_fixes as _apply_fixes

    _apply_fixes()
    del _apply_fixes
del _platform

__version__ = "0.2.1"
__author__ = "GoatBytes.IO"
__license__ = "Apache-2.0"

# High-level SDK
from consoul.sdk import Consoul, ConsoulResponse

__all__ = [
    "Consoul",
    "ConsoulResponse",
    "__author__",
    "__license__",
    "__version__",
]
