"""Tests for ConsoulApp TUI application."""

from __future__ import annotations

import gc
from unittest.mock import Mock, patch

import pytest

from consoul.tui.app import ConsoulApp
from consoul.tui.config import TuiConfig
from consoul.tui.widgets import InputArea


class TestConsoulAppGarbageCollection:
    """Test GC management preserves library-first design."""

    def test_gc_state_restored_after_app_lifecycle(self) -> None:
        """Test that original GC state is restored after app unmount.

        This ensures library-first design: embedding apps don't lose GC
        when Consoul TUI exits.
        """
        # Record original GC state
        original_gc_enabled = gc.isenabled()

        try:
            # Test with GC originally enabled
            gc.enable()
            config = TuiConfig(gc_mode="streaming-aware")
            app = ConsoulApp(config=config, test_mode=True)
            assert app._original_gc_enabled is True

            # Simulate unmount (skip mount to avoid event loop requirement)
            app.on_unmount()
            # GC should be restored to enabled
            assert gc.isenabled() is True

            # Test with GC originally disabled
            gc.disable()
            app = ConsoulApp(config=config, test_mode=True)
            assert app._original_gc_enabled is False

            app.on_unmount()
            # GC should be restored to disabled
            assert gc.isenabled() is False

        finally:
            # Cleanup: restore original state
            if original_gc_enabled:
                gc.enable()
            else:
                gc.disable()

    def test_gc_mode_determines_behavior(self) -> None:
        """Test that GC mode configuration is respected."""
        # Just verify the config is stored correctly
        # Actual GC manipulation happens in on_mount() which requires event loop
        config = TuiConfig(gc_mode="streaming-aware")
        app = ConsoulApp(config=config, test_mode=True)
        assert app.config.gc_mode == "streaming-aware"

        config = TuiConfig(gc_mode="auto")
        app = ConsoulApp(config=config, test_mode=True)
        assert app.config.gc_mode == "auto"

    def test_gc_not_modified_when_auto_mode(self) -> None:
        """Test that GC is not modified in auto mode."""
        original_gc_enabled = gc.isenabled()

        try:
            config = TuiConfig(gc_mode="auto")
            app = ConsoulApp(config=config, test_mode=True)

            # In auto mode, GC state should not be modified
            # We can't call on_mount() without event loop, but we can verify
            # that the config is set correctly
            assert app.config.gc_mode == "auto"

            app.on_unmount()
            # GC should still be in original state
            assert gc.isenabled() == original_gc_enabled

        finally:
            if original_gc_enabled:
                gc.enable()

    def test_original_gc_state_stored_in_init(self) -> None:
        """Test that original GC state is captured in __init__."""
        # Enable GC
        gc.enable()
        app = ConsoulApp(test_mode=True)
        assert app._original_gc_enabled is True

        # Disable GC
        gc.disable()
        app = ConsoulApp(test_mode=True)
        assert app._original_gc_enabled is False

        # Restore
        gc.enable()


class TestConsoulAppInitialization:
    """Test ConsoulApp initialization."""

    def test_app_initialization_with_defaults(self) -> None:
        """Test app initializes with default config."""
        app = ConsoulApp(test_mode=True)
        assert app.title == "Consoul - AI Terminal Assistant"
        assert app.streaming is False
        assert app.conversation_id is None

    def test_app_initialization_with_custom_config(self) -> None:
        """Test app initializes with custom config."""
        config = TuiConfig(theme="dracula", gc_mode="manual")
        app = ConsoulApp(config=config, test_mode=True)
        assert app.config.theme == "dracula"
        assert app.config.gc_mode == "manual"

    def test_app_does_not_crash_with_invalid_theme(self) -> None:
        """Test that invalid theme doesn't crash during __init__.

        Previously, notify() was called from __init__ which would crash
        because message pump isn't running yet. Now theme validation
        happens in on_mount().
        """
        config = TuiConfig(theme="nonexistent-theme")
        # Should not raise RuntimeError
        app = ConsoulApp(config=config, test_mode=True)
        assert app.config.theme == "nonexistent-theme"

        # Notification should happen in on_mount (when message pump is running)
        # We can't easily test this without actually running the app,
        # but we verify that __init__ doesn't crash


class TestConsoulAppReactiveState:
    """Test reactive state management."""

    def test_reactive_state_initialization(self) -> None:
        """Test reactive state variables initialize correctly."""
        with patch("consoul.config.load_config", side_effect=Exception("No config")):
            app = ConsoulApp(test_mode=True)
            assert app.streaming is False
            assert app.conversation_id is None
            assert app.current_profile == "default"
            assert app.current_model == ""

    def test_streaming_state_can_be_changed(self) -> None:
        """Test that streaming reactive state can be modified."""
        app = ConsoulApp(test_mode=True)
        app.streaming = True
        assert app.streaming is True
        app.streaming = False
        assert app.streaming is False


