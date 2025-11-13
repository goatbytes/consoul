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

__version__ = "0.1.0"
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
