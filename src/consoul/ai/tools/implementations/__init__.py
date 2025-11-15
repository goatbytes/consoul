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
from consoul.ai.tools.implementations.code_search import (
    code_search,
    get_code_search_config,
    set_code_search_config,
)
from consoul.ai.tools.implementations.find_references import (
    find_references,
    get_find_references_config,
    set_find_references_config,
)
from consoul.ai.tools.implementations.grep_search import (
    get_grep_search_config,
    grep_search,
    set_grep_search_config,
)
from consoul.ai.tools.implementations.read import (
    get_read_config,
    read_file,
    set_read_config,
)
from consoul.ai.tools.implementations.web_search import (
    get_web_search_config,
    set_web_search_config,
    web_search,
)

__all__ = [
    "bash_execute",
    "code_search",
    "find_references",
    "get_bash_config",
    "get_code_search_config",
    "get_find_references_config",
    "get_grep_search_config",
    "get_read_config",
    "get_web_search_config",
    "grep_search",
    "read_file",
    "set_bash_config",
    "set_code_search_config",
    "set_find_references_config",
    "set_grep_search_config",
    "set_read_config",
    "set_web_search_config",
    "web_search",
]
