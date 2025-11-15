"""Free web search tool with SearxNG and DuckDuckGo support.

Provides flexible web search with automatic fallback:
- SearxNG (self-hosted, production-grade) as primary when configured
- DuckDuckGo (zero setup) as fallback or standalone
- No API keys or authentication required
- Privacy-focused search (no tracking)
- Returns structured JSON results
- Engine selection and categories (SearxNG only)

Example:
    >>> from consoul.ai.tools.implementations.web_search import web_search
    >>> # Basic search (uses configured backend or DuckDuckGo)
    >>> result = web_search.invoke({
    ...     "query": "Python programming tutorials",
    ...     "max_results": 5,
    ... })
    >>>
    >>> # SearxNG with engine selection
    >>> result = web_search.invoke({
    ...     "query": "machine learning papers",
    ...     "engines": ["google", "arxiv"],
    ...     "max_results": 10,
    ... })
"""

from __future__ import annotations

import json
import logging
from typing import Any

import requests
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper, SearxSearchWrapper
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


def _detect_searxng(searxng_url: str, timeout: int) -> bool:
    """Check if SearxNG instance is available and healthy.

    Args:
        searxng_url: SearxNG instance URL
        timeout: Request timeout in seconds

    Returns:
        True if SearxNG is available and responding
    """
    try:
        # Try to hit the healthcheck endpoint
        response = requests.get(
            f"{searxng_url.rstrip('/')}/healthz",
            timeout=timeout,
            allow_redirects=True,
        )
        if response.status_code == 200:
            return True

        # Fallback: try to hit search endpoint
        response = requests.get(
            f"{searxng_url.rstrip('/')}/search",
            params={"q": "test", "format": "json"},
            timeout=timeout,
            allow_redirects=True,
        )
        return bool(response.status_code == 200)

    except Exception as e:
        logger.debug(f"SearxNG detection failed for {searxng_url}: {e}")
        return False


def _execute_searxng_search(
    searxng_url: str,
    query: str,
    max_results: int,
    engines: list[str] | None,
    categories: list[str] | None,
    timeout: int,
) -> list[dict[str, Any]]:
    """Execute web search using SearxNG.

    Args:
        searxng_url: SearxNG instance URL
        query: Search query string
        max_results: Maximum number of results to return
        engines: List of search engines to use
        categories: List of search categories
        timeout: Request timeout in seconds

    Returns:
        List of search result dictionaries

    Raises:
        ToolExecutionError: If search fails
    """
    try:
        # Initialize SearxNG search wrapper
        search = SearxSearchWrapper(
            searx_host=searxng_url,
            unsecure=True,  # Allow self-signed certificates
        )

        # Build kwargs for search
        search_kwargs: dict[str, Any] = {"num_results": max_results}
        if engines:
            search_kwargs["engines"] = engines
        if categories:
            search_kwargs["categories"] = ",".join(categories)

        # Execute search using results() for structured data
        raw_results = search.results(query, **search_kwargs)

        # Normalize results to consistent format
        results = []
        for item in raw_results:
            results.append(
                {
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", item.get("body", "")),
                    "link": item.get("link", item.get("href", "")),
                    "engine": item.get("engine"),  # SearxNG provides this
                }
            )

        return results[:max_results]  # Ensure we don't exceed max_results

    except Exception as e:
        logger.warning(f"SearxNG search failed for query '{query}': {e}")
        raise ToolExecutionError(
            f"SearxNG search failed: {e}. Falling back to DuckDuckGo."
        ) from e


def _execute_duckduckgo_search(
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
        logger.error(f"DuckDuckGo search failed for query '{query}': {e}")
        raise ToolExecutionError(
            f"DuckDuckGo search failed: {e}. "
            "This could be due to network issues, rate limiting, or invalid query."
        ) from e


@tool  # type: ignore[misc]
def web_search(
    query: str,
    max_results: int | None = None,
    region: str | None = None,
    safesearch: str | None = None,
    engines: list[str] | None = None,
    categories: list[str] | None = None,
) -> str:
    """Search the web using SearxNG (if configured) or DuckDuckGo.

    Performs web search with automatic fallback: tries SearxNG first (if configured),
    falls back to DuckDuckGo on failure. Zero setup required for DuckDuckGo.

    Args:
        query: Search query string (e.g., "Python web scraping tutorial")
        max_results: Number of results to return (1-10, default: from config or 5)
        region: Region code for DuckDuckGo (e.g., "us-en", default: "wt-wt")
        safesearch: SafeSearch level for DuckDuckGo: "strict", "moderate", "off"
        engines: Search engines to use (SearxNG only, e.g., ["google", "arxiv"])
        categories: Search categories (SearxNG only, e.g., ["general", "it"])

    Returns:
        JSON string with search results:
        [
            {
                "title": "Result title",
                "snippet": "Brief description of the result...",
                "link": "https://example.com/page",
                "engine": "google"  # Only present for SearxNG results
            },
            ...
        ]

    Raises:
        ToolExecutionError: If both SearxNG and DuckDuckGo fail

    Example:
        >>> # Basic search (uses configured backend)
        >>> web_search("LangChain tutorials", max_results=3)
        '[{"title": "LangChain Docs", "snippet": "...", "link": "..."}]'
        >>>
        >>> # SearxNG with specific engines
        >>> web_search("ML papers", engines=["arxiv", "google"], max_results=5)
        '[{"title": "...", "snippet": "...", "link": "...", "engine": "arxiv"}]'

    Note:
        - Completely free with no API keys required
        - Privacy-focused (no tracking)
        - SearxNG provides engine selection and categories
        - Automatic fallback to DuckDuckGo if SearxNG unavailable
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

    # Validate engine/category parameters
    if engines and not config.enable_engine_selection:
        raise ToolExecutionError("Engine selection is disabled in configuration")
    if categories and not config.enable_categories:
        raise ToolExecutionError("Category selection is disabled in configuration")

    results: list[dict[str, Any]] = []

    # Try SearxNG first if configured
    if config.searxng_url:
        searxng_available = _detect_searxng(config.searxng_url, config.timeout)

        if searxng_available:
            try:
                logger.info(f"Using SearxNG for search: {query}")

                # Use provided engines or config default
                search_engines = engines if engines else config.searxng_engines

                results = _execute_searxng_search(
                    searxng_url=config.searxng_url,
                    query=query,
                    max_results=max_results,
                    engines=search_engines,
                    categories=categories,
                    timeout=config.timeout,
                )

                # Return early if SearxNG succeeded
                return json.dumps(results, indent=2, ensure_ascii=False)

            except ToolExecutionError as e:
                logger.warning(f"SearxNG failed, falling back to DuckDuckGo: {e}")
                # Continue to DuckDuckGo fallback
        else:
            logger.warning(
                f"SearxNG configured but unavailable at {config.searxng_url}, "
                "falling back to DuckDuckGo"
            )

    # Use DuckDuckGo (either as fallback or standalone)
    logger.info(f"Using DuckDuckGo for search: {query}")
    results = _execute_duckduckgo_search(
        query=query,
        max_results=max_results,
        region=region,
        safesearch=safesearch,
        timeout=config.timeout,
    )

    # Return JSON formatted results
    return json.dumps(results, indent=2, ensure_ascii=False)
