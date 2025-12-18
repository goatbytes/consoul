"""Tests for AttachmentButton widget."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from textual.app import App, ComposeResult

from consoul.tui.widgets.attachment_button import AttachmentButton

# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio


class AttachmentButtonTestApp(App[None]):
    """Test app for AttachmentButton widget."""

    def __init__(self) -> None:
        """Initialize test app."""
        super().__init__()
        self.attached_files: list[list[str]] = []

    def compose(self) -> ComposeResult:
        """Compose test app with AttachmentButton."""
        yield AttachmentButton()

    def on_attachment_button_attachment_selected(
        self, event: AttachmentButton.AttachmentSelected
    ) -> None:
        """Handle AttachmentSelected events."""
        self.attached_files.append(event.file_paths)


class TestAttachmentButtonInitialization:
    """Test AttachmentButton initialization and basic properties."""

    async def test_button_mounts(self) -> None:
        """Test AttachmentButton can be mounted with default settings."""
        app = AttachmentButtonTestApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            widget = app.query_one(AttachmentButton)
            assert widget.id == "attachment-button"
            assert widget.variant == AttachmentButton.DEFAULT_VARIANT

    async def test_button_label(self) -> None:
        """Test button displays attach label."""
        app = AttachmentButtonTestApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            widget = app.query_one(AttachmentButton)
            assert widget.label.plain == "+ Attach"


class TestAttachmentButtonFileSelection:
    """Test file selection functionality via modal."""

    async def test_button_opens_modal(self) -> None:
        """Test that clicking button opens FileAttachmentModal."""
        app = AttachmentButtonTestApp()

        async with app.run_test() as pilot:
            await pilot.pause()
            widget = app.query_one(AttachmentButton)

            # Mock _show_modal to return empty list
            with patch.object(
                widget, "_show_modal", new_callable=AsyncMock
            ) as mock_show_modal:
                mock_show_modal.return_value = None

                # Simulate button click
                await pilot.click(AttachmentButton)
                await pilot.pause()

                # Should have called _show_modal
                mock_show_modal.assert_called_once()

    async def test_modal_returns_files(self) -> None:
        """Test that files returned from modal post AttachmentSelected."""
        app = AttachmentButtonTestApp()

        async with app.run_test() as pilot:
            await pilot.pause()
            app.query_one(AttachmentButton)

            # Mock push_screen_wait to return file paths
            files = ["/path/to/file1.png", "/path/to/file2.py"]
            with patch.object(
                app, "push_screen_wait", new_callable=AsyncMock
            ) as mock_push:
                mock_push.return_value = files

                # Simulate button click
                await pilot.click(AttachmentButton)
                await pilot.pause()

                # Should post AttachmentSelected message
                assert len(app.attached_files) == 1
                assert app.attached_files[0] == files

    async def test_modal_cancellation(self) -> None:
        """Test handling when user cancels modal (returns empty list)."""
        app = AttachmentButtonTestApp()

        async with app.run_test() as pilot:
            await pilot.pause()
            app.query_one(AttachmentButton)

            # Mock push_screen_wait to return empty list (cancelled)
            with patch.object(
                app, "push_screen_wait", new_callable=AsyncMock
            ) as mock_push:
                mock_push.return_value = []

                # Simulate button click
                await pilot.click(AttachmentButton)
                await pilot.pause()

                # Should not post event when cancelled
                assert len(app.attached_files) == 0

    async def test_modal_single_file(self) -> None:
        """Test selecting a single file via modal."""
        app = AttachmentButtonTestApp()

        async with app.run_test() as pilot:
            await pilot.pause()
            app.query_one(AttachmentButton)

            # Mock push_screen_wait to return single file
            with patch.object(
                app, "push_screen_wait", new_callable=AsyncMock
            ) as mock_push:
                mock_push.return_value = ["/path/to/file.jpg"]

                # Simulate button click
                await pilot.click(AttachmentButton)
                await pilot.pause()

                assert len(app.attached_files) == 1
                assert app.attached_files[0] == ["/path/to/file.jpg"]

    async def test_modal_multiple_files(self) -> None:
        """Test selecting multiple files via modal."""
        app = AttachmentButtonTestApp()

        files = [
            "/path/to/image.png",
            "/path/to/code.py",
            "/path/to/doc.md",
            "/path/to/data.json",
        ]

        async with app.run_test() as pilot:
            await pilot.pause()
            app.query_one(AttachmentButton)

            # Mock push_screen_wait to return multiple files
            with patch.object(
                app, "push_screen_wait", new_callable=AsyncMock
            ) as mock_push:
                mock_push.return_value = files

                # Simulate button click
                await pilot.click(AttachmentButton)
                await pilot.pause()

                assert len(app.attached_files) == 1
                assert app.attached_files[0] == files


class TestAttachmentButtonMessages:
    """Test message posting behavior."""

    async def test_attachment_selected_message_structure(self) -> None:
        """Test AttachmentSelected message has correct structure."""
        app = AttachmentButtonTestApp()

        files = ["/path/to/file1.png", "/path/to/file2.py"]

        async with app.run_test() as pilot:
            await pilot.pause()
            app.query_one(AttachmentButton)

            with patch.object(
                app, "push_screen_wait", new_callable=AsyncMock
            ) as mock_push:
                mock_push.return_value = files

                # Simulate button click
                await pilot.click(AttachmentButton)
                await pilot.pause()

                # Verify message was received
                assert len(app.attached_files) == 1
                assert isinstance(app.attached_files[0], list)
                assert all(isinstance(p, str) for p in app.attached_files[0])


class TestAttachmentButtonEdgeCases:
    """Test edge cases and special scenarios."""

    async def test_modal_with_unicode_paths(self) -> None:
        """Test handling of file paths with unicode characters."""
        app = AttachmentButtonTestApp()

        unicode_files = ["/path/to/文件.png", "/path/to/файл.py", "/path/to/🚀.txt"]

        async with app.run_test() as pilot:
            await pilot.pause()
            app.query_one(AttachmentButton)

            with patch.object(
                app, "push_screen_wait", new_callable=AsyncMock
            ) as mock_push:
                mock_push.return_value = unicode_files

                # Simulate button click
                await pilot.click(AttachmentButton)
                await pilot.pause()

                assert len(app.attached_files) == 1
                assert app.attached_files[0] == unicode_files

    async def test_modal_with_spaces_in_paths(self) -> None:
        """Test handling of file paths with spaces."""
        app = AttachmentButtonTestApp()

        spaced_files = [
            "/path/to/my file.png",
            "/path/to/another file with spaces.py",
        ]

        async with app.run_test() as pilot:
            await pilot.pause()
            app.query_one(AttachmentButton)

            with patch.object(
                app, "push_screen_wait", new_callable=AsyncMock
            ) as mock_push:
                mock_push.return_value = spaced_files

                # Simulate button click
                await pilot.click(AttachmentButton)
                await pilot.pause()

                assert len(app.attached_files) == 1
                assert app.attached_files[0] == spaced_files
