"""Conversation export formatters.

This module provides formatters for exporting conversations to various formats
including JSON, Markdown, HTML, and CSV.
"""

from __future__ import annotations

from consoul.formatters.base import ExportFormatter
from consoul.formatters.csv_formatter import CSVFormatter
from consoul.formatters.html import HTMLFormatter
from consoul.formatters.json_formatter import JSONFormatter
from consoul.formatters.markdown import MarkdownFormatter

__all__ = [
    "CSVFormatter",
    "ExportFormatter",
    "HTMLFormatter",
    "JSONFormatter",
    "MarkdownFormatter",
    "get_formatter",
]


def get_formatter(format_name: str) -> ExportFormatter:
    """Get formatter instance for the specified format.

    Args:
        format_name: Format name (json, markdown, html, csv)

    Returns:
        Formatter instance

    Raises:
        ValueError: If format is not supported
    """
    formatters = {
        "json": JSONFormatter(),
        "markdown": MarkdownFormatter(),
        "html": HTMLFormatter(),
        "csv": CSVFormatter(),
    }

    formatter = formatters.get(format_name.lower())
    if not formatter:
        raise ValueError(
            f"Unsupported format: {format_name}. "
            f"Supported formats: {', '.join(formatters.keys())}"
        )

    return formatter
