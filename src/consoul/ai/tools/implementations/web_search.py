"""Free web search tool using DuckDuckGo.

Provides zero-setup web search capability via DuckDuckGo's free API:
- No API keys or authentication required
- Privacy-focused search (no tracking)
- Returns structured JSON results
- Configurable result count and safety settings

Example:
    >>> from consoul.ai.tools.implementations.web_search import web_search
    >>> result = web_search.invoke({
    ...     "query": "Python programming tutorials",
    ...     "max_results": 5,
    ... })
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain_core.tools import tool

from consoul.ai.tools.exceptions import ToolExecutionError
from consoul.config.models import WebSearchToolConfig

# Module-level config that can be set by the registry
_TOOL_CONFIG: WebSearchToolConfig | None = None

logger = logging.getLogger(__name__)


def set_web_search_config(config: WebSearchToolConfig) -> None:
    """Set the module-level config for web_search tool.

    This should be called by the ToolRegistry when registering web_search
    to inject the profile's configured settings.

    Args:
        config: WebSearchToolConfig from the active profile's ToolConfig.web_search
    """
    global _TOOL_CONFIG
    _TOOL_CONFIG = config


def get_web_search_config() -> WebSearchToolConfig:
    """Get the current web_search tool config.

    Returns:
        The configured WebSearchToolConfig, or a new default instance if not set.
    """
    return _TOOL_CONFIG if _TOOL_CONFIG is not None else WebSearchToolConfig()


def _execute_search(
    query: str,
    max_results: int,
    region: str,
    safesearch: str,
    timeout: int,
) -> list[dict[str, Any]]:
    """Execute web search using DuckDuckGo.

    Args:
        query: Search query string
        max_results: Maximum number of results to return
        region: Region code for search results
        safesearch: SafeSearch filter level
        timeout: Request timeout in seconds

    Returns:
        List of search result dictionaries

    Raises:
        ToolExecutionError: If search fails
    """
    try:
        # Initialize DuckDuckGo search wrapper
        search = DuckDuckGoSearchAPIWrapper(
            max_results=max_results,
            region=region,
            safesearch=safesearch,
            time="y",  # Results from past year
            backend="auto",  # Auto-select best backend
            source="text",  # Text search (not news/images)
        )

        # Execute search - this returns a formatted string
        # We need to use results() method to get structured data
        raw_results = search.results(query, max_results=max_results)

        # Normalize results to consistent format
        results = []
        for item in raw_results:
            results.append(
                {
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", item.get("body", "")),
                    "link": item.get("link", item.get("href", "")),
                }
            )

        return results

    except Exception as e:
        # DuckDuckGo can raise various exceptions (network, rate limiting, etc.)
        logger.error(f"Web search failed for query '{query}': {e}")
        raise ToolExecutionError(
            f"Web search failed: {e}. "
            "This could be due to network issues, rate limiting, or invalid query."
        ) from e


@tool  # type: ignore[misc]
def web_search(
    query: str,
    max_results: int | None = None,
    region: str | None = None,
    safesearch: str | None = None,
) -> str:
    """Search the web using DuckDuckGo (free, no API keys required).

    Performs web search via DuckDuckGo's free API and returns structured results.
    Zero setup required - works immediately without authentication or API keys.

    Args:
        query: Search query string (e.g., "Python web scraping tutorial")
        max_results: Number of results to return (1-10, default: from config or 5)
        region: Region code (e.g., "us-en", "uk-en", default: "wt-wt" for global)
        safesearch: SafeSearch level: "strict", "moderate", or "off" (default: "moderate")

    Returns:
        JSON string with search results:
        [
            {
                "title": "Result title",
                "snippet": "Brief description of the result...",
                "link": "https://example.com/page"
            },
            ...
        ]

    Raises:
        ToolExecutionError: If search fails due to network, rate limiting, or invalid query

    Example:
        >>> web_search("LangChain tutorials", max_results=3)
        '[{"title": "LangChain Docs", "snippet": "Official documentation...", "link": "..."}]'

    Note:
        - Completely free with no API keys required
        - Privacy-focused (DuckDuckGo doesn't track searches)
        - Soft rate limits may apply (no hard documented limits)
        - For advanced features (engine selection, categories), consider SearxNG (SOUL-100)
    """
    config = get_web_search_config()

    # Use config defaults if not specified
    if max_results is None:
        max_results = config.max_results
    if region is None:
        region = config.region
    if safesearch is None:
        safesearch = config.safesearch

    # Validate max_results
    if not (1 <= max_results <= 10):
        raise ToolExecutionError(
            f"max_results must be between 1 and 10, got {max_results}"
        )

    # Validate safesearch
    if safesearch not in ("strict", "moderate", "off"):
        raise ToolExecutionError(
            f"safesearch must be 'strict', 'moderate', or 'off', got '{safesearch}'"
        )

    # Execute search
    results = _execute_search(
        query=query,
        max_results=max_results,
        region=region,
        safesearch=safesearch,
        timeout=config.timeout,
    )

    # Return JSON formatted results
    return json.dumps(results, indent=2, ensure_ascii=False)
