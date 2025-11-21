"""Tests for InputArea widget."""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from consoul.tui.widgets.input_area import InputArea

# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio


class InputAreaTestApp(App[None]):
    """Test app for InputArea widget."""

    def __init__(self) -> None:
        """Initialize test app."""
        super().__init__()
        self.messages: list[str] = []

    def compose(self) -> ComposeResult:
        """Compose test app with InputArea."""
        yield InputArea()

    def on_input_area_message_submit(self, event: InputArea.MessageSubmit) -> None:
        """Handle MessageSubmit events."""
        self.messages.append(event.content)


class TestInputAreaInitialization:
    """Test InputArea initialization and basic properties."""

    async def test_input_area_mounts(self) -> None:
        """Test InputArea can be mounted with default settings."""
        app = InputAreaTestApp()
        async with app.run_test():
            widget = app.query_one(InputArea)
            assert widget.character_count == 0
            assert "Enter to send" in widget.border_title
            assert widget.can_focus is True

    async def test_text_area_initialized(self) -> None:
        """Test that TextArea is properly initialized."""
        app = InputAreaTestApp()
        async with app.run_test():
            widget = app.query_one(InputArea)
            assert widget.text_area is not None
            assert widget.text_area.show_line_numbers is False

    async def test_text_area_focused_on_mount(self) -> None:
        """Test that TextArea receives focus on mount."""
        app = InputAreaTestApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            widget = app.query_one(InputArea)
            # TextArea should have focus
            assert widget.text_area.has_focus


class TestInputAreaCharacterCount:
    """Test character counting functionality."""

    async def test_character_count_updates(self) -> None:
        """Test that character count updates when text changes."""
        app = InputAreaTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one(InputArea)

            # Simulate typing
            widget.text_area.text = "Hello"
            widget.on_text_area_changed(widget.text_area.Changed(widget.text_area))
            await pilot.pause()

            assert widget.character_count == 5

    async def test_border_title_shows_character_count(self) -> None:
        """Test that border title updates with character count."""
        app = InputAreaTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one(InputArea)

            # Initially no count
            assert "Enter to send" in widget.border_title

            # Add text
            widget.text_area.text = "Test"
            widget.on_text_area_changed(widget.text_area.Changed(widget.text_area))
            await pilot.pause()

            assert "4 chars" in widget.border_title
            assert "Enter to send" in widget.border_title

    async def test_character_count_for_long_text(self) -> None:
        """Test character count with longer text."""
        app = InputAreaTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one(InputArea)

            long_text = "This is a longer message with multiple words."
            widget.text_area.text = long_text
            widget.on_text_area_changed(widget.text_area.Changed(widget.text_area))
            await pilot.pause()

            assert widget.character_count == len(long_text)
            assert f"{len(long_text)} chars" in widget.border_title

    async def test_character_count_with_multiline(self) -> None:
        """Test character count includes newlines."""
        app = InputAreaTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one(InputArea)

            multiline = "Line 1\nLine 2\nLine 3"
            widget.text_area.text = multiline
            widget.on_text_area_changed(widget.text_area.Changed(widget.text_area))
            await pilot.pause()

            assert widget.character_count == len(multiline)


class TestInputAreaMessageSending:
    """Test message sending functionality."""

    async def test_send_message_posts_event(self) -> None:
        """Test that sending a message posts MessageSubmit event."""
        app = InputAreaTestApp()

        async with app.run_test() as pilot:
            widget = app.query_one(InputArea)

            widget.text_area.text = "Test message"
            await widget._send_message()
            await pilot.pause()

            assert len(app.messages) == 1
            assert app.messages[0] == "Test message"

    async def test_send_message_clears_input(self) -> None:
        """Test that sending clears the input area."""
        app = InputAreaTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one(InputArea)

            widget.text_area.text = "Test message"
            await widget._send_message()
            await pilot.pause()

            assert widget.text_area.text == ""
            assert widget.character_count == 0

    async def test_empty_message_not_sent(self) -> None:
        """Test that empty messages are not sent."""
        app = InputAreaTestApp()

        async with app.run_test() as pilot:
            widget = app.query_one(InputArea)

            widget.text_area.text = ""
            await widget._send_message()
            await pilot.pause()

            assert len(app.messages) == 0

    async def test_whitespace_only_message_not_sent(self) -> None:
        """Test that whitespace-only messages are not sent."""
        app = InputAreaTestApp()

        async with app.run_test() as pilot:
            widget = app.query_one(InputArea)

            widget.text_area.text = "   \n\t  "
            await widget._send_message()
            await pilot.pause()

            assert len(app.messages) == 0

    async def test_message_trimmed_before_send(self) -> None:
        """Test that messages are trimmed of whitespace before sending."""
        app = InputAreaTestApp()

        async with app.run_test() as pilot:
            widget = app.query_one(InputArea)

            widget.text_area.text = "  Test message  \n"
            await widget._send_message()
            await pilot.pause()

            assert len(app.messages) == 1
            assert app.messages[0] == "Test message"

    async def test_multiline_message_sent_correctly(self) -> None:
        """Test that multiline messages are sent correctly."""
        app = InputAreaTestApp()

        async with app.run_test() as pilot:
            widget = app.query_one(InputArea)

            multiline = "Line 1\nLine 2\nLine 3"
            widget.text_area.text = multiline
            await widget._send_message()
            await pilot.pause()

            assert len(app.messages) == 1
            assert app.messages[0] == multiline


