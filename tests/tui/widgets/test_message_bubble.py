"""Tests for MessageBubble widget."""

from __future__ import annotations

from datetime import datetime

import pytest
from textual.app import App, ComposeResult

from consoul.tui.widgets.message_bubble import MessageBubble

# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio


class MessageBubbleTestApp(App[None]):
    """Test app for MessageBubble widget."""

    def __init__(self, bubble: MessageBubble) -> None:
        """Initialize test app with a MessageBubble.

        Args:
            bubble: MessageBubble widget to test
        """
        super().__init__()
        self.bubble = bubble

    def compose(self) -> ComposeResult:
        """Compose test app with MessageBubble."""
        yield self.bubble


class TestMessageBubbleInitialization:
    """Test MessageBubble initialization and basic properties."""

    async def test_message_bubble_mounts(self) -> None:
        """Test MessageBubble can be mounted with default settings."""
        bubble = MessageBubble("Test message")
        app = MessageBubbleTestApp(bubble)
        async with app.run_test():
            widget = app.query_one(MessageBubble)
            assert widget.content_text == "Test message"
            assert widget.role == "user"
            assert widget.border_title == "You"
            assert widget.has_class("message")
            assert widget.has_class("message-user")

    async def test_message_bubble_with_custom_timestamp(self) -> None:
        """Test MessageBubble with custom timestamp."""
        custom_time = datetime(2025, 1, 1, 12, 30, 45)
        bubble = MessageBubble("Test", timestamp=custom_time)
        app = MessageBubbleTestApp(bubble)
        async with app.run_test():
            widget = app.query_one(MessageBubble)
            assert widget.timestamp == custom_time

    async def test_message_bubble_with_token_count(self) -> None:
        """Test MessageBubble with token count."""
        bubble = MessageBubble("Test", token_count=42)
        app = MessageBubbleTestApp(bubble)
        async with app.run_test():
            widget = app.query_one(MessageBubble)
            assert widget.token_count == 42

    async def test_message_bubble_without_metadata(self) -> None:
        """Test MessageBubble with metadata disabled."""
        bubble = MessageBubble("Test", show_metadata=False)
        app = MessageBubbleTestApp(bubble)
        async with app.run_test():
            widget = app.query_one(MessageBubble)
            assert widget.show_metadata is False


class TestMessageBubbleRoles:
    """Test MessageBubble with different roles."""

    async def test_user_role(self) -> None:
        """Test MessageBubble with user role."""
        bubble = MessageBubble("User message", role="user")
        app = MessageBubbleTestApp(bubble)
        async with app.run_test():
            widget = app.query_one(MessageBubble)
            assert widget.role == "user"
            assert widget.border_title == "You"
            assert widget.has_class("message-user")

    async def test_assistant_role(self) -> None:
        """Test MessageBubble with assistant role."""
        bubble = MessageBubble("Assistant message", role="assistant")
        app = MessageBubbleTestApp(bubble)
        async with app.run_test():
            widget = app.query_one(MessageBubble)
            assert widget.role == "assistant"
            assert widget.border_title == "Assistant"
            assert widget.has_class("message-assistant")

    async def test_system_role(self) -> None:
        """Test MessageBubble with system role."""
        bubble = MessageBubble("System message", role="system")
        app = MessageBubbleTestApp(bubble)
        async with app.run_test():
            widget = app.query_one(MessageBubble)
            assert widget.role == "system"
            assert widget.border_title == "System"
            assert widget.has_class("message-system")

    async def test_error_role(self) -> None:
        """Test MessageBubble with error role."""
        bubble = MessageBubble("Error message", role="error")
        app = MessageBubbleTestApp(bubble)
        async with app.run_test():
            widget = app.query_one(MessageBubble)
            assert widget.role == "error"
            assert widget.border_title == "Error"
            assert widget.has_class("message-error")


