"""Tool discovery for auto-loading custom tools from directories."""

from __future__ import annotations

import importlib.util
import inspect
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from consoul.ai.tools.base import RiskLevel

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool

logger = logging.getLogger(__name__)


def discover_tools_from_directory(
    directory: Path | str,
    recursive: bool = True,
) -> list[tuple[BaseTool, RiskLevel]]:
    """Discover tools from a directory.

    Scans Python files in the specified directory for:
    - Functions decorated with @tool
    - Classes that inherit from BaseTool

    Args:
        directory: Directory to scan for tools
        recursive: Whether to recursively scan subdirectories (default: True)

    Returns:
        List of (tool, risk_level) tuples for discovered tools.
        All discovered tools default to RiskLevel.CAUTION for safety.

    Example:
        ```python
        from pathlib import Path
        from consoul.ai.tools.discovery import discover_tools_from_directory

        # Discover tools from .consoul/tools/
        tools = discover_tools_from_directory(Path(".consoul/tools"))

        # Non-recursive scan
        tools = discover_tools_from_directory(Path(".consoul/tools"), recursive=False)
        ```

    Notes:
        - Syntax errors in tool files are logged as warnings and skipped
        - Import errors are logged as warnings and skipped
        - Non-tool objects are silently ignored
        - Discovered tools are assigned RiskLevel.CAUTION by default
    """
    directory = Path(directory)

    if not directory.exists():
        logger.debug(f"Tool directory does not exist: {directory}")
        return []

    if not directory.is_dir():
        logger.warning(f"Tool path is not a directory: {directory}")
        return []

    discovered_tools: list[tuple[BaseTool, RiskLevel]] = []

    # Find all Python files
    pattern = "**/*.py" if recursive else "*.py"
    python_files = list(directory.glob(pattern))

    for file_path in python_files:
        # Skip __init__.py and private files
        if file_path.name.startswith("_"):
            continue

        tools = _load_tools_from_file(file_path)
        discovered_tools.extend(tools)

    logger.info(f"Discovered {len(discovered_tools)} tools from {directory}")
    return discovered_tools


def _load_tools_from_file(file_path: Path) -> list[tuple[BaseTool, RiskLevel]]:
    """Load tools from a single Python file.

    Args:
        file_path: Path to Python file to load

    Returns:
        List of (tool, risk_level) tuples found in the file
    """
    tools: list[tuple[BaseTool, RiskLevel]] = []

    try:
        # Import the module
        module_name = f"_consoul_discovered_{file_path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, file_path)

        if spec is None or spec.loader is None:
            logger.warning(f"Could not load spec for {file_path}")
            return []

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Inspect module for tools
        for name, obj in inspect.getmembers(module):
            # Skip private/dunder attributes
            if name.startswith("_"):
                continue

            # Check if it's a BaseTool instance or @tool decorated function
            if _is_tool(obj):
                tools.append((obj, RiskLevel.CAUTION))
                logger.debug(f"Discovered tool '{name}' in {file_path.name}")

    except SyntaxError as e:
        logger.warning(f"Syntax error in {file_path}: {e}")
    except ImportError as e:
        logger.warning(f"Import error in {file_path}: {e}")
    except Exception as e:
        logger.warning(f"Error loading tools from {file_path}: {e}")

    return tools


def _is_tool(obj: object) -> bool:
    """Check if an object is a LangChain tool.

    Args:
        obj: Object to check

    Returns:
        True if object is a BaseTool instance (has name and run attributes)
    """
    # Check for BaseTool interface (has name and run)
    # We use duck typing to avoid importing langchain_core.tools.BaseTool
    # which would create a hard dependency
    return (
        hasattr(obj, "name")
        and hasattr(obj, "run")
        and callable(getattr(obj, "run", None))
        and not inspect.isclass(obj)  # Exclude classes, only instances
    )
