"""Symbol reference finder using tree-sitter AST parsing.

Finds all usages/references of a code symbol across the codebase, complementing
code_search (which finds definitions). Provides IDE-like "Find All References"
functionality.

Example:
    >>> from consoul.ai.tools.implementations.find_references import find_references
    >>> result = find_references.invoke({
    ...     "symbol": "process_data",
    ...     "scope": "project",
    ... })
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from grep_ast import filename_to_lang
from langchain_core.tools import tool
from tree_sitter_language_pack import get_parser

from consoul.ai.tools.cache import CodeSearchCache
from consoul.ai.tools.exceptions import ToolExecutionError
from consoul.config.models import FindReferencesToolConfig

# Module-level config that can be set by the registry
_TOOL_CONFIG: FindReferencesToolConfig | None = None

# Module-level cache instance (shared with code_search for efficiency)
_CACHE: CodeSearchCache | None = None

logger = logging.getLogger(__name__)


def set_find_references_config(config: FindReferencesToolConfig) -> None:
    """Set the module-level config for find_references tool.

    This should be called by the ToolRegistry when registering find_references
    to inject the profile's configured settings.

    Args:
        config: FindReferencesToolConfig from the active profile's ToolConfig.find_references
    """
    global _TOOL_CONFIG
    _TOOL_CONFIG = config


def get_find_references_config() -> FindReferencesToolConfig:
    """Get the current module-level config.

    Returns:
        Current FindReferencesToolConfig, or default if not set
    """
    if _TOOL_CONFIG is None:
        return FindReferencesToolConfig()
    return _TOOL_CONFIG


def _get_cache() -> CodeSearchCache:
    """Get or create the module-level cache instance.

    Returns:
        Shared CodeSearchCache instance
    """
    global _CACHE
    if _CACHE is None:
        _CACHE = CodeSearchCache()
    return _CACHE


def _is_supported_file(file_path: Path, config: FindReferencesToolConfig) -> bool:
    """Check if file should be searched based on extension and size.

    Args:
        file_path: Path to file to check
        config: Tool configuration

    Returns:
        True if file should be searched, False otherwise
    """
    # Check extension
    if file_path.suffix not in config.supported_extensions:
        return False

    # Check file size
    try:
        size_kb = file_path.stat().st_size / 1024
        if size_kb > config.max_file_size_kb:
            logger.debug(
                f"Skipping {file_path}: {size_kb:.1f}KB exceeds limit "
                f"of {config.max_file_size_kb}KB"
            )
            return False
    except (FileNotFoundError, OSError):
        return False

    return True


def _parse_file_for_references(
    file_path: Path,
    symbol_pattern: re.Pattern[str],
) -> list[dict[str, Any]]:
    """Parse file to find symbol references using tree-sitter.

    Uses cache to avoid reparsing unchanged files. The cache stores all
    potential reference nodes (without pattern filtering), so different
    search patterns can benefit from the same cached parse.

    Args:
        file_path: Path to source file to parse
        symbol_pattern: Compiled regex pattern for symbol matching

    Returns:
        List of reference dictionaries with file, line, text, context
    """
    try:
        # Check cache first for ALL reference nodes (pattern-independent)
        # Note: We share the cache instance with code_search but use a different
        # key prefix to store reference data separately from symbol data
        cache = _get_cache()
        cache_key = f"refs:{file_path}"

        # Manual cache management since we need custom key prefix
        # Check if file's mtime matches cached version
        try:
            mtime = file_path.stat().st_mtime
            cached_entry = cache._cache.get(cache_key)

            if cached_entry and cached_entry.get("mtime") == mtime:
                # Cache hit - mtime matches
                cache._hits += 1
                all_reference_nodes = cached_entry["data"]
            else:
                # Cache miss - parse and cache
                cache._misses += 1

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

                # Extract ALL reference nodes (without pattern filtering)
                all_reference_nodes = _extract_all_references_from_tree(
                    root_node, file_path, code
                )

                # Cache the results with mtime
                cache._cache[cache_key] = {"mtime": mtime, "data": all_reference_nodes}

        except (FileNotFoundError, OSError):
            # File doesn't exist or can't read - skip caching
            return []

        # Filter cached nodes by pattern
        filtered_references = [
            ref for ref in all_reference_nodes if symbol_pattern.match(ref["symbol"])
        ]

        return filtered_references

    except UnicodeDecodeError as e:
        logger.warning(f"Failed to decode file {file_path}: {e}")
        return []
    except Exception as e:
        logger.warning(f"Failed to parse {file_path}: {e}")
        return []


def _extract_all_references_from_tree(
    node: Any,
    file_path: Path,
    code: str,
) -> list[dict[str, Any]]:
    """Extract ALL symbol references from parsed AST tree (for caching).

    Detects all usages (calls, imports, attribute access) but NOT definitions.
    Does NOT filter by pattern - returns all references for cache storage.

    Args:
        node: tree-sitter Node (root node of parsed tree)
        file_path: Path to source file
        code: Source code content

    Returns:
        List of ALL reference dictionaries (unfiltered)
    """
    references: list[dict[str, Any]] = []
    lines = code.split("\n")

    # Match any symbol (for cache - we'll filter later)
    any_symbol_pattern = re.compile(r".*")

    def walk_node(node: Any, parent_name: str | None = None) -> None:
        """Recursively walk AST nodes to find references."""
        # Check if this node is a reference (usage, not definition)
        ref_info = _is_reference_node(node, any_symbol_pattern)

        if ref_info:
            symbol_name, ref_type = ref_info
            line_num = node.start_point[0] + 1

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

            references.append(
                {
                    "symbol": symbol_name,
                    "type": ref_type,
                    "line": line_num,
                    "file": str(file_path),
                    "text": lines[line_num - 1]
                    if 0 <= line_num - 1 < len(lines)
                    else "",
                    "context_before": context_before,
                    "context_after": context_after,
                    "is_definition": False,
                }
            )

        # Recursively process children
        for child in node.children:
            walk_node(child, parent_name)

    # Start walking from root node
    walk_node(node)

    return references


def _is_reference_node(
    node: Any, symbol_pattern: re.Pattern[str]
) -> tuple[str, str] | None:
    """Check if AST node represents a symbol reference (usage, not definition).

    Args:
        node: tree-sitter Node to check
        symbol_pattern: Compiled regex for symbol matching

    Returns:
        Tuple of (symbol_name, reference_type) if reference found, None otherwise
    """
    node_type = node.type

    # Python references
    if node_type == "call":
        # Function call: foo() or obj.method()
        for child in node.children:
            if child.type == "identifier":
                name = child.text.decode("utf-8")
                if symbol_pattern.match(name):
                    return (name, "call")
            elif child.type == "attribute":
                # obj.method() - check the attribute name
                for subchild in child.children:
                    if subchild.type == "identifier":
                        name = subchild.text.decode("utf-8")
                        if symbol_pattern.match(name):
                            return (name, "method_call")

    elif node_type == "import_from_statement":
        # from module import foo
        for child in node.children:
            if child.type == "dotted_name":
                for subchild in child.children:
                    if subchild.type == "identifier":
                        name = subchild.text.decode("utf-8")
                        if symbol_pattern.match(name):
                            return (name, "import")

    elif node_type == "attribute":
        # self.foo or obj.foo (attribute access)
        for child in node.children:
            if child.type == "identifier":
                name = child.text.decode("utf-8")
                if symbol_pattern.match(name):
                    return (name, "attribute_access")

    # JavaScript/TypeScript / Go / Kotlin - call_expression (distinguish by child type)
    elif node_type == "call_expression":
        # Try Kotlin first (simple_identifier + navigation_expression)
        for child in node.children:
            if child.type == "simple_identifier":
                name = child.text.decode("utf-8")
                if symbol_pattern.match(name):
                    return (name, "call")
            elif child.type == "navigation_expression":
                # Kotlin: obj.method() - check navigation suffix
                for subchild in child.children:
                    if subchild.type == "navigation_suffix":
                        for id_node in subchild.children:
                            if id_node.type == "simple_identifier":
                                name = id_node.text.decode("utf-8")
                                if symbol_pattern.match(name):
                                    return (name, "method_call")

        # Then JavaScript/TypeScript (identifier + member_expression)
        for child in node.children:
            if child.type == "identifier":
                name = child.text.decode("utf-8")
                if symbol_pattern.match(name):
                    return (name, "call")
            elif child.type == "member_expression":
                # JS/TS: obj.method()
                for subchild in child.children:
                    if subchild.type in ("identifier", "property_identifier"):
                        name = subchild.text.decode("utf-8")
                        if symbol_pattern.match(name):
                            return (name, "method_call")

    elif node_type == "import_specifier":
        # JavaScript/TypeScript: import {foo} from './mod'
        for child in node.children:
            if child.type == "identifier":
                name = child.text.decode("utf-8")
                if symbol_pattern.match(name):
                    return (name, "import")

    elif node_type == "member_expression":
        # JavaScript/TypeScript: obj.foo
        for child in node.children:
            if child.type in ("identifier", "property_identifier"):
                name = child.text.decode("utf-8")
                if symbol_pattern.match(name):
                    return (name, "member_access")

    elif node_type == "selector_expression":
        # Go: obj.Method()
        for child in node.children:
            if child.type in ("identifier", "field_identifier"):
                name = child.text.decode("utf-8")
                if symbol_pattern.match(name):
                    return (name, "method_call")

    elif node_type == "navigation_expression":
        # Property access: obj.property
        for child in node.children:
            if child.type == "navigation_suffix":
                for id_node in child.children:
                    if id_node.type == "simple_identifier":
                        name = id_node.text.decode("utf-8")
                        if symbol_pattern.match(name):
                            return (name, "property_access")

    elif node_type == "import_header":
        # import com.example.MyClass
        for child in node.children:
            if child.type == "identifier":
                # Get the last identifier in dotted path
                for subchild in reversed(child.children):
                    if subchild.type == "simple_identifier":
                        name = subchild.text.decode("utf-8")
                        if symbol_pattern.match(name):
                            return (name, "import")
                        break

    # Java references
    elif node_type == "method_invocation":
        # Java method call: calc.add(5) or System.out.println()
        # The method name is the LAST identifier child (first is the object)
        identifiers = [
            child.text.decode("utf-8")
            for child in node.children
            if child.type == "identifier"
        ]
        if identifiers:
            # Last identifier is the method name
            name = identifiers[-1]
            if symbol_pattern.match(name):
                return (name, "method_call")

    elif node_type == "object_creation_expression":
        # Java constructor call: new Calculator(10)
        for child in node.children:
            if child.type == "type_identifier":
                name = child.text.decode("utf-8")
                if symbol_pattern.match(name):
                    return (name, "constructor_call")

    elif node_type == "import_declaration":
        # Java import: import java.util.ArrayList
        for child in node.children:
            if child.type == "scoped_identifier":
                # Get last part: ArrayList from java.util.ArrayList
                parts = child.text.decode("utf-8").split(".")
                if parts:
                    name = parts[-1]
                    if symbol_pattern.match(name):
                        return (name, "import")

    return None


def _find_symbol_references(
    path: str,
    symbol: str,
    scope: str,
    case_sensitive: bool,
    config: FindReferencesToolConfig,
) -> list[dict[str, Any]]:
    """Find all references to a symbol within the specified scope.

    Args:
        path: Base path to search from
        symbol: Symbol name or regex pattern
        scope: Search scope ("file", "directory", "project")
        case_sensitive: Whether matching is case-sensitive
        config: Tool configuration

    Returns:
        List of reference dictionaries

    Raises:
        ToolExecutionError: If path doesn't exist
    """
    # Validate path exists
    search_path = Path(path)
    if not search_path.exists():
        raise ToolExecutionError(f"Search path does not exist: {path}")

    all_references: list[dict[str, Any]] = []

    # Compile symbol pattern
    pattern_flags = 0 if case_sensitive else re.IGNORECASE
    try:
        symbol_regex = re.compile(symbol, pattern_flags)
    except re.error as e:
        raise ToolExecutionError(f"Invalid regex pattern '{symbol}': {e}") from e

    # Determine files to search based on scope
    if scope == "file":
        if not search_path.is_file():
            raise ToolExecutionError(f"Path is not a file: {path}")
        files_to_search = (
            [search_path] if _is_supported_file(search_path, config) else []
        )
    elif scope == "directory":
        if not search_path.is_dir():
            raise ToolExecutionError(f"Path is not a directory: {path}")
        files_to_search = []
        for ext in config.supported_extensions:
            files_to_search.extend(search_path.glob(f"*{ext}"))
    elif scope == "project":
        # Search recursively from path
        if search_path.is_file():
            search_path = search_path.parent
        files_to_search = []
        for ext in config.supported_extensions:
            files_to_search.extend(search_path.rglob(f"*{ext}"))
    else:
        raise ToolExecutionError(
            f"Invalid scope '{scope}'. Must be 'file', 'directory', or 'project'"
        )

    # Parse each file and collect references
    for file_path in files_to_search:
        if not _is_supported_file(file_path, config):
            continue

        refs = _parse_file_for_references(file_path, symbol_regex)
        all_references.extend(refs)

        # Respect max_results limit
        if len(all_references) >= config.max_results:
            all_references = all_references[: config.max_results]
            logger.warning(
                f"Reached max_results limit ({config.max_results}), truncating results"
            )
            break

    return all_references


@tool
def find_references(
    symbol: str,
    path: str = ".",
    scope: str = "project",
    case_sensitive: bool = False,
    include_definition: bool = False,
) -> str:
    """Find all references/usages of a code symbol across the codebase.

    Searches for where a symbol is used (function calls, imports, attribute access)
    rather than where it's defined. Provides IDE-like "Find All References".

    Args:
        symbol: Symbol name or regex pattern to find references for
        path: Base path to search from (default: current directory)
        scope: Search scope - "file" (single file), "directory" (non-recursive),
               or "project" (recursive from path, default)
        case_sensitive: Whether symbol matching is case-sensitive (default: False)
        include_definition: Include symbol definition in results (default: False)

    Returns:
        JSON string with reference results:
        [
            {
                "symbol": "process_data",
                "type": "call",
                "line": 42,
                "file": "src/main.py",
                "text": "    result = process_data(items)",
                "context_before": ["def main():", "    items = load_data()"],
                "context_after": ["    save_result(result)", ""],
                "is_definition": false
            },
            ...
        ]

    Raises:
        ToolExecutionError: If path doesn't exist or scope is invalid

    Example:
        >>> find_references.invoke({"symbol": "process_data", "scope": "project"})
        '[{"symbol": "process_data", "type": "call", ...}]'

        >>> find_references.invoke({
        ...     "symbol": "UserModel",
        ...     "scope": "directory",
        ...     "include_definition": True
        ... })
        '[{"symbol": "UserModel", "type": "class", "is_definition": true, ...}, ...]'
    """
    config = get_find_references_config()

    # Find all references
    results = _find_symbol_references(
        path=path,
        symbol=symbol,
        scope=scope,
        case_sensitive=case_sensitive,
        config=config,
    )

    # Optionally include definition
    if include_definition:
        # Import code_search to find definitions
        from consoul.ai.tools.implementations.code_search import _search_symbols

        try:
            # Find definitions using code_search
            from consoul.ai.tools.implementations.code_search import (
                get_code_search_config,
            )

            code_search_config = get_code_search_config()
            definitions = _search_symbols(
                path=path,
                query=symbol,
                symbol_type=None,
                case_sensitive=case_sensitive,
                config=code_search_config,
            )

            # Normalize definitions to match reference schema
            normalized_definitions = []
            for defn in definitions:
                # code_search returns "name" field, but references use "symbol"
                # Normalize to consistent schema
                normalized_defn = {
                    "symbol": defn.get("name", ""),  # Rename "name" → "symbol"
                    "type": f"definition_{defn['type']}",  # e.g., "definition_function"
                    "line": defn["line"],
                    "file": defn["file"],
                    "text": defn["text"],
                    "context_before": defn.get("context_before", []),
                    "context_after": defn.get("context_after", []),
                    "is_definition": True,
                }
                normalized_definitions.append(normalized_defn)

            results = normalized_definitions + results
        except Exception as e:
            logger.warning(f"Failed to find definitions: {e}")

    # Return JSON formatted results
    return json.dumps(results, indent=2)