class TestMessageBubbleMarkdown:
    """Test MessageBubble markdown rendering."""

    async def test_bold_text(self) -> None:
        """Test rendering bold markdown."""
        bubble = MessageBubble("**Bold text**")
        app = MessageBubbleTestApp(bubble)
        async with app.run_test():
            widget = app.query_one(MessageBubble)
            assert widget.content_text == "**Bold text**"

    async def test_italic_text(self) -> None:
        """Test rendering italic markdown."""
        bubble = MessageBubble("*Italic text*")
        app = MessageBubbleTestApp(bubble)
        async with app.run_test():
            widget = app.query_one(MessageBubble)
            assert widget.content_text == "*Italic text*"

    async def test_inline_code(self) -> None:
        """Test rendering inline code markdown."""
        bubble = MessageBubble("`inline code`")
        app = MessageBubbleTestApp(bubble)
        async with app.run_test():
            widget = app.query_one(MessageBubble)
            assert widget.content_text == "`inline code`"

    async def test_heading(self) -> None:
        """Test rendering heading markdown."""
        bubble = MessageBubble("# Heading")
        app = MessageBubbleTestApp(bubble)
        async with app.run_test():
            widget = app.query_one(MessageBubble)
            assert widget.content_text == "# Heading"

    async def test_list(self) -> None:
        """Test rendering list markdown."""
        bubble = MessageBubble("- List item 1\n- List item 2")
        app = MessageBubbleTestApp(bubble)
        async with app.run_test():
            widget = app.query_one(MessageBubble)
            assert "List item" in widget.content_text

    async def test_code_block(self) -> None:
        """Test rendering code block markdown."""
        bubble = MessageBubble("```python\nprint('hello')\n```")
        app = MessageBubbleTestApp(bubble)
        async with app.run_test():
            widget = app.query_one(MessageBubble)
            assert "python" in widget.content_text
            assert "print" in widget.content_text

    async def test_link(self) -> None:
        """Test rendering link markdown."""
        bubble = MessageBubble("[Link](https://example.com)")
        app = MessageBubbleTestApp(bubble)
        async with app.run_test():
            widget = app.query_one(MessageBubble)
            assert "Link" in widget.content_text

    async def test_quote(self) -> None:
        """Test rendering quote markdown."""
        bubble = MessageBubble("> This is a quote")
        app = MessageBubbleTestApp(bubble)
        async with app.run_test():
            widget = app.query_one(MessageBubble)
            assert "quote" in widget.content_text

    async def test_complex_markdown(self) -> None:
        """Test rendering complex markdown with multiple elements."""
        content = """# Title

**Bold** and *italic* text.

- List item 1
- List item 2

`inline code` and:

```python
def hello():
    print("world")
```

[Link](https://example.com)
"""
        bubble = MessageBubble(content)
        app = MessageBubbleTestApp(bubble)
        async with app.run_test():
            widget = app.query_one(MessageBubble)
            assert widget.content_text == content

    async def test_markdown_fallback(self) -> None:
        """Test that widget handles markdown rendering gracefully."""
        # Even if markdown fails internally, widget should work
        bubble = MessageBubble("Simple text")
        app = MessageBubbleTestApp(bubble)
        async with app.run_test():
            widget = app.query_one(MessageBubble)
            assert widget.content_text == "Simple text"


class TestMessageBubbleMetadata:
    """Test MessageBubble metadata display."""

    async def test_metadata_footer_with_timestamp(self) -> None:
        """Test metadata footer includes timestamp."""
        custom_time = datetime(2025, 1, 1, 14, 30, 45)
        bubble = MessageBubble("Test", timestamp=custom_time, show_metadata=True)
        app = MessageBubbleTestApp(bubble)
        async with app.run_test():
            widget = app.query_one(MessageBubble)
            footer = widget._build_metadata_footer()
            assert "14:30:45" in str(footer)
            assert "🕐" in str(footer)

    async def test_metadata_footer_with_token_count(self) -> None:
        """Test metadata footer includes token count."""
        bubble = MessageBubble("Test", token_count=100, show_metadata=True)
        app = MessageBubbleTestApp(bubble)
        async with app.run_test():
            widget = app.query_one(MessageBubble)
            footer = widget._build_metadata_footer()
            assert "100 tokens" in str(footer)
            assert "🎯" in str(footer)

    async def test_metadata_footer_with_both(self) -> None:
        """Test metadata footer with timestamp and token count."""
        custom_time = datetime(2025, 1, 1, 9, 15, 30)
        bubble = MessageBubble(
            "Test", timestamp=custom_time, token_count=42, show_metadata=True
        )
        app = MessageBubbleTestApp(bubble)
        async with app.run_test():
            widget = app.query_one(MessageBubble)
            footer = widget._build_metadata_footer()
            assert "09:15:30" in str(footer)
            assert "42 tokens" in str(footer)
            assert "│" in str(footer)

    async def test_metadata_disabled(self) -> None:
        """Test that metadata is not shown when disabled."""
        bubble = MessageBubble("Test", token_count=50, show_metadata=False)
        app = MessageBubbleTestApp(bubble)
        async with app.run_test():
            widget = app.query_one(MessageBubble)
            # When metadata is disabled, it shouldn't affect content
            assert widget.show_metadata is False


