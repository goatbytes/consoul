"""Tests for Wikipedia search tool."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from consoul.ai.tools.exceptions import ToolExecutionError
from consoul.ai.tools.implementations.wikipedia import (
    get_wikipedia_config,
    set_wikipedia_config,
    wikipedia_search,
)
from consoul.config.models import WikipediaToolConfig


class TestWikipediaConfig:
    """Test Wikipedia tool configuration management."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = WikipediaToolConfig()
        assert config.max_results == 1
        assert config.chars_per_result == 1000
        assert config.timeout == 10

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = WikipediaToolConfig(
            max_results=3,
            chars_per_result=2000,
            timeout=20,
        )
        assert config.max_results == 3
        assert config.chars_per_result == 2000
        assert config.timeout == 20

    def test_config_validation(self) -> None:
        """Test configuration validation."""
        # max_results must be 1-5
        with pytest.raises(ValidationError):
            WikipediaToolConfig(max_results=0)
        with pytest.raises(ValidationError):
            WikipediaToolConfig(max_results=6)

        # chars_per_result must be 1-4000
        with pytest.raises(ValidationError):
            WikipediaToolConfig(chars_per_result=0)
        with pytest.raises(ValidationError):
            WikipediaToolConfig(chars_per_result=5000)

        # timeout must be 1-30
        with pytest.raises(ValidationError):
            WikipediaToolConfig(timeout=0)
        with pytest.raises(ValidationError):
            WikipediaToolConfig(timeout=31)

    def test_set_get_config(self) -> None:
        """Test setting and getting module-level config."""
        custom_config = WikipediaToolConfig(
            max_results=2,
            chars_per_result=1500,
        )
        set_wikipedia_config(custom_config)

        retrieved_config = get_wikipedia_config()
        assert retrieved_config.max_results == 2
        assert retrieved_config.chars_per_result == 1500


