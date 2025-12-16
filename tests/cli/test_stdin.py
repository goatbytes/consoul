"""Tests for stdin reading functionality."""

import io
import sys

import pytest

from consoul.cli.stdin_reader import format_stdin_message, read_stdin


class MockStdin:
    """Mock stdin object with buffer attribute for testing."""

    def __init__(self, buffer, is_tty=False):
        """Initialize mock stdin.

        Args:
            buffer: BytesIO object to use as buffer
            is_tty: Whether stdin should behave like a TTY
        """
        self.buffer = buffer
        self._is_tty = is_tty

    def isatty(self):
        """Check if this is a TTY."""
        return self._is_tty


class TestReadStdin:
    """Test read_stdin function."""

    def test_read_stdin_with_content(self, monkeypatch):
        """Test reading content from stdin."""
        test_data = "test content\nline 2"
        fake_buffer = io.BytesIO(test_data.encode("utf-8"))
        fake_stdin = MockStdin(fake_buffer)
        monkeypatch.setattr(sys, "stdin", fake_stdin)

        content = read_stdin()
        assert content == test_data

    def test_read_stdin_empty(self, monkeypatch):
        """Test reading empty stdin."""
        fake_buffer = io.BytesIO(b"")
        fake_stdin = MockStdin(fake_buffer)
        monkeypatch.setattr(sys, "stdin", fake_stdin)

        content = read_stdin()
        assert content is None

    def test_read_stdin_from_tty(self, monkeypatch):
        """Test that stdin from tty returns None."""
        fake_buffer = io.BytesIO(b"data")
        fake_stdin = MockStdin(fake_buffer, is_tty=True)
        monkeypatch.setattr(sys, "stdin", fake_stdin)

        content = read_stdin()
        assert content is None

    def test_read_stdin_size_limit(self, monkeypatch):
        """Test size limit enforcement."""
        # Create data that exceeds 1KB limit
        large_data = b"x" * 1025
        fake_buffer = io.BytesIO(large_data)
        fake_stdin = MockStdin(fake_buffer)
        monkeypatch.setattr(sys, "stdin", fake_stdin)

        with pytest.raises(ValueError, match="exceeds maximum size"):
            read_stdin(max_size=1024)

    def test_read_stdin_invalid_utf8(self, monkeypatch):
        """Test handling of invalid UTF-8."""
        # Invalid UTF-8 sequence
        invalid_data = b"\xff\xfe invalid utf-8"
        fake_buffer = io.BytesIO(invalid_data)
        fake_stdin = MockStdin(fake_buffer)
        monkeypatch.setattr(sys, "stdin", fake_stdin)

        with pytest.raises(ValueError, match="invalid UTF-8"):
            read_stdin()

    def test_read_stdin_multiline(self, monkeypatch):
        """Test reading multi-line content."""
        test_data = "line 1\nline 2\nline 3"
        fake_buffer = io.BytesIO(test_data.encode("utf-8"))
        fake_stdin = MockStdin(fake_buffer)
        monkeypatch.setattr(sys, "stdin", fake_stdin)

        content = read_stdin()
        assert content == test_data
        assert content.count("\n") == 2


class TestFormatStdinMessage:
    """Test format_stdin_message function."""

    def test_format_basic(self):
        """Test basic message formatting."""
        stdin = "git diff output"
        question = "Review this diff"

        result = format_stdin_message(stdin, question)

        assert "<stdin>" in result
        assert "</stdin>" in result
        assert stdin in result
        assert question in result

    def test_format_preserves_order(self):
        """Test that stdin comes before question."""
        stdin = "context data"
        question = "user question"

        result = format_stdin_message(stdin, question)

        stdin_index = result.index(stdin)
        question_index = result.index(question)

        assert stdin_index < question_index

    def test_format_multiline_stdin(self):
        """Test formatting with multiline stdin."""
        stdin = "line 1\nline 2\nline 3"
        question = "Analyze this"

        result = format_stdin_message(stdin, question)

        assert stdin in result
        assert question in result
        assert result.count("\n") >= 3  # At least stdin lines

    def test_format_with_special_characters(self):
        """Test formatting with special characters."""
        stdin = "Code with <tags> and & symbols"
        question = "What does this do?"

        result = format_stdin_message(stdin, question)

        assert stdin in result
        assert question in result

    def test_format_preserves_whitespace(self):
        """Test that formatting preserves whitespace."""
        stdin = "  indented code\n    more indent"
        question = "Fix indentation"

        result = format_stdin_message(stdin, question)

        assert stdin in result
        assert "  indented" in result
        assert "    more indent" in result
