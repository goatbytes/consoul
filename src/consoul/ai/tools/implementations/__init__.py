"""Concrete tool implementations for Consoul AI.

This package contains actual tool implementations that can be registered
with the ToolRegistry and called by AI models.
"""

from __future__ import annotations

from consoul.ai.tools.implementations.analyze_images import (
    analyze_images,
    get_analyze_images_config,
    set_analyze_images_config,
)
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
from consoul.ai.tools.implementations.file_edit import (
    append_to_file,
    create_file,
    delete_file,
    edit_file_lines,
    edit_file_search_replace,
    get_file_edit_config,
    set_file_edit_config,
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
from consoul.ai.tools.implementations.read_url import (
    get_read_url_config,
    read_url,
    set_read_url_config,
)
from consoul.ai.tools.implementations.web_search import (
    get_web_search_config,
    set_web_search_config,
    web_search,
)
from consoul.ai.tools.implementations.wikipedia import (
    get_wikipedia_config,
    set_wikipedia_config,
    wikipedia_search,
)

__all__ = [
    "analyze_images",
    "append_to_file",
    "bash_execute",
    "code_search",
    "create_file",
    "delete_file",
    "edit_file_lines",
    "edit_file_search_replace",
    "find_references",
    "get_analyze_images_config",
    "get_bash_config",
    "get_code_search_config",
    "get_file_edit_config",
    "get_find_references_config",
    "get_grep_search_config",
    "get_read_config",
    "get_read_url_config",
    "get_web_search_config",
    "get_wikipedia_config",
    "grep_search",
    "read_file",
    "read_url",
    "set_analyze_images_config",
    "set_bash_config",
    "set_code_search_config",
    "set_file_edit_config",
    "set_find_references_config",
    "set_grep_search_config",
    "set_read_config",
    "set_read_url_config",
    "set_web_search_config",
    "set_wikipedia_config",
    "web_search",
    "wikipedia_search",
]