class TestWikipediaSearch:
    """Test Wikipedia search tool functionality."""

    @patch("consoul.ai.tools.implementations.wikipedia.WikipediaAPIWrapper")
    @patch("consoul.ai.tools.implementations.wikipedia.WikipediaQueryRun")
    def test_wikipedia_search_basic(
        self, mock_run_class: MagicMock, mock_wrapper_class: MagicMock
    ) -> None:
        """Test basic Wikipedia search."""
        # Mock the wrapper
        mock_wrapper = MagicMock()
        mock_wrapper.load.return_value = "Neural networks are computing systems inspired by biological neural networks."
        mock_wrapper_class.return_value = mock_wrapper

        # Mock the tool
        mock_tool = MagicMock()
        mock_tool.run.return_value = "Neural networks are computing systems inspired by biological neural networks."
        mock_run_class.return_value = mock_tool

        # Execute search
        result_str = wikipedia_search.invoke({"query": "Neural Network"})

        # Verify result
        result = json.loads(result_str)
        assert isinstance(result, list)
        assert len(result) > 0
        assert "title" in result[0]
        assert "summary" in result[0]
        assert "url" in result[0]
        assert "Neural" in result[0]["title"] or "Neural" in result[0]["summary"]

    @patch("consoul.ai.tools.implementations.wikipedia.WikipediaAPIWrapper")
    @patch("consoul.ai.tools.implementations.wikipedia.WikipediaQueryRun")
    def test_wikipedia_search_max_results(
        self, mock_run_class: MagicMock, mock_wrapper_class: MagicMock
    ) -> None:
        """Test Wikipedia search with max_results parameter."""
        mock_wrapper = MagicMock()
        mock_wrapper.load.return_value = "Python is a high-level programming language."
        mock_wrapper_class.return_value = mock_wrapper

        mock_tool = MagicMock()
        mock_tool.run.return_value = "Python is a high-level programming language."
        mock_run_class.return_value = mock_tool

        # Execute with max_results
        result_str = wikipedia_search.invoke(
            {
                "query": "Python",
                "max_results": 3,
            }
        )

        # Verify wrapper was called with correct parameter
        mock_wrapper_class.assert_called_once()
        call_kwargs = mock_wrapper_class.call_args[1]
        assert call_kwargs["top_k_results"] == 3

        # Verify result
        result = json.loads(result_str)
        assert isinstance(result, list)

    @patch("consoul.ai.tools.implementations.wikipedia.WikipediaAPIWrapper")
    @patch("consoul.ai.tools.implementations.wikipedia.WikipediaQueryRun")
    def test_wikipedia_search_chars_limit(
        self, mock_run_class: MagicMock, mock_wrapper_class: MagicMock
    ) -> None:
        """Test Wikipedia search with chars_per_result parameter."""
        mock_wrapper = MagicMock()
        long_text = "A" * 3000  # Longer than default
        mock_wrapper.load.return_value = long_text
        mock_wrapper_class.return_value = mock_wrapper

        mock_tool = MagicMock()
        mock_tool.run.return_value = long_text
        mock_run_class.return_value = mock_tool

        # Execute with chars_per_result
        result_str = wikipedia_search.invoke(
            {
                "query": "Test",
                "chars_per_result": 500,
            }
        )

        # Verify wrapper was called with correct parameter
        mock_wrapper_class.assert_called_once()
        call_kwargs = mock_wrapper_class.call_args[1]
        assert call_kwargs["doc_content_chars_max"] == 500

        # Verify result is truncated
        result = json.loads(result_str)
        assert len(result[0]["summary"]) <= 500

    @patch("consoul.ai.tools.implementations.wikipedia.WikipediaAPIWrapper")
    @patch("consoul.ai.tools.implementations.wikipedia.WikipediaQueryRun")
    def test_wikipedia_search_config_defaults(
        self, mock_run_class: MagicMock, mock_wrapper_class: MagicMock
    ) -> None:
        """Test that config defaults are applied when parameters not specified."""
        # Set custom config
        custom_config = WikipediaToolConfig(
            max_results=2,
            chars_per_result=1500,
        )
        set_wikipedia_config(custom_config)

        mock_wrapper = MagicMock()
        mock_wrapper.load.return_value = "Test content"
        mock_wrapper_class.return_value = mock_wrapper

        mock_tool = MagicMock()
        mock_tool.run.return_value = "Test content"
        mock_run_class.return_value = mock_tool

        # Execute without specifying parameters
        wikipedia_search.invoke({"query": "Test"})

        # Verify config defaults were used
        call_kwargs = mock_wrapper_class.call_args[1]
        assert call_kwargs["top_k_results"] == 2
        assert call_kwargs["doc_content_chars_max"] == 1500

    def test_wikipedia_search_invalid_max_results(self) -> None:
        """Test that invalid max_results raises error."""
        with pytest.raises(
            ToolExecutionError, match="max_results must be between 1 and 5"
        ):
            wikipedia_search.invoke(
                {
                    "query": "Test",
                    "max_results": 10,
                }
            )

        with pytest.raises(
            ToolExecutionError, match="max_results must be between 1 and 5"
        ):
            wikipedia_search.invoke(
                {
                    "query": "Test",
                    "max_results": 0,
                }
            )

    def test_wikipedia_search_invalid_chars_per_result(self) -> None:
        """Test that invalid chars_per_result raises error."""
        with pytest.raises(
            ToolExecutionError, match="chars_per_result must be between 1 and 4000"
        ):
            wikipedia_search.invoke(
                {
                    "query": "Test",
                    "chars_per_result": 5000,
                }
            )

        with pytest.raises(
            ToolExecutionError, match="chars_per_result must be between 1 and 4000"
        ):
            wikipedia_search.invoke(
                {
                    "query": "Test",
                    "chars_per_result": 0,
                }
            )

    @patch("consoul.ai.tools.implementations.wikipedia.WikipediaAPIWrapper")
    @patch("consoul.ai.tools.implementations.wikipedia.WikipediaQueryRun")
    def test_wikipedia_search_no_results(
        self, mock_run_class: MagicMock, mock_wrapper_class: MagicMock
    ) -> None:
        """Test Wikipedia search with no results."""
        mock_wrapper = MagicMock()
        mock_wrapper.load.return_value = ""
        mock_wrapper_class.return_value = mock_wrapper

        mock_tool = MagicMock()
        mock_tool.run.return_value = ""
        mock_run_class.return_value = mock_tool

        # Execute search that returns no results
        with pytest.raises(ToolExecutionError, match="No Wikipedia articles found"):
            wikipedia_search.invoke({"query": "XYZ_NONEXISTENT_123"})

    @patch("consoul.ai.tools.implementations.wikipedia.WikipediaAPIWrapper")
    @patch("consoul.ai.tools.implementations.wikipedia.WikipediaQueryRun")
    def test_wikipedia_search_api_error(
        self, mock_run_class: MagicMock, mock_wrapper_class: MagicMock
    ) -> None:
        """Test Wikipedia search with API error."""
        mock_wrapper = MagicMock()
        mock_wrapper.load.side_effect = Exception("API Error")
        mock_wrapper_class.return_value = mock_wrapper

        mock_tool = MagicMock()
        mock_tool.run.side_effect = Exception("API Error")
        mock_run_class.return_value = mock_tool

        # Execute search that triggers API error
        with pytest.raises(ToolExecutionError, match="Wikipedia search failed"):
            wikipedia_search.invoke({"query": "Test"})

    @patch("consoul.ai.tools.implementations.wikipedia.WikipediaAPIWrapper")
    @patch("consoul.ai.tools.implementations.wikipedia.WikipediaQueryRun")
    def test_wikipedia_search_json_format(
        self, mock_run_class: MagicMock, mock_wrapper_class: MagicMock
    ) -> None:
        """Test that Wikipedia search returns valid JSON."""
        mock_wrapper = MagicMock()
        mock_wrapper.load.return_value = "Test article content"
        mock_wrapper_class.return_value = mock_wrapper

        mock_tool = MagicMock()
        mock_tool.run.return_value = "Test article content"
        mock_run_class.return_value = mock_tool

        # Execute search
        result_str = wikipedia_search.invoke({"query": "Test"})

        # Verify JSON format
        result = json.loads(result_str)
        assert isinstance(result, list)
        assert len(result) > 0

        # Verify required fields
        first_result = result[0]
        assert "title" in first_result
        assert "summary" in first_result
        assert "url" in first_result
        assert "source" in first_result
        assert first_result["source"] == "Wikipedia"

        # Verify URL format
        assert first_result["url"].startswith("https://en.wikipedia.org/wiki/")
