"""Tests for image path detection and validation utilities."""

from pathlib import Path

import pytest

from consoul.tui.utils.image_parser import (
    extract_image_paths,
    format_message_with_indicators,
    validate_image_path,
)


@pytest.fixture
def test_image_png(tmp_path):
    """Create a test PNG image file."""
    img = tmp_path / "screenshot.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)  # Minimal PNG
    return img


@pytest.fixture
def test_image_jpg(tmp_path):
    """Create a test JPEG image file."""
    img = tmp_path / "photo.jpg"
    # Minimal JPEG header
    img.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
    return img


@pytest.fixture
def test_directory(tmp_path):
    """Create a test directory."""
    directory = tmp_path / "test_dir"
    directory.mkdir()
    return directory


class TestExtractImagePaths:
    """Tests for extract_image_paths function."""

    def test_extract_single_image(self, test_image_png):
        """Test extracting a single image reference."""
        message = f"What's in {test_image_png}?"
        original, paths = extract_image_paths(message)

        assert original == message  # Message unchanged
        assert len(paths) == 1
        assert paths[0] == str(test_image_png)

    def test_extract_multiple_images(self, test_image_png, test_image_jpg):
        """Test extracting multiple image references."""
        message = f"Compare {test_image_png} and {test_image_jpg}"
        original, paths = extract_image_paths(message)

        assert original == message
        assert len(paths) == 2
        assert str(test_image_png) in paths
        assert str(test_image_jpg) in paths

    def test_no_images_in_message(self):
        """Test message with no image references."""
        message = "Hello, how are you?"
        original, paths = extract_image_paths(message)

        assert original == message
        assert len(paths) == 0

    def test_extract_with_brackets(self, test_image_png):
        """Test extracting image in brackets."""
        message = f"Analyze [{test_image_png}] please"
        original, paths = extract_image_paths(message)

        assert original == message
        assert len(paths) == 1
        assert paths[0] == str(test_image_png)

    def test_extract_with_quotes(self, test_image_png):
        """Test extracting quoted image path."""
        message = f'Check "{test_image_png}" for errors'
        original, paths = extract_image_paths(message)

        assert original == message
        assert len(paths) == 1
        assert paths[0] == str(test_image_png)

    def test_case_insensitive_extensions(self, tmp_path):
        """Test that extension matching is case-insensitive."""
        img_upper = tmp_path / "Test.PNG"
        img_upper.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        message = f"View {img_upper}"
        _original, paths = extract_image_paths(message)

        assert len(paths) == 1
        assert paths[0] == str(img_upper)

    def test_nonexistent_file_excluded(self):
        """Test that non-existent files are excluded."""
        message = "Check missing.png and nonexistent.jpg"
        original, paths = extract_image_paths(message)

        assert original == message
        assert len(paths) == 0  # Both files don't exist

    def test_directory_path_excluded(self, test_directory):
        """Test that directory paths are excluded."""
        message = f"Look in {test_directory}"
        original, paths = extract_image_paths(message)

        assert original == message
        assert len(paths) == 0  # Directory, not file

    def test_invalid_extension_excluded(self, tmp_path):
        """Test that files with invalid extensions are excluded."""
        exe_file = tmp_path / "malware.exe"
        exe_file.write_bytes(b"fake")

        message = f"Run {exe_file}"
        original, paths = extract_image_paths(message)

        assert original == message
        assert len(paths) == 0  # .exe not a valid image extension

    def test_relative_path_resolution(self, test_image_png):
        """Test that relative paths are resolved to absolute."""
        # Change to temp directory
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(test_image_png.parent)
            message = f"Analyze {test_image_png.name}"
            _original, paths = extract_image_paths(message)

            assert len(paths) == 1
            assert paths[0] == str(test_image_png)  # Absolute path
            assert Path(paths[0]).is_absolute()
        finally:
            os.chdir(original_cwd)

    def test_duplicate_paths_deduplicated(self, test_image_png):
        """Test that duplicate image paths are deduplicated."""
        message = f"Compare {test_image_png} with {test_image_png}"
        original, paths = extract_image_paths(message)

        assert original == message
        assert len(paths) == 1  # Deduplicated
        assert paths[0] == str(test_image_png)

    def test_image_at_end_of_sentence(self, test_image_png):
        """Test extracting image path at end of sentence."""
        message = f"See error in {test_image_png}."
        original, paths = extract_image_paths(message)

        assert original == message
        assert len(paths) == 1
        assert paths[0] == str(test_image_png)

    def test_all_supported_extensions(self, tmp_path):
        """Test all supported image extensions are detected."""
        extensions = ["png", "jpg", "jpeg", "gif", "webp", "bmp"]
        images = []

        for ext in extensions:
            img = tmp_path / f"test.{ext}"
            img.write_bytes(b"\x00" * 100)  # Dummy content
            images.append(img)

        message = " ".join(str(img) for img in images)
        _original, paths = extract_image_paths(message)

        assert len(paths) == len(extensions)


