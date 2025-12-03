"""Tests for FileChip widget."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Label

from consoul.tui.widgets.file_chip import FileChip

# Mark all tests in this module as async
pytestmark = pytest.mark.asyncio


class FileChipTestApp(App[None]):
    """Test app for FileChip widget."""

    def __init__(self) -> None:
        """Initialize test app."""
        super().__init__()
        self.removed_files: list[str] = []

    def compose(self) -> ComposeResult:
        """Compose test app - widgets added dynamically in tests."""
        return []

    def on_file_chip_remove_requested(self, event: FileChip.RemoveRequested) -> None:
        """Handle RemoveRequested events."""
        self.removed_files.append(event.file_path)


class TestFileChipInitialization:
    """Test FileChip initialization and basic properties."""

    async def test_file_chip_mounts_with_image(self) -> None:
        """Test FileChip can be mounted with image file."""
        app = FileChipTestApp()
        async with app.run_test() as pilot:
            chip = FileChip("/path/to/image.png", "image")
            await app.mount(chip)
            await pilot.pause()

            assert chip.file_path == "/path/to/image.png"
            assert chip.file_type == "image"

    async def test_file_chip_mounts_with_code(self) -> None:
        """Test FileChip can be mounted with code file."""
        app = FileChipTestApp()
        async with app.run_test():
            chip = FileChip("/path/to/script.py", "code")
            await app.mount(chip)

            assert chip.file_path == "/path/to/script.py"
            assert chip.file_type == "code"

    async def test_file_chip_default_type(self) -> None:
        """Test FileChip defaults to unknown type."""
        app = FileChipTestApp()
        async with app.run_test():
            chip = FileChip("/path/to/file.xyz")
            await app.mount(chip)

            assert chip.file_type == "unknown"


class TestFileChipDisplay:
    """Test file chip display elements."""

    async def test_file_chip_shows_label(self) -> None:
        """Test FileChip displays label with filename."""
        app = FileChipTestApp()

        # Create a temporary file to get real size
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(b"test content")
            tmp_path = tmp.name

        try:
            async with app.run_test():
                chip = FileChip(tmp_path, "image")
                await app.mount(chip)

                # Query for label
                label = chip.query_one("#file-info", Label)
                assert label is not None
                assert Path(tmp_path).name in str(label.render())
        finally:
            Path(tmp_path).unlink()

    async def test_file_chip_shows_remove_button(self) -> None:
        """Test FileChip displays remove button."""
        app = FileChipTestApp()
        async with app.run_test():
            chip = FileChip("/path/to/file.png", "image")
            await app.mount(chip)

            # Query for remove button
            button = chip.query_one("#remove-chip", Button)
            assert button is not None
            assert button.label.plain == "x"
            assert button.variant == "error"

    async def test_file_chip_image_icon(self) -> None:
        """Test FileChip uses correct icon for images."""
        app = FileChipTestApp()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(b"test")
            tmp_path = tmp.name

        try:
            async with app.run_test():
                chip = FileChip(tmp_path, "image")
                await app.mount(chip)

                label = chip.query_one("#file-info", Label)
                assert "🖼️" in str(label.render())
        finally:
            Path(tmp_path).unlink()

    async def test_file_chip_code_icon(self) -> None:
        """Test FileChip uses correct icon for code files."""
        app = FileChipTestApp()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as tmp:
            tmp.write(b"test")
            tmp_path = tmp.name

        try:
            async with app.run_test():
                chip = FileChip(tmp_path, "code")
                await app.mount(chip)

                label = chip.query_one("#file-info", Label)
                assert "💾" in str(label.render())
        finally:
            Path(tmp_path).unlink()

    async def test_file_chip_document_icon(self) -> None:
        """Test FileChip uses correct icon for documents."""
        app = FileChipTestApp()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(b"test")
            tmp_path = tmp.name

        try:
            async with app.run_test():
                chip = FileChip(tmp_path, "document")
                await app.mount(chip)

                label = chip.query_one("#file-info", Label)
                assert "📄" in str(label.render())
        finally:
            Path(tmp_path).unlink()

    async def test_file_chip_data_icon(self) -> None:
        """Test FileChip uses correct icon for data files."""
        app = FileChipTestApp()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
            tmp.write(b"test")
            tmp_path = tmp.name

        try:
            async with app.run_test():
                chip = FileChip(tmp_path, "data")
                await app.mount(chip)

                label = chip.query_one("#file-info", Label)
                assert "📊" in str(label.render())
        finally:
            Path(tmp_path).unlink()

    async def test_file_chip_unknown_icon(self) -> None:
        """Test FileChip uses default icon for unknown types."""
        app = FileChipTestApp()
        async with app.run_test():
            chip = FileChip("/path/to/file.xyz", "unknown")
            await app.mount(chip)

            label = chip.query_one("#file-info", Label)
            assert "📎" in str(label.render())


class TestFileChipSizeFormatting:
    """Test file size formatting."""

    async def test_file_chip_shows_size_bytes(self) -> None:
        """Test FileChip shows size in bytes for small files."""
        app = FileChipTestApp()

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"x" * 100)  # 100 bytes
            tmp_path = tmp.name

        try:
            async with app.run_test():
                chip = FileChip(tmp_path, "unknown")
                await app.mount(chip)

                label = chip.query_one("#file-info", Label)
                label_text = str(label.render())
                assert "100B" in label_text or "0.1KB" in label_text
        finally:
            Path(tmp_path).unlink()

    async def test_file_chip_shows_size_kilobytes(self) -> None:
        """Test FileChip shows size in KB for medium files."""
        app = FileChipTestApp()

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"x" * 5000)  # ~5KB
            tmp_path = tmp.name

        try:
            async with app.run_test():
                chip = FileChip(tmp_path, "unknown")
                await app.mount(chip)

                label = chip.query_one("#file-info", Label)
                assert "KB" in str(label.render())
        finally:
            Path(tmp_path).unlink()

    async def test_file_chip_shows_size_megabytes(self) -> None:
        """Test FileChip shows size in MB for large files."""
        app = FileChipTestApp()

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(b"x" * (2 * 1024 * 1024))  # 2MB
            tmp_path = tmp.name

        try:
            async with app.run_test():
                chip = FileChip(tmp_path, "unknown")
                await app.mount(chip)

                label = chip.query_one("#file-info", Label)
                assert "MB" in str(label.render())
        finally:
            Path(tmp_path).unlink()

    async def test_file_chip_missing_file_no_size(self) -> None:
        """Test FileChip handles missing files gracefully."""
        app = FileChipTestApp()
        async with app.run_test():
            chip = FileChip("/nonexistent/file.png", "image")
            await app.mount(chip)

            # Should still show label, just without size
            label = chip.query_one("#file-info", Label)
            assert label is not None


class TestFileChipRemoval:
    """Test file chip removal functionality."""

    async def test_remove_button_posts_message(self) -> None:
        """Test clicking remove button posts RemoveRequested message."""
        app = FileChipTestApp()
        async with app.run_test() as pilot:
            chip = FileChip("/path/to/file.png", "image")
            await app.mount(chip)
            await pilot.pause()

            # Click remove button
            await pilot.click("#remove-chip")
            await pilot.pause()

            # Should post RemoveRequested message
            assert len(app.removed_files) == 1
            assert app.removed_files[0] == "/path/to/file.png"

    async def test_remove_button_removes_widget(self) -> None:
        """Test clicking remove button removes chip from DOM."""
        app = FileChipTestApp()
        async with app.run_test() as pilot:
            chip = FileChip("/path/to/file.png", "image")
            await app.mount(chip)
            await pilot.pause()

            # Verify chip is in DOM
            chips = app.query(FileChip)
            assert len(chips) == 1

            # Click remove button
            await pilot.click("#remove-chip")
            await pilot.pause()

            # Chip should be removed from DOM
            chips = app.query(FileChip)
            assert len(chips) == 0

    async def test_multiple_chips_removal(self) -> None:
        """Test removing multiple chips independently."""
        app = FileChipTestApp()
        async with app.run_test() as pilot:
            chip1 = FileChip("/path/to/file1.png", "image")
            chip2 = FileChip("/path/to/file2.py", "code")
            chip3 = FileChip("/path/to/file3.json", "data")

            await app.mount(chip1, chip2, chip3)
            await pilot.pause()

            # Remove second chip
            button2 = chip2.query_one("#remove-chip", Button)
            await pilot.click(button2)
            await pilot.pause()

            # Should have 2 chips remaining
            chips = app.query(FileChip)
            assert len(chips) == 2

            # Should have posted removal for chip2
            assert len(app.removed_files) == 1
            assert app.removed_files[0] == "/path/to/file2.py"


class TestFileChipEdgeCases:
    """Test edge cases and special scenarios."""

    async def test_file_chip_with_unicode_filename(self) -> None:
        """Test FileChip handles unicode filenames."""
        app = FileChipTestApp()

        with tempfile.NamedTemporaryFile(delete=False, suffix="文件.txt") as tmp:
            tmp.write(b"test")
            tmp_path = tmp.name

        try:
            async with app.run_test():
                chip = FileChip(tmp_path, "document")
                await app.mount(chip)

                label = chip.query_one("#file-info", Label)
                assert label is not None
        finally:
            Path(tmp_path).unlink()

    async def test_file_chip_with_spaces_in_filename(self) -> None:
        """Test FileChip handles filenames with spaces."""
        app = FileChipTestApp()

        with tempfile.NamedTemporaryFile(delete=False, suffix=" my file.txt") as tmp:
            tmp.write(b"test")
            tmp_path = tmp.name

        try:
            async with app.run_test():
                chip = FileChip(tmp_path, "document")
                await app.mount(chip)

                label = chip.query_one("#file-info", Label)
                assert label is not None
        finally:
            Path(tmp_path).unlink()

    async def test_file_chip_with_long_filename(self) -> None:
        """Test FileChip handles very long filenames."""
        app = FileChipTestApp()

        long_name = "a" * 200 + ".txt"
        with tempfile.NamedTemporaryFile(delete=False, suffix=long_name) as tmp:
            tmp.write(b"test")
            tmp_path = tmp.name

        try:
            async with app.run_test():
                chip = FileChip(tmp_path, "document")
                await app.mount(chip)

                label = chip.query_one("#file-info", Label)
                assert label is not None
        finally:
            Path(tmp_path).unlink()

    async def test_file_chip_all_file_types(self) -> None:
        """Test FileChip correctly handles all file type classifications."""
        app = FileChipTestApp()

        file_types = ["image", "code", "document", "data", "unknown"]

        async with app.run_test():
            for file_type in file_types:
                chip = FileChip(f"/path/to/file.{file_type}", file_type)
                await app.mount(chip)

                # Should mount without error
                assert chip.file_type == file_type


class TestFileChipMessages:
    """Test message structure and behavior."""

    async def test_remove_requested_message_structure(self) -> None:
        """Test RemoveRequested message has correct structure."""
        app = FileChipTestApp()
        async with app.run_test() as pilot:
            file_path = "/path/to/test.png"
            chip = FileChip(file_path, "image")
            await app.mount(chip)
            await pilot.pause()

            button = chip.query_one("#remove-chip", Button)
            await pilot.click(button)
            await pilot.pause()

            # Verify message content
            assert len(app.removed_files) == 1
            assert isinstance(app.removed_files[0], str)
            assert app.removed_files[0] == file_path

    async def test_multiple_removals_post_multiple_messages(self) -> None:
        """Test multiple removals each post separate messages."""
        app = FileChipTestApp()
        async with app.run_test() as pilot:
            chips = [
                FileChip("/file1.png", "image"),
                FileChip("/file2.py", "code"),
                FileChip("/file3.json", "data"),
            ]

            for chip in chips:
                await app.mount(chip)
            await pilot.pause()

            # Remove all chips
            for chip in chips:
                button = chip.query_one("#remove-chip", Button)
                await pilot.click(button)
                await pilot.pause()

            # Should have 3 removal messages
            assert len(app.removed_files) == 3
            assert app.removed_files == ["/file1.png", "/file2.py", "/file3.json"]