class TestInputAreaClearFunction:
    """Test clear functionality."""

    async def test_clear_resets_text(self) -> None:
        """Test that clear resets text content."""
        app = InputAreaTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one(InputArea)

            widget.text_area.text = "Some text"
            widget.clear()
            await pilot.pause()

            assert widget.text_area.text == ""

    async def test_clear_resets_character_count(self) -> None:
        """Test that clear resets character count."""
        app = InputAreaTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one(InputArea)

            widget.text_area.text = "Some text"
            widget.character_count = len("Some text")
            widget.clear()
            await pilot.pause()

            assert widget.character_count == 0

    async def test_clear_restores_focus(self) -> None:
        """Test that clear restores focus to TextArea."""
        app = InputAreaTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one(InputArea)

            widget.text_area.text = "Text"
            widget.clear()
            await pilot.pause()

            # Focus should be restored
            assert widget.text_area.has_focus


class TestInputAreaBorderTitle:
    """Test border title updates."""

    async def test_initial_border_title(self) -> None:
        """Test initial border title shows help text."""
        app = InputAreaTestApp()
        async with app.run_test():
            widget = app.query_one(InputArea)
            assert "Enter to send" in widget.border_title
            assert "Shift+Enter for newline" in widget.border_title

    async def test_border_title_with_text(self) -> None:
        """Test border title updates when text is present."""
        app = InputAreaTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one(InputArea)

            widget.text_area.text = "Hello"
            widget.on_text_area_changed(widget.text_area.Changed(widget.text_area))
            await pilot.pause()

            assert "5 chars" in widget.border_title
            assert "Enter to send" in widget.border_title

    async def test_border_title_after_clear(self) -> None:
        """Test border title resets after clear."""
        app = InputAreaTestApp()
        async with app.run_test() as pilot:
            widget = app.query_one(InputArea)

            widget.text_area.text = "Text"
            widget.on_text_area_changed(widget.text_area.Changed(widget.text_area))
            await pilot.pause()

            widget.clear()
            widget.on_text_area_changed(widget.text_area.Changed(widget.text_area))
            await pilot.pause()

            assert "Enter to send" in widget.border_title
            assert (
                "chars" not in widget.border_title or "0 chars" in widget.border_title
            )


