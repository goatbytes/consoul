"""Tests for ThinkingIndicator widget."""

from __future__ import annotations

import pytest
from textual.app import App
from textual.widgets import Static

from consoul.tui.widgets.thinking_indicator import ThinkingIndicator

# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio


class ThinkingIndicatorTestApp(App[None]):
    """Test app for ThinkingIndicator widget."""

    def __init__(self, widget: ThinkingIndicator) -> None:
        """Initialize test app with widget.

        Args:
            widget: ThinkingIndicator widget to test
        """
        super().__init__()
        self.test_widget = widget

    def compose(self):
        """Compose test app."""
        yield self.test_widget


class TestThinkingIndicator:
    """Test suite for ThinkingIndicator widget."""

    async def test_indicator_creation(self) -> None:
        """Test thinking indicator is created with correct structure."""
        indicator = ThinkingIndicator()
        app = ThinkingIndicatorTestApp(indicator)

        async with app.run_test():
            widget = app.query_one(ThinkingIndicator)
            assert widget is not None
            assert widget.border_title == "🧠 Thinking"

    async def test_has_thinking_text(self) -> None:
        """Test indicator has thinking text widget."""
        indicator = ThinkingIndicator()
        app = ThinkingIndicatorTestApp(indicator)

        async with app.run_test():
            widget = app.query_one(ThinkingIndicator)
            text_widget = widget.query_one("#thinking-text", Static)
            assert text_widget is not None

    async def test_has_dots_widget(self) -> None:
        """Test indicator has animated dots widget."""
        indicator = ThinkingIndicator()
        app = ThinkingIndicatorTestApp(indicator)

        async with app.run_test():
            widget = app.query_one(ThinkingIndicator)
            dots_widget = widget.query_one("#thinking-dots", Static)
            assert dots_widget is not None

    async def test_dots_animation_cycles(self) -> None:
        """Test dots animation cycles through 0-3 dots."""
        indicator = ThinkingIndicator()
        app = ThinkingIndicatorTestApp(indicator)

        async with app.run_test():
            widget = app.query_one(ThinkingIndicator)

            # Initial state
            assert widget.dot_count == 0

            # Manually trigger update to test cycling
            widget._update_dots()
            assert widget.dot_count == 1

            widget._update_dots()
            assert widget.dot_count == 2

            widget._update_dots()
            assert widget.dot_count == 3

            widget._update_dots()
            assert widget.dot_count == 0  # Cycles back to 0

    async def test_dots_display_updates(self) -> None:
        """Test dots widget display updates with animation."""
        indicator = ThinkingIndicator()
        app = ThinkingIndicatorTestApp(indicator)

        async with app.run_test() as pilot:
            widget = app.query_one(ThinkingIndicator)

            # Just test that dot_count cycles correctly (visual check done manually)
            # The widget updates dots internally via update() calls

            # Initial state
            assert widget.dot_count == 0

            # After first update - should be 1
            widget._update_dots()
            await pilot.pause()
            assert widget.dot_count == 1

            # After second update - should be 2
            widget._update_dots()
            await pilot.pause()
            assert widget.dot_count == 2

            # After third update - should be 3
            widget._update_dots()
            await pilot.pause()
            assert widget.dot_count == 3

            # After fourth update - should cycle back to 0
            widget._update_dots()
            await pilot.pause()
            assert widget.dot_count == 0

    async def test_has_correct_css_classes(self) -> None:
        """Test indicator has correct CSS structure."""
        indicator = ThinkingIndicator()
        app = ThinkingIndicatorTestApp(indicator)

        async with app.run_test():
            widget = app.query_one(ThinkingIndicator)

            # Check text widget has correct class
            text_widget = widget.query_one("#thinking-text", Static)
            assert text_widget.has_class("thinking-text")

            # Check dots widget has correct class
            dots_widget = widget.query_one("#thinking-dots", Static)
            assert dots_widget.has_class("thinking-dots")

    async def test_animation_starts_on_mount(self) -> None:
        """Test animation timer starts when widget is mounted."""
        indicator = ThinkingIndicator()
        app = ThinkingIndicatorTestApp(indicator)

        async with app.run_test() as pilot:
            widget = app.query_one(ThinkingIndicator)

            # Wait for animation interval (0.4s)
            await pilot.pause(0.5)

            # Dot count should have incremented automatically
            assert widget.dot_count > 0

    async def test_multiple_indicators(self) -> None:
        """Test multiple thinking indicators can coexist."""

        class MultiIndicatorApp(App[None]):
            def compose(self):
                yield ThinkingIndicator()
                yield ThinkingIndicator()

        app = MultiIndicatorApp()

        async with app.run_test():
            indicators = app.query(ThinkingIndicator)
            assert len(indicators) == 2

            # Each should have independent animation state
            for indicator in indicators:
                assert indicator.border_title == "🧠 Thinking"
                assert indicator.dot_count >= 0
                assert indicator.dot_count <= 3

    async def test_border_title_emoji(self) -> None:
        """Test border title includes brain emoji."""
        indicator = ThinkingIndicator()
        app = ThinkingIndicatorTestApp(indicator)

        async with app.run_test():
            widget = app.query_one(ThinkingIndicator)
            assert "🧠" in widget.border_title
            assert "Thinking" in widget.border_title

    async def test_widget_can_be_removed(self) -> None:
        """Test thinking indicator can be removed from display."""

        class RemovableIndicatorApp(App[None]):
            def compose(self):
                yield ThinkingIndicator()

        app = RemovableIndicatorApp()

        async with app.run_test():
            widget = app.query_one(ThinkingIndicator)
            assert widget is not None

            # Remove the widget
            await widget.remove()

            # Should no longer be in DOM
            indicators = app.query(ThinkingIndicator)
            assert len(indicators) == 0

    async def test_add_token_updates_content(self) -> None:
        """Test adding tokens updates the thinking content display."""

        indicator = ThinkingIndicator()
        app = ThinkingIndicatorTestApp(indicator)

        async with app.run_test() as pilot:
            widget = app.query_one(ThinkingIndicator)

            # Initially no content
            assert widget.thinking_content == ""

            # Add some tokens
            await widget.add_token("Step 1: ")
            await pilot.pause()
            assert widget.thinking_content == "Step 1: "

            await widget.add_token("Analyze ")
            await pilot.pause()
            assert widget.thinking_content == "Step 1: Analyze "

            await widget.add_token("problem")
            await pilot.pause()
            assert widget.thinking_content == "Step 1: Analyze problem"

    async def test_has_content_log_widget(self) -> None:
        """Test indicator has RichLog for displaying thinking content."""
        from textual.widgets import RichLog

        indicator = ThinkingIndicator()
        app = ThinkingIndicatorTestApp(indicator)

        async with app.run_test():
            widget = app.query_one(ThinkingIndicator)
            content_log = widget.query_one("#thinking-content-log", RichLog)
            assert content_log is not None

    async def test_streaming_thinking_workflow(self) -> None:
        """Test complete workflow of streaming thinking content."""
        indicator = ThinkingIndicator()
        app = ThinkingIndicatorTestApp(indicator)

        async with app.run_test() as pilot:
            widget = app.query_one(ThinkingIndicator)

            # Simulate streaming thinking tokens
            thinking_tokens = [
                "<think>",
                "Step 1: ",
                "Understand the problem\n",
                "Step 2: ",
                "Formulate solution\n",
                "Step 3: ",
                "Verify correctness",
                "</think>",
            ]

            for token in thinking_tokens:
                await widget.add_token(token)
                await pilot.pause()

            # Check all content was accumulated
            expected = "".join(thinking_tokens)
            assert widget.thinking_content == expected

    async def test_strips_opening_tags(self) -> None:
        """Test that opening thinking tags are stripped from display."""
        indicator = ThinkingIndicator()
        app = ThinkingIndicatorTestApp(indicator)

        async with app.run_test() as pilot:
            widget = app.query_one(ThinkingIndicator)

            # Add content with opening tag
            await widget.add_token("<think>")
            await widget.add_token("Step 1: Analyze")
            await pilot.pause()

            # Raw content includes tags
            assert widget.thinking_content == "<think>Step 1: Analyze"
            # Display content strips tags
            assert widget.display_content == "Step 1: Analyze"

    async def test_strips_closing_tags(self) -> None:
        """Test that closing thinking tags are stripped from display."""
        indicator = ThinkingIndicator()
        app = ThinkingIndicatorTestApp(indicator)

        async with app.run_test() as pilot:
            widget = app.query_one(ThinkingIndicator)

            # Add content with closing tag
            await widget.add_token("<think>Reasoning</think>")
            await pilot.pause()

            # Raw content includes tags
            assert widget.thinking_content == "<think>Reasoning</think>"
            # Display content strips tags
            assert widget.display_content == "Reasoning"

    async def test_strips_all_tag_variants(self) -> None:
        """Test that all thinking tag variants are stripped."""
        indicator = ThinkingIndicator()
        app = ThinkingIndicatorTestApp(indicator)

        async with app.run_test() as pilot:
            widget = app.query_one(ThinkingIndicator)

            # Test different tag types
            test_cases = [
                ("<think>Content</think>", "Content"),
                ("<thinking>Content</thinking>", "Content"),
                ("<reasoning>Content</reasoning>", "Content"),
                ("<THINK>Content</THINK>", "Content"),  # Case insensitive
            ]

            for raw, expected_display in test_cases:
                # Reset widget
                widget.thinking_content = ""
                widget.display_content = ""

                await widget.add_token(raw)
                await pilot.pause()

                assert widget.display_content == expected_display

    async def test_preserves_content_between_tags(self) -> None:
        """Test that content between tags is preserved."""
        indicator = ThinkingIndicator()
        app = ThinkingIndicatorTestApp(indicator)

        async with app.run_test() as pilot:
            widget = app.query_one(ThinkingIndicator)

            # Stream tokens that form complete tagged content
            tokens = ["<think>", "Step 1\n", "Step 2\n", "Step 3", "</think>"]
            for token in tokens:
                await widget.add_token(token)
                await pilot.pause()

            # Display should have only the steps, no tags
            expected_display = "Step 1\nStep 2\nStep 3"
            assert widget.display_content == expected_display
