"""Tests for --system flag functionality in ask and chat commands."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from consoul.cli import ChatSession


@pytest.fixture
def mock_config():
    """Create a mock ConsoulConfig for testing."""
    config = Mock()
    config.current_provider = Mock(value="anthropic")
    config.current_model = "claude-3-5-sonnet-20241022"

    # Mock model config
    model_config = Mock()
    model_config.model = "claude-3-5-sonnet-20241022"
    model_config.provider = "anthropic"
    config.get_current_model_config = Mock(return_value=model_config)

    # Mock profile with system prompt
    profile = Mock()
    profile.system_prompt = "You are a helpful AI assistant."
    profile.conversation = Mock(persist=False)
    profile.context = Mock(
        include_system_info=False,
        include_git_info=False,
    )
    config.get_active_profile = Mock(return_value=profile)

    return config


@pytest.fixture
def mock_conversation_service():
    """Create a mock ConversationService."""
    service = Mock()
    conversation = Mock()
    conversation.messages = []
    service.conversation = conversation
    service.model = Mock()
    # Mock tool_registry to return empty list for list_tools()
    tool_registry = Mock()
    tool_registry.list_tools.return_value = []
    service.tool_registry = tool_registry
    return service


@patch("consoul.cli.chat_session.ConversationService")
def test_system_prompt_override_prepends_to_profile(
    mock_service_class, mock_config, mock_conversation_service
):
    """Test that --system flag prepends to profile system prompt."""
    mock_service_class.from_config.return_value = mock_conversation_service

    override = "You are a Python expert."

    _ = ChatSession(mock_config, system_prompt_override=override)

    # Verify add_system_message was called
    assert mock_conversation_service.conversation.add_system_message.called

    # Get the system prompt that was added
    call_args = mock_conversation_service.conversation.add_system_message.call_args[0]
    system_prompt = call_args[0]

    # Verify override is prepended to profile prompt
    assert override in system_prompt
    assert "You are a helpful AI assistant." in system_prompt
    assert system_prompt.index(override) < system_prompt.index(
        "You are a helpful AI assistant."
    )


@patch("consoul.cli.chat_session.ConversationService")
def test_system_prompt_override_without_profile_prompt(
    mock_service_class, mock_config, mock_conversation_service
):
    """Test --system flag works when profile has no system prompt."""
    mock_service_class.from_config.return_value = mock_conversation_service

    # Remove profile system prompt
    profile = mock_config.get_active_profile()
    profile.system_prompt = None

    override = "You are a security expert."

    _ = ChatSession(mock_config, system_prompt_override=override)

    # Verify add_system_message was called
    assert mock_conversation_service.conversation.add_system_message.called

    # Get the system prompt
    call_args = mock_conversation_service.conversation.add_system_message.call_args[0]
    system_prompt = call_args[0]

    # Verify override becomes the system prompt
    assert override in system_prompt


@patch("consoul.cli.chat_session.ConversationService")
def test_no_system_prompt_override(
    mock_service_class, mock_config, mock_conversation_service
):
    """Test normal behavior without --system flag."""
    mock_service_class.from_config.return_value = mock_conversation_service

    _ = ChatSession(mock_config)

    # Verify add_system_message was called with profile prompt only
    assert mock_conversation_service.conversation.add_system_message.called

    call_args = mock_conversation_service.conversation.add_system_message.call_args[0]
    system_prompt = call_args[0]

    # Should contain profile prompt
    assert "You are a helpful AI assistant." in system_prompt


@patch("consoul.cli.chat_session.ConversationService")
@patch("consoul.ai.environment.get_environment_context")
def test_system_prompt_with_environment_context(
    mock_env_context,
    mock_service_class,
    mock_config,
    mock_conversation_service,
):
    """Test --system flag with environment context injection enabled."""
    mock_service_class.from_config.return_value = mock_conversation_service

    # Enable environment context
    profile = mock_config.get_active_profile()
    profile.context.include_system_info = True
    profile.context.include_git_info = True

    # Mock environment context
    mock_env_context.return_value = "# Environment\nOS: macOS\nShell: zsh"

    override = "You are a code reviewer."

    _ = ChatSession(mock_config, system_prompt_override=override)

    # Verify add_system_message was called
    assert mock_conversation_service.conversation.add_system_message.called

    call_args = mock_conversation_service.conversation.add_system_message.call_args[0]
    system_prompt = call_args[0]

    # Verify override is present
    assert override in system_prompt
    assert "You are a helpful AI assistant." in system_prompt


@patch("consoul.cli.chat_session.ConversationService")
def test_system_prompt_with_tools(
    mock_service_class, mock_config, mock_conversation_service
):
    """Test --system flag with tool registry."""
    mock_service_class.from_config.return_value = mock_conversation_service

    override = "You are a Python expert."

    _ = ChatSession(
        mock_config,
        system_prompt_override=override,
    )

    # Verify add_system_message was called
    assert mock_conversation_service.conversation.add_system_message.called

    call_args = mock_conversation_service.conversation.add_system_message.call_args[0]
    system_prompt = call_args[0]

    # Verify override is present
    assert override in system_prompt


@patch("consoul.cli.chat_session.ConversationService")
def test_empty_system_prompt_override(
    mock_service_class, mock_config, mock_conversation_service
):
    """Test empty string for --system flag is treated as no override."""
    mock_service_class.from_config.return_value = mock_conversation_service

    # Empty string override
    override = ""

    _ = ChatSession(mock_config, system_prompt_override=override)

    # Verify add_system_message was called
    assert mock_conversation_service.conversation.add_system_message.called

    call_args = mock_conversation_service.conversation.add_system_message.call_args[0]
    system_prompt = call_args[0]

    # Should only contain profile prompt (empty string is falsy)
    assert "You are a helpful AI assistant." in system_prompt


@patch("consoul.cli.chat_session.ConversationService")
def test_multiline_system_prompt_override(
    mock_service_class, mock_config, mock_conversation_service
):
    """Test multi-line --system flag content."""
    mock_service_class.from_config.return_value = mock_conversation_service

    # Multi-line override
    override = """You are an expert programmer.
