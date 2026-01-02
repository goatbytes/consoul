"""Tests for CommandProcessor class."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from consoul.cli.command_processor import (
    CommandProcessor,
    cmd_clear,
    cmd_exit,
    cmd_export,
    cmd_help,
    cmd_model,
    cmd_stats,
    cmd_tokens,
    cmd_tools,
)


@pytest.fixture
def mock_session():
    """Create a mock ChatSession for testing."""
    session = Mock()
    session.console = Mock()
    session.config = Mock()
    session.config.core = Mock()
    session.config.core.current_provider = Mock(value="openai")
    session.config.core.current_model = "gpt-4o"
    session.conversation_service = Mock()
    session.conversation_service.conversation = Mock()
    session.conversation_service.conversation.model_name = "gpt-4o"
    session.conversation_service.conversation.session_id = "test-session-123"
    session.conversation_service.conversation.messages = []
    session.conversation_service.tool_registry = None
    session._should_exit = False

    # Mock methods
    session.clear_history = Mock()
    session.get_stats = Mock(return_value={"message_count": 10, "token_count": 1500})
    session.export_conversation = Mock()

    return session


class TestCommandProcessor:
    """Tests for CommandProcessor class."""

    def test_initialization(self, mock_session):
        """Test CommandProcessor initialization."""
        processor = CommandProcessor(mock_session)

        assert processor.session == mock_session
        assert len(processor.list_commands()) > 0
        assert "help" in processor.list_commands()
        assert "clear" in processor.list_commands()
        assert "tokens" in processor.list_commands()
        assert "exit" in processor.list_commands()
        assert "model" in processor.list_commands()
        assert "tools" in processor.list_commands()
        assert "export" in processor.list_commands()
        assert "stats" in processor.list_commands()

    def test_process_valid_command(self, mock_session):
        """Test processing a valid command."""
        processor = CommandProcessor(mock_session)

        # Should return True for commands
        assert processor.process("/help") is True
        assert processor.process("/clear") is True
        assert processor.process("/exit") is True

    def test_process_non_command(self, mock_session):
        """Test processing non-command input."""
        processor = CommandProcessor(mock_session)

        # Should return False for non-commands
        assert processor.process("regular message") is False
        assert processor.process("how are you?") is False

    def test_process_unknown_command(self, mock_session):
        """Test processing unknown command."""
        processor = CommandProcessor(mock_session)

        result = processor.process("/unknown")

        assert result is True  # Commands always return True
        mock_session.console.print.assert_called()
        # Check error message was printed
        call_args = str(mock_session.console.print.call_args)
        assert "Unknown command" in call_args

    def test_command_with_arguments(self, mock_session):
        """Test processing command with arguments."""
        processor = CommandProcessor(mock_session)

        processor.process("/model gpt-4o-mini")

        # Command should be processed (implementation tested separately)
        assert mock_session.console.print.called

    def test_command_aliases(self, mock_session):
        """Test command aliases work correctly."""
        processor = CommandProcessor(mock_session)

        # Test help alias
        processor.process("/?")
        assert mock_session.console.print.called

        mock_session.console.print.reset_mock()

        # Test exit alias
        processor.process("/quit")
        assert mock_session._should_exit is True

    def test_register_custom_command(self, mock_session):
        """Test registering a custom command."""
        processor = CommandProcessor(mock_session)

        # Create custom command
        custom_called = []

        def custom_cmd(session, args):
            custom_called.append(args)
            session.console.print(f"Custom: {args}")

        # Register command
        processor.register_command("custom", custom_cmd, aliases=["c"])

        # Test command
        processor.process("/custom test args")
        assert len(custom_called) == 1
        assert custom_called[0] == "test args"

        # Test alias
        processor.process("/c other args")
        assert len(custom_called) == 2
        assert custom_called[1] == "other args"

    def test_list_commands(self, mock_session):
        """Test listing all commands."""
        processor = CommandProcessor(mock_session)

        commands = processor.list_commands()

        assert isinstance(commands, list)
        assert len(commands) == 8  # 8 default commands
        assert commands == sorted(commands)  # Should be sorted


class TestCommandHelp:
    """Tests for cmd_help command."""

    def test_cmd_help(self, mock_session):
        """Test help command displays all commands."""
        cmd_help(mock_session, "")

        # Should print 3 times (blank line, table, blank line)
        assert mock_session.console.print.call_count == 3


class TestCommandClear:
    """Tests for cmd_clear command."""

    def test_cmd_clear(self, mock_session):
        """Test clear command."""
        cmd_clear(mock_session, "")

        mock_session.clear_history.assert_called_once()
        mock_session.console.print.assert_called_once()


class TestCommandTokens:
    """Tests for cmd_tokens command."""

    @patch("consoul.ai.context.get_model_token_limit")
    def test_cmd_tokens(self, mock_get_limit, mock_session):
        """Test tokens command."""
        mock_get_limit.return_value = 100000

        cmd_tokens(mock_session, "")

        mock_session.get_stats.assert_called_once()
        # Should print 3 times (2 blank lines + panel)
        assert mock_session.console.print.call_count == 3


class TestCommandExit:
    """Tests for cmd_exit command."""

    def test_cmd_exit(self, mock_session):
        """Test exit command sets flag."""
        assert mock_session._should_exit is False

        cmd_exit(mock_session, "")

        assert mock_session._should_exit is True
        mock_session.console.print.assert_called_once()


class TestCommandModel:
    """Tests for cmd_model command."""

    def test_cmd_model_no_args(self, mock_session):
        """Test model command without arguments."""
        cmd_model(mock_session, "")

        # Should print error message
        mock_session.console.print.assert_called_once()
        call_args = str(mock_session.console.print.call_args)
        assert "Error" in call_args
        assert "Model name required" in call_args

    @patch("consoul.ai.providers.get_chat_model")
    @patch("consoul.ai.providers.get_provider_from_model")
    def test_cmd_model_success(self, mock_get_provider, mock_get_model, mock_session):
        """Test successful model switch."""
        mock_get_provider.return_value = Mock(value="anthropic")
        mock_new_model = Mock()
        mock_get_model.return_value = mock_new_model

        cmd_model(mock_session, "claude-3-5-sonnet-20241022")

        # Should update config
        assert mock_session.config.core.current_model == "claude-3-5-sonnet-20241022"
        # Should update conversation service model
        assert mock_session.conversation_service.model == mock_new_model
        # Should print success message
        mock_session.console.print.assert_called_once()
        call_args = str(mock_session.console.print.call_args)
        assert "Switched to model" in call_args

    @patch("consoul.ai.providers.get_provider_from_model")
    def test_cmd_model_error(self, mock_get_provider, mock_session):
        """Test model switch with error."""
        mock_get_provider.side_effect = Exception("Model not found")

        cmd_model(mock_session, "invalid-model")

        # Should print error message
        mock_session.console.print.assert_called_once()
        call_args = str(mock_session.console.print.call_args)
        assert "Error" in call_args


class TestCommandTools:
    """Tests for cmd_tools command."""

    def test_cmd_tools_no_args(self, mock_session):
        """Test tools command without arguments shows status."""
        cmd_tools(mock_session, "")

        mock_session.console.print.assert_called_once()
        call_args = str(mock_session.console.print.call_args)
        assert "Tools:" in call_args

    @patch("consoul.ai.providers.get_chat_model")
    def test_cmd_tools_disable(self, mock_get_model, mock_session):
        """Test disabling tools."""
        # Setup - tools enabled
        mock_session.conversation_service.tool_registry = Mock()
        mock_session.conversation_service.tool_registry.__len__ = Mock(return_value=5)

        cmd_tools(mock_session, "off")

        # Should disable tools
        assert mock_session.conversation_service.tool_registry is None
        mock_session.console.print.assert_called_once()
        call_args = str(mock_session.console.print.call_args)
        assert "Tools disabled" in call_args

    def test_cmd_tools_enable_with_saved_registry(self, mock_session):
        """Test enabling tools with saved registry."""
        # Setup saved registry
        mock_registry = Mock()
        mock_registry.__len__ = Mock(return_value=3)
        mock_registry.bind_to_model = Mock(return_value=Mock())
        mock_session._saved_tool_registry = mock_registry

        cmd_tools(mock_session, "on")

        # Should restore registry
        assert mock_session.conversation_service.tool_registry == mock_registry
        mock_session.console.print.assert_called_once()
        call_args = str(mock_session.console.print.call_args)
        assert "Tools enabled" in call_args

    def test_cmd_tools_invalid_arg(self, mock_session):
        """Test tools command with invalid argument."""
        cmd_tools(mock_session, "invalid")

        mock_session.console.print.assert_called_once()
        call_args = str(mock_session.console.print.call_args)
        assert "Error" in call_args
        assert "Invalid argument" in call_args


class TestCommandExport:
    """Tests for cmd_export command."""

    def test_cmd_export_no_args(self, mock_session):
        """Test export command without arguments."""
        cmd_export(mock_session, "")

        mock_session.console.print.assert_called_once()
        call_args = str(mock_session.console.print.call_args)
        assert "Error" in call_args
        assert "Filename required" in call_args

    def test_cmd_export_success(self, mock_session):
        """Test successful export."""
        cmd_export(mock_session, "conversation.md")

        mock_session.export_conversation.assert_called_once_with("conversation.md")

    def test_cmd_export_error(self, mock_session):
        """Test export with error."""
        mock_session.export_conversation.side_effect = OSError("Cannot write file")

        cmd_export(mock_session, "conversation.md")

        mock_session.console.print.assert_called_once()
        call_args = str(mock_session.console.print.call_args)
        assert "Error" in call_args


class TestCommandStats:
    """Tests for cmd_stats command."""

    @patch("consoul.ai.context.get_model_token_limit")
    def test_cmd_stats(self, mock_get_limit, mock_session):
        """Test stats command."""
        mock_get_limit.return_value = 100000

        # Add some mock messages
        mock_msg1 = Mock()
        mock_msg1.type = "human"
        mock_msg2 = Mock()
        mock_msg2.type = "ai"
        mock_session.conversation_service.conversation.messages = [mock_msg1, mock_msg2]

        cmd_stats(mock_session, "")

        mock_session.get_stats.assert_called_once()
        # Should print 3 times (2 blank lines + panel)
        assert mock_session.console.print.call_count == 3


class TestIntegration:
    """Integration tests with ChatSession."""

    def test_commands_via_session(self, mock_session):
        """Test commands work through ChatSession integration."""
        processor = CommandProcessor(mock_session)

        # Test multiple commands in sequence
        assert processor.process("/help") is True
        assert processor.process("/clear") is True
        assert processor.process("/exit") is True

        # Verify expected side effects
        mock_session.clear_history.assert_called_once()
        assert mock_session._should_exit is True
