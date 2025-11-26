"""Tests for enhanced CLI input with prompt_toolkit."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest

from consoul.cli.input import get_user_input

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def temp_history_file(tmp_path: Path) -> Path:
    """Create a temporary history file path."""
    return tmp_path / "test_history"


@patch("consoul.cli.input.PromptSession")
def test_get_user_input_basic(mock_prompt_session_class: Mock) -> None:
    """Test basic input returns user text."""
    # Mock the prompt session
    mock_session = Mock()
    mock_session.prompt.return_value = "Hello, world!"
    mock_prompt_session_class.return_value = mock_session

    result = get_user_input()

    assert result == "Hello, world!"
    mock_session.prompt.assert_called_once()


@patch("consoul.cli.input.PromptSession")
def test_get_user_input_strips_whitespace(mock_prompt_session_class: Mock) -> None:
    """Test that input is stripped of leading/trailing whitespace."""
    mock_session = Mock()
    mock_session.prompt.return_value = "  test input  \n"
    mock_prompt_session_class.return_value = mock_session

    result = get_user_input()

    assert result == "test input"


@patch("consoul.cli.input.PromptSession")
def test_get_user_input_exit_command(mock_prompt_session_class: Mock) -> None:
    """Test that exit commands return None."""
    mock_session = Mock()
    mock_prompt_session_class.return_value = mock_session

    # Test various exit commands
    exit_commands = ["exit", "quit", "/quit", "EXIT", "QUIT", "/QUIT"]
    for command in exit_commands:
        mock_session.prompt.return_value = command
        result = get_user_input()
        assert result is None, f"{command} should return None"


@patch("consoul.cli.input.PromptSession")
def test_get_user_input_empty_returns_none(mock_prompt_session_class: Mock) -> None:
    """Test that empty input returns None."""
    mock_session = Mock()
    mock_prompt_session_class.return_value = mock_session

    # Test empty string and whitespace-only
    for empty_input in ["", "  ", "\n", "\t"]:
        mock_session.prompt.return_value = empty_input
        result = get_user_input()
        assert result is None, f"'{empty_input}' should return None"


@patch("consoul.cli.input.PromptSession")
def test_get_user_input_eof_error(mock_prompt_session_class: Mock) -> None:
    """Test that EOFError (Ctrl+D) returns None."""
    mock_session = Mock()
    mock_session.prompt.side_effect = EOFError()
    mock_prompt_session_class.return_value = mock_session

    result = get_user_input()

    assert result is None


@patch("consoul.cli.input.PromptSession")
def test_get_user_input_keyboard_interrupt(mock_prompt_session_class: Mock) -> None:
    """Test that KeyboardInterrupt (Ctrl+C) returns None."""
    mock_session = Mock()
    mock_session.prompt.side_effect = KeyboardInterrupt()
    mock_prompt_session_class.return_value = mock_session

    result = get_user_input()

    assert result is None


@patch("consoul.cli.input.PromptSession")
@patch("consoul.cli.input.FileHistory")
def test_get_user_input_custom_history_file(
    mock_file_history: Mock, mock_prompt_session_class: Mock, temp_history_file: Path
) -> None:
    """Test that custom history file is used."""
    mock_session = Mock()
    mock_session.prompt.return_value = "test"
    mock_prompt_session_class.return_value = mock_session
    mock_history = Mock()
    mock_file_history.return_value = mock_history

    result = get_user_input(history_file=temp_history_file)

    assert result == "test"
    # Verify FileHistory was called with the custom path
    mock_file_history.assert_called_once_with(str(temp_history_file))
    # Verify history was passed to PromptSession
    call_kwargs = mock_prompt_session_class.call_args[1]
    assert call_kwargs["history"] == mock_history


@patch("consoul.cli.input.PromptSession")
@patch("consoul.cli.input.FileHistory")
def test_get_user_input_default_history_location(
    mock_file_history: Mock, mock_prompt_session_class: Mock
) -> None:
    """Test that default history location is used when not specified."""
    mock_session = Mock()
    mock_session.prompt.return_value = "test"
    mock_prompt_session_class.return_value = mock_session
    mock_history = Mock()
    mock_file_history.return_value = mock_history

    result = get_user_input(history_file=None)

    assert result == "test"
    # Verify FileHistory was called with default path
    call_args = mock_file_history.call_args[0][0]
    assert ".consoul/chat_history" in call_args


@patch("consoul.cli.input.PromptSession")
def test_get_user_input_custom_prompt_text(mock_prompt_session_class: Mock) -> None:
    """Test that custom prompt text is used."""
    mock_session = Mock()
    mock_session.prompt.return_value = "test"
    mock_prompt_session_class.return_value = mock_session

    result = get_user_input(prompt_text="Ask me: ")

    assert result == "test"
    # Verify prompt text was used in FormattedText
    call_args = mock_prompt_session_class.call_args[1]
    formatted_prompt = call_args["message"]
    assert any("Ask me: " in str(item) for item in formatted_prompt)


@patch("consoul.cli.input.PromptSession")
def test_get_user_input_multiline_mode(mock_prompt_session_class: Mock) -> None:
    """Test that multiline mode is passed to PromptSession."""
    mock_session = Mock()
    mock_session.prompt.return_value = "line1\nline2"
    mock_prompt_session_class.return_value = mock_session

    result = get_user_input(multiline=True)

    assert result == "line1\nline2"
    # Verify multiline=True was passed
    call_kwargs = mock_prompt_session_class.call_args[1]
    assert call_kwargs["multiline"] is True


@patch("consoul.cli.input.PromptSession")
def test_get_user_input_single_line_mode_default(
    mock_prompt_session_class: Mock,
) -> None:
    """Test that single-line mode is default."""
    mock_session = Mock()
    mock_session.prompt.return_value = "test"
    mock_prompt_session_class.return_value = mock_session

    result = get_user_input()

    assert result == "test"
    # Verify multiline=False by default
    call_kwargs = mock_prompt_session_class.call_args[1]
    assert call_kwargs["multiline"] is False


@patch("consoul.cli.input.PromptSession")
def test_get_user_input_style_configuration(mock_prompt_session_class: Mock) -> None:
    """Test that Consoul style is configured."""
    mock_session = Mock()
    mock_session.prompt.return_value = "test"
    mock_prompt_session_class.return_value = mock_session

    result = get_user_input()

    assert result == "test"
    # Verify style was passed
    call_kwargs = mock_prompt_session_class.call_args[1]
    assert "style" in call_kwargs
    assert call_kwargs["style"] is not None


@patch("consoul.cli.input.PromptSession")
@patch("consoul.cli.input.FileHistory")
def test_get_user_input_creates_history_directory(
    mock_file_history: Mock, mock_prompt_session_class: Mock, temp_history_file: Path
) -> None:
    """Test that history directory is created if it doesn't exist."""
    # Use a path with non-existent parent directory
    nested_path = temp_history_file.parent / "nested" / "history"

    mock_session = Mock()
    mock_session.prompt.return_value = "test"
    mock_prompt_session_class.return_value = mock_session
    mock_file_history.return_value = Mock()

    result = get_user_input(history_file=nested_path)

    assert result == "test"
    # Verify parent directory was created
    assert nested_path.parent.exists()