Focus on code quality and best practices.
Prioritize security and performance."""

    _ = ChatSession(mock_config, system_prompt_override=override)

    # Verify add_system_message was called
    assert mock_conversation_service.conversation.add_system_message.called

    call_args = mock_conversation_service.conversation.add_system_message.call_args[0]
    system_prompt = call_args[0]

    # Verify all lines are present
    assert "expert programmer" in system_prompt
    assert "code quality" in system_prompt
    assert "security and performance" in system_prompt


# Tests for --system-file flag


@patch("consoul.cli.chat_session.ConversationService")
def test_system_file_basic(
    mock_service_class, mock_config, mock_conversation_service, tmp_path
):
    """Test --system-file flag reads from file."""
    mock_service_class.from_config.return_value = mock_conversation_service

    # Create test file
    prompt_file = tmp_path / "prompt.txt"
    prompt_content = "You are a Python expert.\nFocus on best practices."
    prompt_file.write_text(prompt_content, encoding="utf-8")

    # Import _read_system_prompt_file
    from consoul.__main__ import _read_system_prompt_file

    system_prompt = _read_system_prompt_file(str(prompt_file))

    _ = ChatSession(mock_config, system_prompt_override=system_prompt)

    assert mock_conversation_service.conversation.add_system_message.called
    call_args = mock_conversation_service.conversation.add_system_message.call_args[0]
    result = call_args[0]

    assert "Python expert" in result
    assert "best practices" in result


def test_system_file_too_large(tmp_path):
    """Test --system-file rejects files over 10KB."""

    from consoul.__main__ import _read_system_prompt_file

    # Create file larger than 10KB
    prompt_file = tmp_path / "large_prompt.txt"
    large_content = "x" * 11_000  # 11KB
    prompt_file.write_text(large_content, encoding="utf-8")

    with pytest.raises(ValueError, match="too large"):
        _read_system_prompt_file(str(prompt_file))


def test_system_file_utf8(tmp_path):
    """Test --system-file handles UTF-8 content."""

    from consoul.__main__ import _read_system_prompt_file

    prompt_file = tmp_path / "utf8_prompt.txt"
    utf8_content = "You are an expert. 你好 🌍"
    prompt_file.write_text(utf8_content, encoding="utf-8")

    result = _read_system_prompt_file(str(prompt_file))

    assert "你好" in result
    assert "🌍" in result


def test_system_file_empty(tmp_path):
    """Test --system-file with empty file returns empty string."""

    from consoul.__main__ import _read_system_prompt_file

    prompt_file = tmp_path / "empty.txt"
    prompt_file.write_text("", encoding="utf-8")

    result = _read_system_prompt_file(str(prompt_file))

    assert result == ""


def test_system_file_whitespace_only(tmp_path):
    """Test --system-file strips whitespace."""

    from consoul.__main__ import _read_system_prompt_file

    prompt_file = tmp_path / "whitespace.txt"
    prompt_file.write_text("  \n\n  You are helpful  \n\n  ", encoding="utf-8")

    result = _read_system_prompt_file(str(prompt_file))

    assert result == "You are helpful"


def test_system_file_multiline(tmp_path):
    """Test --system-file preserves multiline content."""

    from consoul.__main__ import _read_system_prompt_file

    prompt_file = tmp_path / "multiline.txt"
    multiline_content = """You are a code reviewer.

Rules:
1. Check for bugs
2. Verify tests
3. Review documentation

Focus on quality."""
    prompt_file.write_text(multiline_content, encoding="utf-8")

    result = _read_system_prompt_file(str(prompt_file))

    assert "code reviewer" in result
    assert "Rules:" in result
    assert "1. Check for bugs" in result
    assert "Focus on quality" in result


@patch("consoul.cli.chat_session.ConversationService")
def test_system_file_prepends_to_profile(
    mock_service_class, mock_config, mock_conversation_service, tmp_path
):
    """Test --system-file prepends to profile prompt (same as --system)."""

    mock_service_class.from_config.return_value = mock_conversation_service

    prompt_file = tmp_path / "prepend_test.txt"
    prompt_file.write_text("Override instruction.", encoding="utf-8")

    from consoul.__main__ import _read_system_prompt_file

    override = _read_system_prompt_file(str(prompt_file))

    _ = ChatSession(mock_config, system_prompt_override=override)

    assert mock_conversation_service.conversation.add_system_message.called
    call_args = mock_conversation_service.conversation.add_system_message.call_args[0]
    system_prompt = call_args[0]

    # Verify override is prepended to profile prompt
    assert "Override instruction" in system_prompt
    assert "You are a helpful AI assistant." in system_prompt
    assert system_prompt.index("Override instruction") < system_prompt.index(
        "You are a helpful AI assistant."
    )
