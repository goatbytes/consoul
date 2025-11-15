"""AST-based code structure search using tree-sitter.

Provides semantic code search for symbols (functions, classes, methods) across
multiple programming languages using Abstract Syntax Tree parsing.

Example:
    >>> from consoul.ai.tools.implementations.code_search import code_search
    >>> result = code_search.invoke({
    ...     "query": "calculate_total",
    ...     "path": "src/",
    ...     "symbol_type": "function",
    ... })
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from grep_ast import filename_to_lang
from langchain_core.tools import tool
from tree_sitter_language_pack import get_parser

from consoul.ai.tools.cache import CodeSearchCache
from consoul.ai.tools.exceptions import ToolExecutionError
from consoul.config.models import CodeSearchToolConfig

# Module-level config that can be set by the registry
_TOOL_CONFIG: CodeSearchToolConfig | None = None

# Module-level cache instance
_CACHE: CodeSearchCache | None = None

logger = logging.getLogger(__name__)


def set_code_search_config(config: CodeSearchToolConfig) -> None:
    """Set the module-level config for code_search tool.

    This should be called by the ToolRegistry when registering code_search
    to inject the profile's configured settings.

    Args:
        config: CodeSearchToolConfig from the active profile's ToolConfig.code_search
    """
    global _TOOL_CONFIG
    _TOOL_CONFIG = config


def get_code_search_config() -> CodeSearchToolConfig:
    """Get the current code_search tool config.

    Returns:
        The configured CodeSearchToolConfig, or a new default instance if not set.
    """
    return _TOOL_CONFIG if _TOOL_CONFIG is not None else CodeSearchToolConfig()


def _get_cache() -> CodeSearchCache:
    """Get or create the module-level cache instance.

    Returns:
        CodeSearchCache instance for caching parsed AST data
    """
    global _CACHE
    if _CACHE is None:
        _CACHE = CodeSearchCache()
    return _CACHE


def _is_supported_file(file_path: Path, config: CodeSearchToolConfig) -> bool:
    """Check if file is supported for AST parsing.

    Args:
        file_path: Path to file to check
        config: Configuration with supported extensions and size limits

    Returns:
        True if file should be processed, False otherwise
    """
    # Check extension
    if file_path.suffix not in config.supported_extensions:
        return False

    # Check file size
    try:
        file_size_kb = file_path.stat().st_size / 1024
        if file_size_kb > config.max_file_size_kb:
            logger.warning(
                f"Skipping large file {file_path} ({file_size_kb:.1f}KB > {config.max_file_size_kb}KB)"
            )
            return False
    except (FileNotFoundError, OSError):
        return False

    return True


def _parse_file_ast(file_path: Path) -> list[dict[str, Any]]:
    """Parse file using grep-ast to extract symbol information.

    Args:
        file_path: Path to source file to parse

    Returns:
        List of symbol dictionaries with keys:
        - name: Symbol name
        - type: Symbol type (function, class, method, etc.)
        - line: Line number where symbol is defined
        - file: File path (as string)
        - context: Surrounding code context

    Raises:
        ToolExecutionError: If file cannot be read or parsed
    """
    try:
        # Check cache first
        cache = _get_cache()
        cached_symbols = cache.get_cached_tags(file_path)
        if cached_symbols is not None:
            return cached_symbols

        # Read file content
        code = file_path.read_text(encoding="utf-8", errors="ignore")

        # Detect language from filename
        lang = filename_to_lang(str(file_path))
        if not lang:
            logger.warning(f"Unsupported language for file: {file_path}")
            return []

        # Parse AST using tree-sitter
        try:
            parser = get_parser(lang)
            tree = parser.parse(code.encode("utf-8"))
            root_node = tree.root_node
        except Exception as e:
            logger.warning(f"Failed to get parser for language '{lang}': {e}")
            return []

        # Extract symbols by walking the tree
        symbols = _extract_symbols_from_tree(root_node, file_path, code)

        # Cache the results
        cache.cache_tags(file_path, symbols)

        return symbols

    except UnicodeDecodeError as e:
        logger.warning(f"Failed to decode file {file_path}: {e}")
        return []
    except Exception as e:
        # Log but don't fail - continue processing other files
        logger.warning(f"Failed to parse {file_path}: {e}")
        return []


def _extract_symbols_from_tree(
    node: Any,
    file_path: Path,
    code: str,
) -> list[dict[str, Any]]:
    """Extract symbol information from parsed tree.

    Args:
        node: tree-sitter Node (root node of parsed tree)
        file_path: Path to source file
        code: Source code content

    Returns:
        List of symbol dictionaries
    """
    symbols: list[dict[str, Any]] = []
    lines = code.split("\n")

    def walk_node(node: Any, parent_name: str | None = None) -> None:
        """Recursively walk AST nodes to find symbols."""
        node_type = node.type

        # Detect symbol types based on node type
        symbol_type: str | None = None
        symbol_name: str | None = None

        # Python
        if node_type == "function_definition":
            symbol_type = "function"
            # Find name child
            for child in node.children:
                if child.type == "identifier":
                    symbol_name = child.text.decode("utf-8")
                    break
        elif node_type == "class_definition":
            symbol_type = "class"
            for child in node.children:
                if child.type == "identifier":
                    symbol_name = child.text.decode("utf-8")
                    break

        # JavaScript/TypeScript / Kotlin - function_declaration (distinguish by child type)
        elif node_type in ("function_declaration", "function"):
            symbol_type = "function"
            # Check for Kotlin first (has simple_identifier)
            for child in node.children:
                if child.type == "simple_identifier":
                    symbol_name = child.text.decode("utf-8")
                    break
            # Otherwise JavaScript/TypeScript (has identifier)
            if not symbol_name:
                for child in node.children:
                    if child.type == "identifier":
                        symbol_name = child.text.decode("utf-8")
                        break

        # JavaScript/TypeScript / Kotlin - class_declaration (distinguish by checking for fun keyword in children)
        elif node_type == "class_declaration":
            symbol_type = "class"
            # Check for type_identifier (both JS/TS and Kotlin use this)
            for child in node.children:
                if child.type == "type_identifier":
                    symbol_name = child.text.decode("utf-8")
                    break
            # Fallback to identifier (JavaScript can use this)
            if not symbol_name:
                for child in node.children:
                    if child.type == "identifier":
                        symbol_name = child.text.decode("utf-8")
                        break

        elif node_type == "method_definition":
            symbol_type = "method"
            for child in node.children:
                if child.type in ("property_identifier", "identifier"):
                    symbol_name = child.text.decode("utf-8")
                    break
        elif node_type == "method_declaration":
            # Go (field_identifier) or Java/C/C++ (identifier)
            symbol_type = "method"
            # Try Java/C/C++ first (identifier)
            for child in node.children:
                if child.type == "identifier":
                    symbol_name = child.text.decode("utf-8")
                    break
            # Then try Go (field_identifier)
            if not symbol_name:
                for child in node.children:
                    if child.type == "field_identifier":
                        symbol_name = child.text.decode("utf-8")
                        break
        elif node_type == "type_declaration":
            symbol_type = "class"  # Treat Go structs/interfaces as classes
            for child in node.children:
                if child.type == "type_identifier":
                    symbol_name = child.text.decode("utf-8")
                    break

        # Rust
        elif node_type == "function_item":
            symbol_type = "function"
            for child in node.children:
                if child.type == "identifier":
                    symbol_name = child.text.decode("utf-8")
                    break
        elif node_type in ("struct_item", "impl_item"):
            symbol_type = "class"
            for child in node.children:
                if child.type == "type_identifier":
                    symbol_name = child.text.decode("utf-8")
                    break

        # Java
        elif node_type == "constructor_declaration":
            # Java constructor
            symbol_type = "method"
            for child in node.children:
                if child.type == "identifier":
                    symbol_name = child.text.decode("utf-8")
                    break

        # C/C++
        elif node_type == "struct_specifier":
            # C/C++ struct
            symbol_type = "class"
            for child in node.children:
                if child.type in ("identifier", "type_identifier"):
                    symbol_name = child.text.decode("utf-8")
                    break

        # If we found a symbol, add it
        if symbol_type and symbol_name:
            line_num = node.start_point[0] + 1  # Convert 0-based to 1-based

            # Get context lines
            context_before: list[str] = []
            context_after: list[str] = []

            if 0 <= line_num - 1 < len(lines):
                # Get 2 lines before
                for i in range(max(0, line_num - 3), line_num - 1):
                    if i < len(lines):
                        context_before.append(lines[i])

                # Get 2 lines after
                for i in range(line_num, min(len(lines), line_num + 2)):
                    if i < len(lines):
                        context_after.append(lines[i])

            symbols.append(
                {
                    "name": symbol_name,
                    "type": symbol_type,
                    "line": line_num,
                    "file": str(file_path),
                    "text": lines[line_num - 1]
                    if 0 <= line_num - 1 < len(lines)
                    else "",
                    "context_before": context_before,
                    "context_after": context_after,
                    "parent": parent_name,
                }
            )

        # Recursively process children
        current_parent = symbol_name if symbol_type == "class" else parent_name
        for child in node.children:
            walk_node(child, current_parent)

    # Start walking from root node
    walk_node(node)

    return symbols


def _search_symbols(
    path: str,
    query: str,
    symbol_type: str | None = None,
    case_sensitive: bool = False,
    config: CodeSearchToolConfig | None = None,
) -> list[dict[str, Any]]:
    """Search for symbols across files in the specified path.

    Args:
        path: Directory or file path to search
        query: Symbol name or pattern to search for (supports regex)
        symbol_type: Optional filter by symbol type (function, class, method)
        case_sensitive: Whether search is case-sensitive
        config: Tool configuration

    Returns:
        List of matching symbol dictionaries

    Raises:
        ToolExecutionError: If path doesn't exist or search fails
    """
    if config is None:
        config = get_code_search_config()

    search_path = Path(path)
    if not search_path.exists():
        raise ToolExecutionError(f"Search path does not exist: {path}")

    all_symbols: list[dict[str, Any]] = []

    # Handle single file vs directory
    if search_path.is_file():
        files_to_search = (
            [search_path] if _is_supported_file(search_path, config) else []
        )
    else:
        # Recursively find all supported files
        files_to_search = []
        for ext in config.supported_extensions:
            files_to_search.extend(search_path.rglob(f"*{ext}"))

    # Parse each file and collect symbols
    for file_path in files_to_search:
        if not _is_supported_file(file_path, config):
            continue

        try:
            symbols = _parse_file_ast(file_path)
            all_symbols.extend(symbols)
        except Exception as e:
            logger.warning(f"Error processing {file_path}: {e}")
            continue

    # Filter by query pattern
    import re

    pattern_flags = 0 if case_sensitive else re.IGNORECASE
    try:
        query_regex = re.compile(query, pattern_flags)
    except re.error as e:
        raise ToolExecutionError(f"Invalid regex pattern '{query}': {e}") from e

    matching_symbols = [sym for sym in all_symbols if query_regex.search(sym["name"])]

    # Filter by symbol type if specified
    if symbol_type:
        matching_symbols = [
            sym for sym in matching_symbols if sym["type"] == symbol_type
        ]

    return matching_symbols


@tool  # type: ignore[misc]
def code_search(
    query: str,
    path: str = ".",
    symbol_type: str | None = None,
    case_sensitive: bool = False,
) -> str:
    """Search for code symbols (functions, classes, methods) using AST parsing.

    Semantic code search that finds symbols by structure, not text patterns.
    Supports multiple languages via tree-sitter parsers with automatic caching.

    Performance is controlled via CodeSearchToolConfig.max_file_size_kb to skip
    large files. Typical search completes in <1s for 100-file repos.

    Args:
        query: Symbol name or regex pattern to search for
        path: Directory or file path to search (default: current directory)
        symbol_type: Optional filter by type: "function", "class", or "method"
        case_sensitive: Whether search is case-sensitive (default: False)

    Returns:
        JSON string with search results:
        [
            {
                "name": "calculate_total",
                "type": "function",
                "line": 42,
                "file": "src/utils.py",
                "text": "def calculate_total(items):",
                "context_before": ["", "# Calculate total price"],
                "context_after": ["    total = 0", "    for item in items:"],
                "parent": null
            },
            ...
        ]

    Raises:
        ToolExecutionError: If path doesn't exist or search fails

    Example:
        >>> code_search.invoke({"query": "calculate_total", "symbol_type": "function"})
        '[{"name": "calculate_total", "type": "function", ...}]'

        >>> code_search.invoke({"query": "Shopping.*", "symbol_type": "class", "path": "src/"})
        '[{"name": "ShoppingCart", "type": "class", ...}]'
    """
    config = get_code_search_config()

    # Execute search
    results = _search_symbols(
        path=path,
        query=query,
        symbol_type=symbol_type,
        case_sensitive=case_sensitive,
        config=config,
    )

    # Return JSON formatted results
    return json.dumps(results, indent=2)
