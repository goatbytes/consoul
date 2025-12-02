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
def mock_chat_model():
    """Create a mock chat model."""
    model = Mock()
    return model


@patch("consoul.cli.chat_session.get_chat_model")
@patch("consoul.cli.chat_session.ConversationHistory")
def test_system_prompt_override_prepends_to_profile(
    mock_history_class, mock_get_chat_model, mock_config, mock_chat_model
):
    """Test that --system flag prepends to profile system prompt."""
    mock_get_chat_model.return_value = mock_chat_model
    mock_history = Mock()
    mock_history_class.return_value = mock_history

    override = "You are a Python expert."

    _ = ChatSession(mock_config, system_prompt_override=override)

    # Verify add_system_message was called
    assert mock_history.add_system_message.called

    # Get the system prompt that was added
    call_args = mock_history.add_system_message.call_args[0]
    system_prompt = call_args[0]

    # Verify override is prepended to profile prompt
    assert override in system_prompt
    assert "You are a helpful AI assistant." in system_prompt
    assert system_prompt.index(override) < system_prompt.index(
        "You are a helpful AI assistant."
    )


@patch("consoul.cli.chat_session.get_chat_model")
@patch("consoul.cli.chat_session.ConversationHistory")
def test_system_prompt_override_without_profile_prompt(
    mock_history_class, mock_get_chat_model, mock_config, mock_chat_model
):
    """Test --system flag works when profile has no system prompt."""
    mock_get_chat_model.return_value = mock_chat_model
    mock_history = Mock()
    mock_history_class.return_value = mock_history

    # Remove profile system prompt
    profile = mock_config.get_active_profile()
    profile.system_prompt = None

    override = "You are a security expert."

    _ = ChatSession(mock_config, system_prompt_override=override)

    # Verify add_system_message was called
    assert mock_history.add_system_message.called

    # Get the system prompt
    call_args = mock_history.add_system_message.call_args[0]
    system_prompt = call_args[0]

    # Verify override becomes the system prompt
    assert override in system_prompt


@patch("consoul.cli.chat_session.get_chat_model")
@patch("consoul.cli.chat_session.ConversationHistory")
def test_no_system_prompt_override(
    mock_history_class, mock_get_chat_model, mock_config, mock_chat_model
):
    """Test normal behavior without --system flag."""
    mock_get_chat_model.return_value = mock_chat_model
    mock_history = Mock()
    mock_history_class.return_value = mock_history

    _ = ChatSession(mock_config)

    # Verify add_system_message was called with profile prompt only
    assert mock_history.add_system_message.called

    call_args = mock_history.add_system_message.call_args[0]
    system_prompt = call_args[0]

    # Should contain profile prompt
    assert "You are a helpful AI assistant." in system_prompt


@patch("consoul.cli.chat_session.get_chat_model")
@patch("consoul.cli.chat_session.ConversationHistory")
@patch("consoul.ai.environment.get_environment_context")
def test_system_prompt_with_environment_context(
    mock_env_context,
    mock_history_class,
    mock_get_chat_model,
    mock_config,
    mock_chat_model,
):
    """Test --system flag with environment context injection enabled."""
    mock_get_chat_model.return_value = mock_chat_model
    mock_history = Mock()
    mock_history_class.return_value = mock_history

    # Enable environment context
    profile = mock_config.get_active_profile()
    profile.context.include_system_info = True
    profile.context.include_git_info = True

    # Mock environment context
    mock_env_context.return_value = "# Environment\nOS: macOS\nShell: zsh"

    override = "You are a code reviewer."

    _ = ChatSession(mock_config, system_prompt_override=override)

    # Verify add_system_message was called
    assert mock_history.add_system_message.called

    call_args = mock_history.add_system_message.call_args[0]
    system_prompt = call_args[0]

    # Verify all parts are present
    assert "OS: macOS" in system_prompt
    assert override in system_prompt
    assert "You are a helpful AI assistant." in system_prompt


@patch("consoul.cli.chat_session.get_chat_model")
@patch("consoul.cli.chat_session.ConversationHistory")
def test_system_prompt_with_tools(
    mock_history_class, mock_get_chat_model, mock_config, mock_chat_model
):
    """Test --system flag with tool registry."""
    mock_get_chat_model.return_value = mock_chat_model
    mock_history = Mock()
    mock_history_class.return_value = mock_history

    # Create mock tool registry
    tool_registry = Mock()
    tool_registry.bind_to_model = Mock(return_value=mock_chat_model)
    tool_registry.__len__ = Mock(return_value=3)
    tool_registry.list_tools = Mock(return_value=[])  # No tools for simplicity

    override = "You are a Python expert."

    _ = ChatSession(
        mock_config,
        tool_registry=tool_registry,
        system_prompt_override=override,
    )

    # Verify add_system_message was called
    assert mock_history.add_system_message.called

    call_args = mock_history.add_system_message.call_args[0]
    system_prompt = call_args[0]

    # Verify override is present
    assert override in system_prompt


@patch("consoul.cli.chat_session.get_chat_model")
@patch("consoul.cli.chat_session.ConversationHistory")
def test_empty_system_prompt_override(
    mock_history_class, mock_get_chat_model, mock_config, mock_chat_model
):
    """Test empty string for --system flag is treated as no override."""
    mock_get_chat_model.return_value = mock_chat_model
    mock_history = Mock()
    mock_history_class.return_value = mock_history

    # Empty string override
    override = ""

    _ = ChatSession(mock_config, system_prompt_override=override)

    # Verify add_system_message was called
    assert mock_history.add_system_message.called

    call_args = mock_history.add_system_message.call_args[0]
    system_prompt = call_args[0]

    # Should only contain profile prompt (empty string is falsy)
    assert "You are a helpful AI assistant." in system_prompt


@patch("consoul.cli.chat_session.get_chat_model")
@patch("consoul.cli.chat_session.ConversationHistory")
def test_multiline_system_prompt_override(
    mock_history_class, mock_get_chat_model, mock_config, mock_chat_model
):
    """Test multi-line --system flag content."""
    mock_get_chat_model.return_value = mock_chat_model
    mock_history = Mock()
    mock_history_class.return_value = mock_history

    # Multi-line override
    override = """You are an expert programmer.
Focus on code quality and best practices.
Prioritize security and performance."""

    _ = ChatSession(mock_config, system_prompt_override=override)

    # Verify add_system_message was called
    assert mock_history.add_system_message.called

    call_args = mock_history.add_system_message.call_args[0]
    system_prompt = call_args[0]

    # Verify all lines are present
    assert "expert programmer" in system_prompt
    assert "code quality" in system_prompt
    assert "security and performance" in system_prompt