class TestInputAreaEdgeCases:
    """Test edge cases and error handling."""

    async def test_unicode_characters(self) -> None:
        """Test handling of unicode characters."""
        app = InputAreaTestApp()

        async with app.run_test() as pilot:
            widget = app.query_one(InputArea)

            unicode_text = "Hello 世界 🌍 🚀"
            widget.text_area.text = unicode_text
            await widget._send_message()
            await pilot.pause()

            assert len(app.messages) == 1
            assert app.messages[0] == unicode_text

    async def test_very_long_message(self) -> None:
        """Test handling of very long messages."""
        app = InputAreaTestApp()

        async with app.run_test() as pilot:
            widget = app.query_one(InputArea)

            long_text = "Lorem ipsum " * 1000
            widget.text_area.text = long_text
            await widget._send_message()
            await pilot.pause()

            assert len(app.messages) == 1
            assert app.messages[0] == long_text.strip()

    async def test_special_characters(self) -> None:
        """Test handling of special characters."""
        app = InputAreaTestApp()

        async with app.run_test() as pilot:
            widget = app.query_one(InputArea)

            special = "Special: @#$%^&*()_+-=[]{}|;':\",./<>?`~"
            widget.text_area.text = special
            await widget._send_message()
            await pilot.pause()

            assert len(app.messages) == 1
            assert app.messages[0] == special

    async def test_multiple_sends(self) -> None:
        """Test sending multiple messages in succession."""
        app = InputAreaTestApp()

        async with app.run_test() as pilot:
            widget = app.query_one(InputArea)

            # Send first message
            widget.text_area.text = "First"
            await widget._send_message()
            await pilot.pause()

            # Send second message
            widget.text_area.text = "Second"
            await widget._send_message()
            await pilot.pause()

            # Send third message
            widget.text_area.text = "Third"
            await widget._send_message()
            await pilot.pause()

            assert len(app.messages) == 3
            assert app.messages == ["First", "Second", "Third"]

    async def test_border_title_updates_after_clear(self) -> None:
        """Test that border title resets after clear.

        Regression test: clear() must update border title back to default
        state, not leave stale character count visible.
        """
        app = InputAreaTestApp()

        async with app.run_test() as pilot:
            widget = app.query_one(InputArea)

            # Add text - border title should show count
            widget.text_area.text = "Test message"
            widget.on_text_area_changed(widget.text_area.Changed(widget.text_area))
            await pilot.pause()

            assert "12 chars" in widget.border_title

            # Clear - border title should reset
            widget.clear()
            await pilot.pause()

            assert "Enter to send" in widget.border_title
            assert "Shift+Enter for newline" in widget.border_title
            assert "chars" not in widget.border_title

    async def test_border_title_updates_after_send(self) -> None:
        """Test that border title resets after sending message.

        Regression test: Sending a message clears input, which should
        also reset the border title to default state.
        """
        app = InputAreaTestApp()

        async with app.run_test() as pilot:
            widget = app.query_one(InputArea)

            # Add text and trigger change event
            widget.text_area.text = "Test message"
            widget.on_text_area_changed(widget.text_area.Changed(widget.text_area))
            await pilot.pause()

            assert "12 chars" in widget.border_title

            # Send message (which calls clear internally)
            await widget._send_message()
            await pilot.pause()

            # Border title should be reset
            assert "Enter to send" in widget.border_title
            assert "Shift+Enter for newline" in widget.border_title
            assert "chars" not in widget.border_title