class TestConsoulAppAIIntegration:
    """Test AI provider integration."""

    @pytest.mark.asyncio
    async def test_app_initializes_without_config(self) -> None:
        """Test app gracefully handles missing config."""
        with patch("consoul.config.load_config", side_effect=Exception("No config")):
            app = ConsoulApp(test_mode=True)
            assert app.chat_model is None
            assert app.conversation is None
            assert app.consoul_config is None

    @pytest.mark.asyncio
    async def test_app_initializes_with_mock_config(self) -> None:
        """Test app initializes AI components with valid config."""
        # Mock config
        mock_config = Mock()
        mock_profile = Mock()
        mock_profile.name = "test-profile"
        mock_profile.model.model = "gpt-4o"
        mock_profile.system_prompt = "You are helpful."
        mock_config.get_active_profile.return_value = mock_profile

        # Mock get_chat_model
        mock_chat_model = Mock()
        mock_conversation = Mock()
        mock_conversation.session_id = "test-session"

        with (
            patch("consoul.ai.get_chat_model", return_value=mock_chat_model),
            patch("consoul.ai.ConversationHistory", return_value=mock_conversation),
        ):
            app = ConsoulApp(consoul_config=mock_config, test_mode=True)

            assert app.chat_model is mock_chat_model
            assert app.conversation is mock_conversation
            assert app.current_profile == "test-profile"
            assert app.current_model == "gpt-4o"

    @pytest.mark.asyncio
    async def test_message_submit_without_ai_shows_error(self) -> None:
        """Test submitting message without AI model shows error."""
        app = ConsoulApp(test_mode=True)

        async with app.run_test() as pilot:
            # Ensure no AI model
            app.chat_model = None
            app.conversation = None

            # Post message submit event
            event = InputArea.MessageSubmit("Hello")
            await app.on_input_area_message_submit(event)
            await pilot.pause()

            # Should have added error message to chat
            messages = list(app.chat_view.query("MessageBubble"))
            assert len(messages) == 1
            assert "not initialized" in str(messages[0].content_text).lower()

    @pytest.mark.asyncio
    async def test_message_submit_with_ai_displays_user_message(self) -> None:
        """Test submitting message displays user bubble."""
        # Setup mock AI
        mock_chat_model = Mock()
        mock_conversation = Mock()
        mock_conversation.get_trimmed_messages.return_value = []

        # Mock streaming to return no tokens (prevent actual streaming)
        mock_chat_model.stream = Mock(return_value=iter([]))

        mock_config = Mock()
        mock_profile = Mock()
        mock_profile.name = "test"
        mock_profile.model.model = "gpt-4o"
        mock_profile.model.max_tokens = 4096
        mock_profile.system_prompt = None
        mock_config.get_active_profile.return_value = mock_profile

        with (
            patch("consoul.ai.get_chat_model", return_value=mock_chat_model),
            patch("consoul.ai.ConversationHistory", return_value=mock_conversation),
        ):
            app = ConsoulApp(consoul_config=mock_config, test_mode=True)

            async with app.run_test() as pilot:
                # Post message submit event
                event = InputArea.MessageSubmit("Hello AI")
                await app.on_input_area_message_submit(event)
                await pilot.pause()

                # Should have user message
                messages = list(app.chat_view.query("MessageBubble"))
                assert len(messages) >= 1
                # First message should be user message
                assert messages[0].role == "user"

    @pytest.mark.asyncio
    async def test_stream_cancellation(self) -> None:
        """Test cancelling stream sets flag."""
        app = ConsoulApp(test_mode=True)
        app.streaming = True
        app._current_stream = Mock()

        # Call action
        app.action_cancel_stream()

        assert app._stream_cancelled is True

    @pytest.mark.asyncio
    async def test_clear_conversation_with_ai(self) -> None:
        """Test clearing conversation clears view and history."""
        mock_conversation = Mock()
        app = ConsoulApp(test_mode=True)
        app.conversation = mock_conversation

        async with app.run_test() as pilot:
            # Add some mock messages
            from consoul.tui.widgets import MessageBubble

            await app.chat_view.add_message(
                MessageBubble("Test 1", role="user", show_metadata=False)
            )
            await app.chat_view.add_message(
                MessageBubble("Test 2", role="assistant", show_metadata=False)
            )
            await pilot.pause()

            # Clear conversation
            await app.action_clear_conversation()
            await pilot.pause()

            # Should have cleared view
            messages = list(app.chat_view.query("MessageBubble"))
            assert len(messages) == 0

            # Should have called conversation.clear()
            mock_conversation.clear.assert_called_once_with(preserve_system=True)

    @pytest.mark.asyncio
    async def test_new_conversation_creates_new_session(self) -> None:
        """Test new conversation action creates new session."""
        mock_chat_model = Mock()
        mock_old_conversation = Mock()
        mock_old_conversation.session_id = "old-session"

        mock_config = Mock()
        mock_profile = Mock()
        mock_profile.name = "test"
        mock_profile.model.model = "gpt-4o"
        mock_profile.system_prompt = None
        mock_config.get_active_profile.return_value = mock_profile

        with (
            patch("consoul.ai.get_chat_model", return_value=mock_chat_model),
            patch("consoul.ai.ConversationHistory", return_value=mock_old_conversation),
        ):
            app = ConsoulApp(consoul_config=mock_config, test_mode=True)

            async with app.run_test() as pilot:
                # Create new conversation
                mock_new_conversation = Mock()
                mock_new_conversation.session_id = "new-session"

                with patch(
                    "consoul.ai.ConversationHistory",
                    return_value=mock_new_conversation,
                ):
                    await app.action_new_conversation()
                    await pilot.pause()

                # Should have new conversation
                assert app.conversation is mock_new_conversation
                assert app.conversation_id == "new-session"
