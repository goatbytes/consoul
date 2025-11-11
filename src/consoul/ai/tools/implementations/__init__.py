"""Concrete tool implementations for Consoul AI.

This package contains actual tool implementations that can be registered
with the ToolRegistry and called by AI models.
"""

from __future__ import annotations

from consoul.ai.tools.implementations.bash import (
    bash_execute,
    get_bash_config,
    set_bash_config,
)

__all__ = ["bash_execute", "get_bash_config", "set_bash_config"]
