"""Tests for ChatView widget."""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from consoul.tui.widgets.chat_view import ChatView
from consoul.tui.widgets.message_bubble import MessageBubble

# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio


class ChatViewTestApp(App[None]):
    """Test app for ChatView widget."""

    def compose(self) -> ComposeResult:
        """Compose test app with ChatView."""
        yield ChatView()


class TestChatViewInitialization:
    """Test ChatView initialization and basic properties."""

    async def test_chat_view_mounts(self) -> None:
        """Test ChatView can be mounted and has correct initial state."""
        app = ChatViewTestApp()
        async with app.run_test():
            chat_view = app.query_one(ChatView)
            assert chat_view.border_title == "Conversation"
            assert chat_view.message_count == 0
            assert chat_view.auto_scroll is True
            assert chat_view.can_focus is True

    async def test_chat_view_is_focusable(self) -> None:
        """Test that ChatView can receive focus."""
        app = ChatViewTestApp()
        async with app.run_test() as pilot:
            chat_view = app.query_one(ChatView)
            chat_view.focus()
            await pilot.pause()
            assert chat_view.has_focus


class TestChatViewMessageManagement:
    """Test adding and clearing messages."""

    async def test_add_single_message(self) -> None:
        """Test adding a single message to ChatView."""
        app = ChatViewTestApp()
        async with app.run_test() as pilot:
            chat_view = app.query_one(ChatView)
            message = MessageBubble("Test message", role="user")

            await chat_view.add_message(message)
            await pilot.pause()

            assert chat_view.message_count == 1
            assert chat_view.border_title == "Conversation (1 messages)"
            # Check if message widget is in children
            messages = list(chat_view.query(MessageBubble))
            assert len(messages) == 1

    async def test_add_multiple_messages(self) -> None:
        """Test adding multiple messages increments counter correctly."""
        app = ChatViewTestApp()
        async with app.run_test() as pilot:
            chat_view = app.query_one(ChatView)

            for i in range(5):
                await chat_view.add_message(MessageBubble(f"Message {i}", role="user"))
                await pilot.pause()

            assert chat_view.message_count == 5
            assert chat_view.border_title == "Conversation (5 messages)"
            messages = list(chat_view.query(MessageBubble))
            assert len(messages) == 5

    async def test_clear_messages(self) -> None:
        """Test clearing all messages resets state."""
        app = ChatViewTestApp()
        async with app.run_test() as pilot:
            chat_view = app.query_one(ChatView)

            # Add some messages
            for i in range(3):
                await chat_view.add_message(
                    MessageBubble(f"Message {i}", role="assistant")
                )
                await pilot.pause()

            assert chat_view.message_count == 3

            # Clear messages
            await chat_view.clear_messages()
            await pilot.pause()

            assert chat_view.message_count == 0
            assert chat_view.border_title == "Conversation"
            messages = list(chat_view.query(MessageBubble))
            assert len(messages) == 0

    async def test_clear_empty_chat_view(self) -> None:
        """Test clearing an already empty ChatView doesn't cause errors."""
        app = ChatViewTestApp()
        async with app.run_test() as pilot:
            chat_view = app.query_one(ChatView)

            await chat_view.clear_messages()
            await pilot.pause()

            assert chat_view.message_count == 0
            assert chat_view.border_title == "Conversation"


class TestChatViewBorderTitle:
    """Test border title updates based on message count."""

    async def test_border_title_updates_with_count(self) -> None:
        """Test border title updates as messages are added."""
        app = ChatViewTestApp()
        async with app.run_test() as pilot:
            chat_view = app.query_one(ChatView)

            # Initial state
            assert chat_view.border_title == "Conversation"

            # Add one message
            await chat_view.add_message(MessageBubble("First", role="user"))
            await pilot.pause()
            assert chat_view.border_title == "Conversation (1 messages)"

            # Add more messages
            await chat_view.add_message(MessageBubble("Second", role="assistant"))
            await pilot.pause()
            assert chat_view.border_title == "Conversation (2 messages)"

            # Clear
            await chat_view.clear_messages()
            await pilot.pause()
            assert chat_view.border_title == "Conversation"

    async def test_border_title_after_clearing(self) -> None:
        """Test border title resets after clearing messages."""
        app = ChatViewTestApp()
        async with app.run_test() as pilot:
            chat_view = app.query_one(ChatView)

            await chat_view.add_message(MessageBubble("Message", role="user"))
            await pilot.pause()
            title = chat_view.border_title
            assert title is not None and "messages" in title

            await chat_view.clear_messages()
            await pilot.pause()
            assert chat_view.border_title == "Conversation"


class TestChatViewAutoScroll:
    """Test auto-scroll behavior."""

    async def test_auto_scroll_enabled_by_default(self) -> None:
        """Test that auto_scroll is enabled by default."""
        app = ChatViewTestApp()
        async with app.run_test():
            chat_view = app.query_one(ChatView)
            assert chat_view.auto_scroll is True

    async def test_auto_scroll_can_be_disabled(self) -> None:
        """Test that auto_scroll can be disabled."""
        app = ChatViewTestApp()
        async with app.run_test() as pilot:
            chat_view = app.query_one(ChatView)
            chat_view.auto_scroll = False
            await pilot.pause()
            assert chat_view.auto_scroll is False

    async def test_adding_message_with_auto_scroll(self) -> None:
        """Test that adding message with auto_scroll enabled works."""
        app = ChatViewTestApp()
        async with app.run_test() as pilot:
            chat_view = app.query_one(ChatView)
            chat_view.auto_scroll = True

            # Add message - should not raise error
            await chat_view.add_message(MessageBubble("Message", role="user"))
            await pilot.pause()

            assert chat_view.message_count == 1

    async def test_adding_message_without_auto_scroll(self) -> None:
        """Test that adding message with auto_scroll disabled works."""
        app = ChatViewTestApp()
        async with app.run_test() as pilot:
            chat_view = app.query_one(ChatView)
            chat_view.auto_scroll = False

            # Add message - should not raise error
            await chat_view.add_message(MessageBubble("Message", role="assistant"))
            await pilot.pause()

            assert chat_view.message_count == 1


class TestChatViewReactiveProperties:
    """Test reactive property behavior."""

    async def test_message_count_reactive_updates(self) -> None:
        """Test that message_count reactive property updates correctly."""
        app = ChatViewTestApp()
        async with app.run_test() as pilot:
            chat_view = app.query_one(ChatView)

            # Check reactive updates
            initial_count = chat_view.message_count
            assert initial_count == 0

            # Add message - reactive should update
            await chat_view.add_message(MessageBubble("Test", role="user"))
            await pilot.pause()

            assert chat_view.message_count == 1
            assert chat_view.message_count != initial_count

    async def test_auto_scroll_reactive_updates(self) -> None:
        """Test that auto_scroll reactive property can be changed."""
        app = ChatViewTestApp()
        async with app.run_test() as pilot:
            chat_view = app.query_one(ChatView)

            # Toggle auto_scroll
            original_value = chat_view.auto_scroll
            chat_view.auto_scroll = not original_value
            await pilot.pause()

            assert chat_view.auto_scroll != original_value
