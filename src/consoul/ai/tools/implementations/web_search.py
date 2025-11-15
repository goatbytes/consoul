"""Free web search tool with Jina AI, SearxNG, and DuckDuckGo support.

Provides flexible web search with automatic fallback priority:
- Jina AI Search (LLM-optimized, requires free API key) - Best quality
- SearxNG (self-hosted, production-grade) - Privacy and control
- DuckDuckGo (zero setup) - No configuration needed
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
from langchain_community.utilities.jina_search import JinaSearchAPIWrapper
from langchain_core.tools import tool
from pydantic import SecretStr

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


def _detect_searxng(searxng_url: str, timeout: int, verify_ssl: bool = False) -> bool:
    """Check if SearxNG instance is available and healthy.

    Args:
        searxng_url: SearxNG instance URL
        timeout: Request timeout in seconds
        verify_ssl: Whether to verify SSL certificates (False for self-signed certs)

    Returns:
        True if SearxNG is available and responding
    """
    try:
        # Try to hit the healthcheck endpoint
        response = requests.get(
            f"{searxng_url.rstrip('/')}/healthz",
            timeout=timeout,
            allow_redirects=True,
            verify=verify_ssl,  # Match SearxSearchWrapper's unsecure setting
        )
        if response.status_code == 200:
            return True

        # Fallback: try to hit search endpoint
        response = requests.get(
            f"{searxng_url.rstrip('/')}/search",
            params={"q": "test", "format": "json"},
            timeout=timeout,
            allow_redirects=True,
            verify=verify_ssl,  # Match SearxSearchWrapper's unsecure setting
        )
        return bool(response.status_code == 200)

    except Exception as e:
        logger.debug(f"SearxNG detection failed for {searxng_url}: {e}")
        return False


def _execute_jina_search(
    api_key: str,
    query: str,
    max_results: int,
    timeout: int,
) -> list[dict[str, Any]]:
    """Execute web search using Jina AI Search.

    Args:
        api_key: Jina AI API key
        query: Search query string
        max_results: Maximum number of results to return
        timeout: Request timeout in seconds

    Returns:
        List of search result dictionaries

    Raises:
        ToolExecutionError: If search fails

    Note:
        Jina Search fetches top 5 results and processes each URL with r.jina.ai
        for full content extraction. Results are LLM-optimized with clean markdown.
    """
    try:
        # Initialize Jina search wrapper
        search = JinaSearchAPIWrapper(
            api_key=SecretStr(api_key),
            base_url="https://s.jina.ai/",
        )

        # Execute search - this returns formatted text (possibly JSON)
        raw_result = search.run(query)

        # Try to parse as JSON first (Jina may return JSON array)
        try:
            parsed = json.loads(raw_result)
            if isinstance(parsed, list):
                # Already in list format - normalize structure
                results = []
                for item in parsed[:max_results]:
                    results.append(
                        {
                            "title": item.get("title", ""),
                            "snippet": item.get(
                                "snippet", item.get("description", item.get("content", ""))
                            ),
                            "link": item.get("link", item.get("url", "")),
                            "engine": "jina",
                        }
                    )
                logger.info(f"Jina Search returned {len(results)} results")
                return results
        except json.JSONDecodeError:
            # Not JSON - try parsing as text
            pass

        # Fallback: Parse text response
        # Jina might return plain text with results separated by newlines
        lines = raw_result.strip().split("\n")
        results = []

        # Try to extract structured data from text
        # This is a best-effort parser for non-JSON responses
        current_result: dict[str, Any] = {}
        for line in lines:
            line = line.strip()
            if not line:
                if current_result:
                    results.append(current_result)
                    current_result = {}
                continue

            # Try to parse title/link/snippet patterns
            if line.startswith("Title:"):
                current_result["title"] = line[6:].strip()
            elif line.startswith("URL:") or line.startswith("Link:"):
                current_result["link"] = line.split(":", 1)[1].strip()
            elif "snippet" not in current_result:
                current_result["snippet"] = line

        # Add last result if exists
        if current_result:
            results.append(current_result)

        # Ensure all results have required fields and engine tag
        normalized_results = []
        for item in results[:max_results]:
            normalized_results.append(
                {
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "link": item.get("link", ""),
                    "engine": "jina",
                }
            )

        if not normalized_results:
            raise ToolExecutionError(
                "Jina Search returned no parseable results. "
                "The response format may have changed."
            )

        logger.info(f"Jina Search returned {len(normalized_results)} results")
        return normalized_results

    except ToolExecutionError:
        raise
    except Exception as e:
        logger.error(f"Jina Search failed: {e}")
        raise ToolExecutionError(
            f"Jina Search failed: {e}. Falling back to next backend."
        ) from e


def _execute_searxng_search(
    searxng_url: str,
    query: str,
    max_results: int,
    engines: list[str] | None,
    categories: list[str] | None,
    timeout: int,
    verify_ssl: bool = False,
) -> list[dict[str, Any]]:
    """Execute web search using SearxNG.

    Args:
        searxng_url: SearxNG instance URL
        query: Search query string
        max_results: Maximum number of results to return
        engines: List of search engines to use
        categories: List of search categories
        timeout: Request timeout in seconds
        verify_ssl: Whether to verify SSL certificates (False for self-signed certs)

    Returns:
        List of search result dictionaries

    Raises:
        ToolExecutionError: If search fails
    """
    try:
        # Initialize SearxNG search wrapper
        # Note: SearxSearchWrapper uses 'unsecure' parameter (inverted logic)
        search = SearxSearchWrapper(
            searx_host=searxng_url,
            unsecure=not verify_ssl,  # unsecure=True means skip verification
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
    """Search the web using Jina AI, SearxNG, or DuckDuckGo.

    Performs web search with automatic fallback priority:
    1. Jina Search (if API key configured) - Best quality, LLM-optimized
    2. SearxNG (if URL configured) - Self-hosted, privacy-focused
    3. DuckDuckGo (always available) - Zero setup required

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
                "engine": "jina"  # Backend used: "jina", "google", etc.
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
        Backend priority (automatic fallback):
        1. Jina Search (if API key configured) - LLM-optimized results
        2. SearxNG (if URL configured) - Self-hosted meta-search
        3. DuckDuckGo (always available) - Zero-config fallback

        Features:
        - SearxNG: Engine selection and category filtering
        - Jina: Semantic search with full content extraction
        - DuckDuckGo: Privacy-focused, no tracking
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

    # Priority 1: Try Jina Search first if configured (best quality)
    if config.jina_api_key and config.jina_enabled:
        try:
            logger.info(f"Using Jina Search for query: {query}")

            results = _execute_jina_search(
                api_key=config.jina_api_key,
                query=query,
                max_results=max_results,
                timeout=config.timeout,
            )

            # Return early if Jina succeeded
            return json.dumps(results, indent=2, ensure_ascii=False)

        except ToolExecutionError as e:
            logger.warning(f"Jina Search failed, falling back to SearxNG/DuckDuckGo: {e}")
            # Continue to next backend

    # Priority 2: Try SearxNG if configured (self-hosted)
    if config.searxng_url:
        searxng_available = _detect_searxng(
            config.searxng_url, config.timeout, config.searxng_verify_ssl
        )

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
                    verify_ssl=config.searxng_verify_ssl,
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
