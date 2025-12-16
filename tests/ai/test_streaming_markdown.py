"""Integration tests for markdown rendering in streaming responses."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from consoul.ai.streaming import stream_response


@pytest.fixture
def mock_chat_model_with_markdown():
    """Create a mock chat model that returns markdown content."""
    model = Mock()

    def mock_stream_markdown(messages):
        """Stream markdown content with code blocks."""
        markdown_chunks = [
            "Here's ",
            "some ",
            "**bold** ",
            "text ",
            "and ",
            "a ",
            "code ",
            "block:\n\n",
            "```python\n",
            "def hello():\n",
            "    print('Hello, World!')\n",
            "```\n",
        ]
        for chunk in markdown_chunks:
            mock_chunk = Mock()
            mock_chunk.content = chunk
            mock_chunk.tool_call_chunks = []  # No tool calls
            yield mock_chunk

    model.stream = Mock(side_effect=mock_stream_markdown)
    return model


@pytest.fixture
def mock_chat_model_with_lists():
    """Create a mock chat model that returns markdown lists."""
    model = Mock()

    def mock_stream_lists(messages):
        """Stream markdown content with lists."""
        list_chunks = [
            "Here's ",
            "a ",
            "list:\n\n",
            "- Item 1\n",
            "- Item 2\n",
            "- Item 3\n",
            "\n",
            "And ",
            "numbered:\n\n",
            "1. First\n",
            "2. Second\n",
            "3. Third\n",
        ]
        for chunk in list_chunks:
            mock_chunk = Mock()
            mock_chunk.content = chunk
            mock_chunk.tool_call_chunks = []  # No tool calls
            yield mock_chunk

    model.stream = Mock(side_effect=mock_stream_lists)
    return model


@pytest.fixture
def mock_chat_model_with_headers():
    """Create a mock chat model that returns markdown headers."""
    model = Mock()

    def mock_stream_headers(messages):
        """Stream markdown content with headers."""
        header_chunks = [
            "# Main Title\n\n",
            "Some intro text.\n\n",
            "## Section 1\n\n",
            "Content here.\n\n",
            "### Subsection\n\n",
            "More details.\n",
        ]
        for chunk in header_chunks:
            mock_chunk = Mock()
            mock_chunk.content = chunk
            mock_chunk.tool_call_chunks = []  # No tool calls
            yield mock_chunk

    model.stream = Mock(side_effect=mock_stream_headers)
    return model


@patch("consoul.ai.streaming.Markdown")
def test_stream_response_renders_code_blocks(
    mock_markdown_class, mock_chat_model_with_markdown
):
    """Test that code blocks are rendered as markdown."""
    mock_md = Mock()
    mock_markdown_class.return_value = mock_md

    messages = [{"role": "user", "content": "Show me code"}]
    response, _ = stream_response(
        mock_chat_model_with_markdown,
        messages,
        console=None,  # Let it create its own console
        show_spinner=True,
        render_markdown=True,
    )

    # Verify response contains markdown
    assert "**bold**" in response
    assert "```python" in response
    assert "def hello():" in response

    # Verify Markdown was created
    mock_markdown_class.assert_called_once()
    call_args = mock_markdown_class.call_args[0][0]
    assert "**bold**" in call_args
    assert "```python" in call_args


@patch("consoul.ai.streaming.Markdown")
def test_stream_response_renders_lists(mock_markdown_class, mock_chat_model_with_lists):
    """Test that lists are rendered as markdown."""
    mock_md = Mock()
    mock_markdown_class.return_value = mock_md

    messages = [{"role": "user", "content": "Give me a list"}]
    response, _ = stream_response(
        mock_chat_model_with_lists,
        messages,
        console=None,  # Let it create its own console
        show_spinner=True,
        render_markdown=True,
    )

    # Verify response contains list items
    assert "- Item 1" in response
    assert "1. First" in response

    # Verify Markdown was created with list content
    mock_markdown_class.assert_called_once()
    call_args = mock_markdown_class.call_args[0][0]
    assert "- Item 1" in call_args
    assert "1. First" in call_args


@patch("consoul.ai.streaming.Markdown")
def test_stream_response_renders_headers(
    mock_markdown_class, mock_chat_model_with_headers
):
    """Test that headers are rendered as markdown."""
    mock_md = Mock()
    mock_markdown_class.return_value = mock_md

    messages = [{"role": "user", "content": "Give me sections"}]
    response, _ = stream_response(
        mock_chat_model_with_headers,
        messages,
        console=None,  # Let it create its own console
        show_spinner=True,
        render_markdown=True,
    )

    # Verify response contains headers
    assert "# Main Title" in response
    assert "## Section 1" in response
    assert "### Subsection" in response

    # Verify Markdown was created with header content
    mock_markdown_class.assert_called_once()
    call_args = mock_markdown_class.call_args[0][0]
    assert "# Main Title" in call_args
    assert "## Section 1" in call_args


@patch("consoul.ai.streaming.Markdown")
def test_stream_response_plain_text_when_disabled(
    mock_markdown_class, mock_chat_model_with_markdown
):
    """Test that markdown rendering can be disabled."""
    messages = [{"role": "user", "content": "Show me code"}]
    response, _ = stream_response(
        mock_chat_model_with_markdown,
        messages,
        console=None,  # Let it create its own console
        show_spinner=False,
        render_markdown=False,  # Disabled
    )

    # Response still contains markdown syntax (not rendered)
    assert "**bold**" in response
    assert "```python" in response

    # Verify Markdown was NOT called when disabled
    mock_markdown_class.assert_not_called()


@patch("consoul.ai.streaming.Markdown")
def test_stream_response_empty_content(mock_markdown_class):
    """Test handling of empty responses."""
    mock_md = Mock()
    mock_markdown_class.return_value = mock_md

    # Mock model that returns empty chunks
    model = Mock()

    def mock_stream_empty(messages):
        empty_chunks = []
        yield from empty_chunks

    model.stream = Mock(side_effect=mock_stream_empty)

    messages = [{"role": "user", "content": "Empty response"}]
    response, _ = stream_response(
        model,
        messages,
        console=None,  # Let it create its own console
        show_spinner=True,
        render_markdown=True,
    )

    # Empty response
    assert response == ""

    # Markdown should not be called for empty content
    mock_markdown_class.assert_not_called()


@patch("consoul.ai.streaming.Markdown")
def test_stream_response_no_spinner_with_markdown(
    mock_markdown_class, mock_chat_model_with_markdown
):
    """Test markdown rendering without spinner."""
    mock_md = Mock()
    mock_markdown_class.return_value = mock_md

    messages = [{"role": "user", "content": "Show me code"}]
    response, _ = stream_response(
        mock_chat_model_with_markdown,
        messages,
        console=None,  # Let it create its own console
        show_spinner=False,  # No spinner
        render_markdown=True,
    )

    # Verify response contains markdown
    assert "**bold**" in response
    assert "```python" in response

    # Verify Markdown was still created
    mock_markdown_class.assert_called_once()