class TestInputAreaAttachments:
    """Test file attachment functionality."""

    async def test_attached_files_list_initialized(self) -> None:
        """Test attached_files list is initialized empty."""
        app = InputAreaTestApp()
        async with app.run_test():
            widget = app.query_one(InputArea)
            assert widget.attached_files == []

    async def test_file_classification_image(self) -> None:
        """Test _classify_file correctly identifies images."""
        app = InputAreaTestApp()
        async with app.run_test():
            widget = app.query_one(InputArea)

            assert widget._classify_file("/path/to/image.png") == "image"
            assert widget._classify_file("/path/to/photo.jpg") == "image"
            assert widget._classify_file("/path/to/pic.jpeg") == "image"
            assert widget._classify_file("/path/to/animation.gif") == "image"
            assert widget._classify_file("/path/to/web.webp") == "image"
            assert widget._classify_file("/path/to/bitmap.bmp") == "image"

    async def test_file_classification_code(self) -> None:
        """Test _classify_file correctly identifies code files."""
        app = InputAreaTestApp()
        async with app.run_test():
            widget = app.query_one(InputArea)

            assert widget._classify_file("/path/to/script.py") == "code"
            assert widget._classify_file("/path/to/app.js") == "code"
            assert widget._classify_file("/path/to/module.ts") == "code"
            assert widget._classify_file("/path/to/Component.jsx") == "code"
            assert widget._classify_file("/path/to/App.tsx") == "code"
            assert widget._classify_file("/path/to/main.rs") == "code"
            assert widget._classify_file("/path/to/server.go") == "code"
            assert widget._classify_file("/path/to/App.java") == "code"
            assert widget._classify_file("/path/to/program.cpp") == "code"
            assert widget._classify_file("/path/to/lib.c") == "code"
            assert widget._classify_file("/path/to/header.h") == "code"
            assert widget._classify_file("/path/to/template.hpp") == "code"

    async def test_file_classification_document(self) -> None:
        """Test _classify_file correctly identifies documents."""
        app = InputAreaTestApp()
        async with app.run_test():
            widget = app.query_one(InputArea)

            assert widget._classify_file("/path/to/doc.pdf") == "document"
            assert widget._classify_file("/path/to/README.md") == "document"
            assert widget._classify_file("/path/to/notes.txt") == "document"
            assert widget._classify_file("/path/to/docs.rst") == "document"
            assert widget._classify_file("/path/to/report.doc") == "document"
            assert widget._classify_file("/path/to/paper.docx") == "document"

    async def test_file_classification_data(self) -> None:
        """Test _classify_file correctly identifies data files."""
        app = InputAreaTestApp()
        async with app.run_test():
            widget = app.query_one(InputArea)

            assert widget._classify_file("/path/to/config.json") == "data"
            assert widget._classify_file("/path/to/settings.yaml") == "data"
            assert widget._classify_file("/path/to/data.yml") == "data"
            assert widget._classify_file("/path/to/spreadsheet.csv") == "data"
            assert widget._classify_file("/path/to/markup.xml") == "data"
            assert widget._classify_file("/path/to/pyproject.toml") == "data"

    async def test_file_classification_unknown(self) -> None:
        """Test _classify_file returns unknown for unrecognized extensions."""
        app = InputAreaTestApp()
        async with app.run_test():
            widget = app.query_one(InputArea)

            assert widget._classify_file("/path/to/file.xyz") == "unknown"
            assert widget._classify_file("/path/to/file.bin") == "unknown"
            assert widget._classify_file("/path/to/noext") == "unknown"

    async def test_file_classification_case_insensitive(self) -> None:
        """Test file classification is case-insensitive."""
        app = InputAreaTestApp()
        async with app.run_test():
            widget = app.query_one(InputArea)

            assert widget._classify_file("/path/to/IMAGE.PNG") == "image"
            assert widget._classify_file("/path/to/Script.PY") == "code"
            assert widget._classify_file("/path/to/Doc.PDF") == "document"
            assert widget._classify_file("/path/to/Config.JSON") == "data"

    async def test_compose_includes_attachment_button(self) -> None:
        """Test InputArea compose includes AttachmentButton."""
        from consoul.tui.widgets.attachment_button import AttachmentButton

        app = InputAreaTestApp()
        async with app.run_test():
            widget = app.query_one(InputArea)

            # Should have AttachmentButton
            buttons = widget.query(AttachmentButton)
            assert len(buttons) == 1

    async def test_compose_includes_file_chips_container(self) -> None:
        """Test InputArea compose includes file chips container."""
        app = InputAreaTestApp()
        async with app.run_test():
            widget = app.query_one(InputArea)

            # Should have file-chips-container
            container = widget.query_one("#file-chips-container")
            assert container is not None

    async def test_update_file_chips_adds_chips(self) -> None:
        """Test _update_file_chips adds FileChip widgets."""
        import tempfile
        from pathlib import Path

        from consoul.tui.widgets.file_chip import FileChip
        from consoul.tui.widgets.input_area import AttachedFile

        app = InputAreaTestApp()

        # Create temporary files
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp1:
            tmp1.write(b"test")
            tmp1_path = tmp1.name

        try:
            async with app.run_test() as pilot:
                widget = app.query_one(InputArea)

                # Add attached file
                widget.attached_files.append(
                    AttachedFile(
                        path=tmp1_path,
                        type="image",
                        mime_type="image/png",
                        size=4,
                    )
                )

                # Update chips
                widget._update_file_chips()
                await pilot.pause()

                # Should have one FileChip
                chips = widget.query(FileChip)
                assert len(chips) == 1
        finally:
            Path(tmp1_path).unlink()

    async def test_update_file_chips_clears_old_chips(self) -> None:
        """Test _update_file_chips clears old chips before adding new ones."""
        import tempfile
        from pathlib import Path

        from consoul.tui.widgets.file_chip import FileChip
        from consoul.tui.widgets.input_area import AttachedFile

        app = InputAreaTestApp()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(b"test")
            tmp_path = tmp.name

        try:
            async with app.run_test() as pilot:
                widget = app.query_one(InputArea)

                # Add first file
                widget.attached_files.append(
                    AttachedFile(
                        path=tmp_path,
                        type="image",
                        mime_type="image/png",
                        size=4,
                    )
                )
                widget._update_file_chips()
                await pilot.pause()

                # Clear files and update again
                widget.attached_files.clear()
                widget._update_file_chips()
                await pilot.pause()

                # Should have no chips
                chips = widget.query(FileChip)
                assert len(chips) == 0
        finally:
            Path(tmp_path).unlink()

    async def test_clear_removes_attached_files(self) -> None:
        """Test that clearing input does NOT automatically clear attached files.

        Note: attached_files are cleared separately in app.py after message submission.
        """
        import tempfile
        from pathlib import Path

        from consoul.tui.widgets.input_area import AttachedFile

        app = InputAreaTestApp()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(b"test")
            tmp_path = tmp.name

        try:
            async with app.run_test() as pilot:
                widget = app.query_one(InputArea)

                # Add attached file
                widget.attached_files.append(
                    AttachedFile(
                        path=tmp_path,
                        type="image",
                        mime_type="image/png",
                        size=4,
                    )
                )

                # Clear input
                widget.clear()
                await pilot.pause()

                # Attached files should remain (they're cleared by app.py)
                assert len(widget.attached_files) == 1
        finally:
            Path(tmp_path).unlink()
