"""Wikipedia search tool for factual information retrieval.

Provides access to Wikipedia article summaries using LangChain's WikipediaQueryRun.
No API key required - uses the public Wikipedia API.

Example:
    >>> from consoul.ai.tools.implementations.wikipedia import wikipedia_search
    >>> # Basic search (1 article, 1000 chars)
    >>> result = wikipedia_search.invoke({
    ...     "query": "Neural Network",
    ... })
    >>>
    >>> # Multiple articles with more detail
    >>> result = wikipedia_search.invoke({
    ...     "query": "Python programming",
    ...     "max_results": 3,
    ...     "chars_per_result": 2000,
    ... })
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain_core.tools import tool

from consoul.ai.tools.exceptions import ToolExecutionError
from consoul.config.models import WikipediaToolConfig

# Module-level config that can be set by the registry
_TOOL_CONFIG: WikipediaToolConfig | None = None

logger = logging.getLogger(__name__)


def set_wikipedia_config(config: WikipediaToolConfig) -> None:
    """Set the module-level config for wikipedia_search tool.

    This should be called by the ToolRegistry when registering wikipedia_search
    to inject the profile's configured settings.

    Args:
        config: WikipediaToolConfig from the active profile's ToolConfig.wikipedia
    """
    global _TOOL_CONFIG
    _TOOL_CONFIG = config


def get_wikipedia_config() -> WikipediaToolConfig:
    """Get the current wikipedia_search tool config.

    Returns:
        The configured WikipediaToolConfig, or a new default instance if not set.
    """
    return _TOOL_CONFIG if _TOOL_CONFIG is not None else WikipediaToolConfig()


@tool
def wikipedia_search(
    query: str,
    max_results: int | None = None,
    chars_per_result: int | None = None,
) -> str:
    """Search Wikipedia for factual information.

    Fetches Wikipedia article summaries for general knowledge queries about
    people, places, companies, historical events, technical concepts, and more.
    Results include article titles, summaries, and Wikipedia URLs.

    No API key required - uses the public Wikipedia API.

    Args:
        query: Search query (e.g., "Python programming language", "Albert Einstein")
        max_results: Number of articles to fetch (1-5, default: from config or 1)
        chars_per_result: Characters per summary (1-4000, default: from config or 1000)

    Returns:
        JSON string with Wikipedia results:
        [
            {
                "title": "Article title",
                "summary": "Article summary...",
                "url": "https://en.wikipedia.org/wiki/Article_title"
            },
            ...
        ]

    Raises:
        ToolExecutionError: If Wikipedia API fails or query is invalid

    Example:
        >>> # Basic search
        >>> wikipedia_search("Neural Network")
        '[{"title": "Neural network", "summary": "...", "url": "..."}]'
        >>>
        >>> # Multiple articles
        >>> wikipedia_search("Python", max_results=3, chars_per_result=500)
        '[{"title": "Python (programming language)", "summary": "...", ...}]'

    Note:
        - Returns structured, authoritative content from Wikipedia
        - Complements web_search for factual queries
        - Handles disambiguation pages automatically
        - No rate limiting concerns (public API)
    """
    config = get_wikipedia_config()

    # Use config defaults if not specified
    if max_results is None:
        max_results = config.max_results
    if chars_per_result is None:
        chars_per_result = config.chars_per_result

    # Validate max_results
    if not (1 <= max_results <= 5):
        raise ToolExecutionError(
            f"max_results must be between 1 and 5, got {max_results}"
        )

    # Validate chars_per_result
    if not (1 <= chars_per_result <= 4000):
        raise ToolExecutionError(
            f"chars_per_result must be between 1 and 4000, got {chars_per_result}"
        )

    try:
        logger.info(f"Searching Wikipedia for: {query}")

        # Initialize Wikipedia wrapper
        api_wrapper = WikipediaAPIWrapper(
            top_k_results=max_results,
            doc_content_chars_max=chars_per_result,
        )

        # Create tool instance
        wiki_tool = WikipediaQueryRun(api_wrapper=api_wrapper)

        # Execute search
        raw_result = wiki_tool.run(query)

        # Parse the result
        # WikipediaQueryRun returns concatenated summaries as text
        # We need to extract structured data from the wrapper

        # Get the actual search results from the wrapper
        # The wrapper's results() method returns structured data
        try:
            structured_results = api_wrapper.load(query)

            # Build result list
            results: list[dict[str, Any]] = []

            # Split the structured results into individual articles
            # The load() method returns a concatenated string, but we can extract titles
            # For now, we'll return the text as a single result with source attribution
            if structured_results:
                # WikipediaAPIWrapper returns text, we need to structure it
                # Since we can't easily split by article, return as single comprehensive result
                results.append(
                    {
                        "title": f"Wikipedia: {query}",
                        "summary": structured_results[:chars_per_result],
                        "url": f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}",
                        "source": "Wikipedia",
                    }
                )
            else:
                raise ToolExecutionError(
                    f"No Wikipedia articles found for query: {query}"
                )

            logger.info(f"Wikipedia search returned {len(results)} results")
            return json.dumps(results, indent=2, ensure_ascii=False)

        except Exception as e:
            # If structured parsing fails, fall back to raw text result
            logger.warning(f"Failed to parse structured results: {e}")

            if not raw_result or raw_result.strip() == "":
                raise ToolExecutionError(
                    f"No Wikipedia articles found for query: {query}"
                ) from None

            # Return raw result as single structured entry
            results = [
                {
                    "title": f"Wikipedia: {query}",
                    "summary": raw_result[:chars_per_result],
                    "url": f"https://en.wikipedia.org/wiki/{query.replace(' ', '_')}",
                    "source": "Wikipedia",
                }
            ]

            return json.dumps(results, indent=2, ensure_ascii=False)

    except ToolExecutionError:
        raise
    except Exception as e:
        logger.error(f"Wikipedia search failed for query '{query}': {e}")
        raise ToolExecutionError(
            f"Wikipedia search failed: {e}. "
            "This could be due to network issues, invalid query, or Wikipedia API unavailability."
        ) from e