class TestMessageBubbleReactive:
    """Test MessageBubble reactive properties."""

    async def test_role_change(self) -> None:
        """Test changing role updates styling."""
        bubble = MessageBubble("Test", role="user")
        app = MessageBubbleTestApp(bubble)
        async with app.run_test() as pilot:
            widget = app.query_one(MessageBubble)

            # Initially user
            assert widget.role == "user"
            assert widget.has_class("message-user")
            assert widget.border_title == "You"

            # Change to assistant
            widget.role = "assistant"
            await pilot.pause()

            assert widget.has_class("message-assistant")
            assert not widget.has_class("message-user")
            assert widget.border_title == "Assistant"

    async def test_role_change_to_system(self) -> None:
        """Test changing role to system."""
        bubble = MessageBubble("Test", role="user")
        app = MessageBubbleTestApp(bubble)
        async with app.run_test() as pilot:
            widget = app.query_one(MessageBubble)

            widget.role = "system"
            await pilot.pause()

            assert widget.has_class("message-system")
            assert widget.border_title == "System"

    async def test_role_change_to_error(self) -> None:
        """Test changing role to error."""
        bubble = MessageBubble("Test", role="user")
        app = MessageBubbleTestApp(bubble)
        async with app.run_test() as pilot:
            widget = app.query_one(MessageBubble)

            widget.role = "error"
            await pilot.pause()

            assert widget.has_class("message-error")
            assert widget.border_title == "Error"

    async def test_multiple_role_changes(self) -> None:
        """Test multiple role changes update correctly."""
        bubble = MessageBubble("Test", role="user")
        app = MessageBubbleTestApp(bubble)
        async with app.run_test() as pilot:
            widget = app.query_one(MessageBubble)

            # user -> assistant -> system -> error
            roles = ["assistant", "system", "error", "user"]
            expected_classes = [
                "message-assistant",
                "message-system",
                "message-error",
                "message-user",
            ]
            expected_titles = ["Assistant", "System", "Error", "You"]

            for role, css_class, title in zip(
                roles, expected_classes, expected_titles, strict=True
            ):
                widget.role = role
                await pilot.pause()
                assert widget.has_class(css_class)
                assert widget.border_title == title


class TestMessageBubbleContentUpdate:
    """Test MessageBubble content updates."""

    async def test_update_content(self) -> None:
        """Test updating message content."""
        bubble = MessageBubble("Original message")
        app = MessageBubbleTestApp(bubble)
        async with app.run_test() as pilot:
            widget = app.query_one(MessageBubble)

            assert widget.content_text == "Original message"

            widget.update_content("Updated message")
            await pilot.pause()

            assert widget.content_text == "Updated message"

    async def test_update_content_with_markdown(self) -> None:
        """Test updating content with markdown."""
        bubble = MessageBubble("Plain text")
        app = MessageBubbleTestApp(bubble)
        async with app.run_test() as pilot:
            widget = app.query_one(MessageBubble)

            widget.update_content("**Bold markdown**")
            await pilot.pause()

            assert widget.content_text == "**Bold markdown**"

    async def test_update_content_resets_markdown_failed(self) -> None:
        """Test that updating content resets markdown failed flag."""
        bubble = MessageBubble("Test")
        app = MessageBubbleTestApp(bubble)
        async with app.run_test() as pilot:
            widget = app.query_one(MessageBubble)

            # Simulate markdown failure
            widget._markdown_failed = True

            widget.update_content("New content")
            await pilot.pause()

            # Should reset flag
            assert widget._markdown_failed is False


class TestMessageBubbleEdgeCases:
    """Test MessageBubble edge cases and error handling."""

    async def test_empty_content(self) -> None:
        """Test MessageBubble with empty content."""
        bubble = MessageBubble("")
        app = MessageBubbleTestApp(bubble)
        async with app.run_test():
            widget = app.query_one(MessageBubble)
            assert widget.content_text == ""

    async def test_very_long_content(self) -> None:
        """Test MessageBubble with very long content."""
        long_content = "Lorem ipsum " * 1000
        bubble = MessageBubble(long_content)
        app = MessageBubbleTestApp(bubble)
        async with app.run_test():
            widget = app.query_one(MessageBubble)
            assert len(widget.content_text) > 10000

    async def test_special_characters(self) -> None:
        """Test MessageBubble with special characters."""
        special = "Special: @#$%^&*()_+-=[]{}|;':\",./<>?`~"
        bubble = MessageBubble(special)
        app = MessageBubbleTestApp(bubble)
        async with app.run_test():
            widget = app.query_one(MessageBubble)
            assert widget.content_text == special

    async def test_unicode_content(self) -> None:
        """Test MessageBubble with unicode characters."""
        unicode_text = "Hello 世界 🌍 🚀 ✨"
        bubble = MessageBubble(unicode_text)
        app = MessageBubbleTestApp(bubble)
        async with app.run_test():
            widget = app.query_one(MessageBubble)
            assert widget.content_text == unicode_text

    async def test_multiline_content(self) -> None:
        """Test MessageBubble with multiline content."""
        multiline = "Line 1\nLine 2\nLine 3"
        bubble = MessageBubble(multiline)
        app = MessageBubbleTestApp(bubble)
        async with app.run_test():
            widget = app.query_one(MessageBubble)
            assert widget.content_text == multiline

    async def test_none_token_count(self) -> None:
        """Test MessageBubble with None token count."""
        bubble = MessageBubble("Test", token_count=None)
        app = MessageBubbleTestApp(bubble)
        async with app.run_test():
            widget = app.query_one(MessageBubble)
            footer = widget._build_metadata_footer()
            # Should not include token count
            assert "tokens" not in str(footer)

    async def test_zero_token_count(self) -> None:
        """Test MessageBubble with zero token count."""
        bubble = MessageBubble("Test", token_count=0)
        app = MessageBubbleTestApp(bubble)
        async with app.run_test():
            widget = app.query_one(MessageBubble)
            footer = widget._build_metadata_footer()
            assert "0 tokens" in str(footer)