class TestValidateImagePath:
    """Tests for validate_image_path function."""

    def test_validate_existing_file(self, test_image_png):
        """Test validating an existing image file."""
        is_valid, error = validate_image_path(str(test_image_png))

        assert is_valid is True
        assert error == ""

    def test_validate_nonexistent_file(self):
        """Test validating a non-existent file."""
        is_valid, error = validate_image_path("/nonexistent/missing.png")

        assert is_valid is False
        assert "File not found" in error

    def test_validate_directory_path(self, test_directory):
        """Test validating a directory path."""
        is_valid, error = validate_image_path(str(test_directory))

        assert is_valid is False
        assert "directory" in error.lower()

    def test_validate_invalid_extension(self, tmp_path):
        """Test validating a file with invalid extension."""
        text_file = tmp_path / "document.txt"
        text_file.write_text("Hello")

        is_valid, error = validate_image_path(str(text_file))

        assert is_valid is False
        assert "Invalid image extension" in error

    def test_validate_relative_path(self, test_image_png):
        """Test validating a relative path."""
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(test_image_png.parent)
            is_valid, error = validate_image_path(test_image_png.name)

            assert is_valid is True
            assert error == ""
        finally:
            os.chdir(original_cwd)

    def test_validate_with_tilde_expansion(self):
        """Test validating path with ~ expansion works."""
        # Test that tilde expansion doesn't crash
        # This will fail validation (file doesn't exist) but shouldn't error on expansion
        is_valid, error = validate_image_path("~/nonexistent.png")

        assert is_valid is False
        # Should be "File not found", not "Invalid path" (which would indicate expansion failed)
        assert "File not found" in error

    def test_validate_invalid_path_characters(self):
        """Test validating path with invalid characters."""
        is_valid, error = validate_image_path("/invalid\x00/path.png")

        assert is_valid is False
        assert "Invalid path" in error


class TestFormatMessageWithIndicators:
    """Tests for format_message_with_indicators function."""

    def test_format_single_image(self):
        """Test formatting message with one image."""
        message = "What's in /path/to/screenshot.png?"
        paths = ["/path/to/screenshot.png"]
        result = format_message_with_indicators(message, paths)

        assert "🖼️ [screenshot.png]" in result
        assert "/path/to/screenshot.png" not in result

    def test_format_multiple_images(self):
        """Test formatting message with multiple images."""
        message = "Compare /path/img1.png and /path/img2.jpg"
        paths = ["/path/img1.png", "/path/img2.jpg"]
        result = format_message_with_indicators(message, paths)

        assert "🖼️ [img1.png]" in result
        assert "🖼️ [img2.jpg]" in result
        assert "/path/img1.png" not in result
        assert "/path/img2.jpg" not in result

    def test_format_no_images(self):
        """Test formatting message with no images."""
        message = "Hello world"
        paths = []
        result = format_message_with_indicators(message, paths)

        assert result == message  # Unchanged

    def test_format_preserves_message_structure(self):
        """Test that formatting preserves message structure."""
        message = "Check screenshot.png for the error"
        paths = ["/absolute/path/to/screenshot.png"]
        result = format_message_with_indicators(message, paths)

        # Should preserve "for the error" part
        assert "for the error" in result
        assert "🖼️ [screenshot.png]" in result
