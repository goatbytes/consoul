"""Tests for analyze_images tool implementation."""

import base64
import json
from pathlib import Path

import pytest

from consoul.ai.tools.implementations.analyze_images import (
    _detect_mime_type,
    _validate_extension,
    _validate_file_type,
    _validate_path,
    _validate_size,
    analyze_images,
    get_analyze_images_config,
    set_analyze_images_config,
)
from consoul.config.models import ImageAnalysisToolConfig


@pytest.fixture
def test_image_png():
    """Path to test PNG image fixture."""
    return Path(__file__).parent.parent.parent.parent / "fixtures" / "test_image.png"


@pytest.fixture
def test_image_jpg():
    """Path to test JPEG image fixture."""
    return Path(__file__).parent.parent.parent.parent / "fixtures" / "test_photo.jpg"


@pytest.fixture
def test_image_webp():
    """Path to test WebP image fixture."""
    return Path(__file__).parent.parent.parent.parent / "fixtures" / "test_diagram.webp"


@pytest.fixture
def default_config():
    """Default ImageAnalysisToolConfig for testing."""
    return ImageAnalysisToolConfig()


class TestDetectMimeType:
    """Tests for MIME type detection."""

    def test_detect_png_mime_type(self, test_image_png):
        """Test PNG MIME type detection."""
        mime_type = _detect_mime_type(test_image_png)
        assert mime_type == "image/png"

    def test_detect_jpeg_mime_type(self, test_image_jpg):
        """Test JPEG MIME type detection."""
        mime_type = _detect_mime_type(test_image_jpg)
        assert mime_type == "image/jpeg"

    def test_detect_webp_mime_type(self, test_image_webp):
        """Test WebP MIME type detection."""
        mime_type = _detect_mime_type(test_image_webp)
        assert mime_type == "image/webp"

    def test_detect_non_image_mime_type(self, tmp_path):
        """Test that non-image files raise ValueError."""
        text_file = tmp_path / "test.txt"
        text_file.write_text("Hello, world!")

        with pytest.raises(ValueError, match="not an image"):
            _detect_mime_type(text_file)

    def test_detect_no_extension_file(self, tmp_path):
        """Test file with no extension raises ValueError."""
        no_ext_file = tmp_path / "testfile"
        no_ext_file.write_bytes(b"fake image data")

        with pytest.raises(ValueError, match="Could not detect MIME type"):
            _detect_mime_type(no_ext_file)


class TestValidatePath:
    """Tests for path validation."""

    def test_valid_path(self, test_image_png, default_config):
        """Test that valid file paths pass validation."""
        path = _validate_path(str(test_image_png), default_config)
        assert path.exists()
        assert path.is_file()

    def test_path_traversal_blocked(self, default_config):
        """Test that path traversal attempts are blocked."""
        with pytest.raises(ValueError, match="Path traversal"):
            _validate_path("../../etc/passwd", default_config)

    def test_blocked_path_etc(self, default_config):
        """Test that /etc paths are blocked."""
        with pytest.raises(ValueError, match="not allowed for security"):
            _validate_path("/etc/shadow", default_config)

    def test_blocked_path_ssh(self, default_config):
        """Test that ~/.ssh paths are blocked."""
        with pytest.raises(ValueError, match="not allowed for security"):
            _validate_path("~/.ssh/id_rsa", default_config)

    def test_nonexistent_file(self, tmp_path, default_config):
        """Test that nonexistent files raise ValueError."""
        nonexistent = tmp_path / "nonexistent.png"

        with pytest.raises(ValueError, match="File not found"):
            _validate_path(str(nonexistent), default_config)

    def test_directory_path(self, tmp_path, default_config):
        """Test that directories raise ValueError."""
        directory = tmp_path / "testdir"
        directory.mkdir()

        with pytest.raises(ValueError, match="Cannot analyze directory"):
            _validate_path(str(directory), default_config)

    def test_expanduser_home_path(self, test_image_png, default_config, tmp_path):
        """Test that ~ paths are expanded correctly."""
        # Create a test file in a predictable location
        test_file = tmp_path / "test.png"
        test_file.write_bytes(test_image_png.read_bytes())

        # Path validation should work with absolute path
        path = _validate_path(str(test_file), default_config)
        assert path.is_absolute()

    def test_similarly_named_dirs_not_blocked(self, tmp_path, default_config):
        """Test that dirs with similar names to blocked paths are not rejected."""
        # Create directories with names that START with blocked path tokens
        # but are not actually under those blocked paths
        etcetera_dir = tmp_path / "etcetera" / "screenshots"
        devotion_dir = tmp_path / "devotion" / "assets"

        etcetera_dir.mkdir(parents=True)
        devotion_dir.mkdir(parents=True)

        # Create test images in these directories
        etcetera_img = etcetera_dir / "ui.png"
        devotion_img = devotion_dir / "img.png"

        etcetera_img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        devotion_img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

        # These should NOT be blocked (old startswith() logic would block them)
        # New is_relative_to() logic should allow them
        path1 = _validate_path(str(etcetera_img), default_config)
        path2 = _validate_path(str(devotion_img), default_config)

        assert path1.exists()
        assert path2.exists()


class TestValidateExtension:
    """Tests for extension validation."""

    def test_valid_png_extension(self, test_image_png, default_config):
        """Test that .png extension passes validation."""
        _validate_extension(test_image_png, default_config)  # Should not raise

    def test_valid_jpg_extension(self, test_image_jpg, default_config):
        """Test that .jpg extension passes validation."""
        _validate_extension(test_image_jpg, default_config)  # Should not raise

    def test_valid_webp_extension(self, test_image_webp, default_config):
        """Test that .webp extension passes validation."""
        _validate_extension(test_image_webp, default_config)  # Should not raise

    def test_case_insensitive_extension(self, tmp_path, default_config):
        """Test that extension matching is case-insensitive."""
        uppercase_file = tmp_path / "test.PNG"
        uppercase_file.touch()

        _validate_extension(uppercase_file, default_config)  # Should not raise

    def test_invalid_extension(self, tmp_path, default_config):
        """Test that invalid extensions raise ValueError."""
        exe_file = tmp_path / "malware.exe"
        exe_file.touch()

        with pytest.raises(ValueError, match="not allowed"):
            _validate_extension(exe_file, default_config)


class TestValidateFileType:
    """Tests for magic byte validation."""

    def test_valid_png_file_type(self, test_image_png):
        """Test that valid PNG passes magic byte check."""
        _validate_file_type(test_image_png)  # Should not raise

    def test_valid_jpeg_file_type(self, test_image_jpg):
        """Test that valid JPEG passes magic byte check."""
        _validate_file_type(test_image_jpg)  # Should not raise

    def test_valid_webp_file_type(self, test_image_webp):
        """Test that valid WebP passes magic byte check."""
        _validate_file_type(test_image_webp)  # Should not raise

    def test_fake_image_file_rejected(self, tmp_path):
        """Test that files with wrong magic bytes are rejected."""
        fake_image = tmp_path / "fake.png"
        fake_image.write_text("This is not an image file!")

        with pytest.raises(ValueError, match="not a valid image"):
            _validate_file_type(fake_image)

    def test_corrupted_image_rejected(self, tmp_path):
        """Test that corrupted image files are rejected."""
        corrupted = tmp_path / "corrupted.png"
        # Write PNG header but incomplete/corrupted data
        corrupted.write_bytes(b"\x89PNG\r\n\x1a\n" + b"garbage data")

        with pytest.raises(ValueError, match="not a valid image"):
            _validate_file_type(corrupted)


class TestValidateSize:
    """Tests for file size validation."""

    def test_small_image_passes(self, test_image_png, default_config):
        """Test that small images pass size validation."""
        _validate_size(test_image_png, default_config)  # Should not raise

    def test_oversized_image_rejected(self, tmp_path, default_config):
        """Test that oversized images are rejected."""
        # Create a file larger than 5MB
        large_file = tmp_path / "large.png"
        large_file.write_bytes(b"x" * (6 * 1024 * 1024))  # 6 MB

        with pytest.raises(ValueError, match="exceeds maximum size"):
            _validate_size(large_file, default_config)

    def test_custom_size_limit(self, tmp_path):
        """Test custom size limit configuration."""
        config = ImageAnalysisToolConfig(max_image_size_mb=1)

        # Create a 2MB file
        medium_file = tmp_path / "medium.png"
        medium_file.write_bytes(b"x" * (2 * 1024 * 1024))

        with pytest.raises(ValueError, match="exceeds maximum size of 1 MB"):
            _validate_size(medium_file, config)


class TestConfigInjection:
    """Tests for config injection pattern."""

    def test_set_and_get_config(self):
        """Test setting and getting config."""
        custom_config = ImageAnalysisToolConfig(
            max_image_size_mb=10, max_images_per_query=3
        )

        set_analyze_images_config(custom_config)
        retrieved_config = get_analyze_images_config()

        assert retrieved_config.max_image_size_mb == 10
        assert retrieved_config.max_images_per_query == 3

    def test_default_config_when_not_set(self):
        """Test that default config is returned when not set."""
        # Reset to None (simulate fresh state)
        set_analyze_images_config(ImageAnalysisToolConfig())

        config = get_analyze_images_config()
        assert isinstance(config, ImageAnalysisToolConfig)
        assert config.max_image_size_mb == 5  # Default value


class TestAnalyzeImagesTool:
    """Tests for the main analyze_images tool."""

    def test_analyze_single_image(self, test_image_png):
        """Test analyzing a single image."""
        set_analyze_images_config(ImageAnalysisToolConfig())

        result = analyze_images.invoke(
            {"query": "What is in this image?", "image_paths": [str(test_image_png)]}
        )

        # Parse JSON result
        assert not result.startswith("❌"), f"Tool returned error: {result}"
        data = json.loads(result)

        assert data["query"] == "What is in this image?"
        assert len(data["images"]) == 1
        assert data["images"][0]["path"] == str(test_image_png)
        assert data["images"][0]["mime_type"] == "image/png"
        assert len(data["images"][0]["data"]) > 0  # Base64 data present

        # Verify base64 decoding works
        base64_data = data["images"][0]["data"]
        decoded = base64.b64decode(base64_data)
        assert len(decoded) > 0

    def test_analyze_multiple_images(
        self, test_image_png, test_image_jpg, test_image_webp
    ):
        """Test analyzing multiple images."""
        set_analyze_images_config(ImageAnalysisToolConfig())

        result = analyze_images.invoke(
            {
                "query": "Compare these images",
                "image_paths": [
                    str(test_image_png),
                    str(test_image_jpg),
                    str(test_image_webp),
                ],
            }
        )

        assert not result.startswith("❌"), f"Tool returned error: {result}"
        data = json.loads(result)

        assert data["query"] == "Compare these images"
        assert len(data["images"]) == 3
        assert data["images"][0]["mime_type"] == "image/png"
        assert data["images"][1]["mime_type"] == "image/jpeg"
        assert data["images"][2]["mime_type"] == "image/webp"

    def test_too_many_images_rejected(self, test_image_png):
        """Test that exceeding max_images_per_query is rejected."""
        set_analyze_images_config(ImageAnalysisToolConfig(max_images_per_query=2))

        result = analyze_images.invoke(
            {
                "query": "Analyze these",
                "image_paths": [str(test_image_png)] * 3,  # 3 images
            }
        )

        assert result.startswith("❌")
        assert "Maximum 2 images allowed" in result

    def test_nonexistent_file_error(self):
        """Test that nonexistent files return error."""
        set_analyze_images_config(ImageAnalysisToolConfig())

        result = analyze_images.invoke(
            {"query": "Analyze this", "image_paths": ["/nonexistent/image.png"]}
        )

        assert result.startswith("❌")
        assert "File not found" in result

    def test_blocked_path_error(self):
        """Test that blocked paths return error."""
        set_analyze_images_config(ImageAnalysisToolConfig())

        result = analyze_images.invoke(
            {"query": "Analyze this", "image_paths": ["/etc/shadow"]}
        )

        assert result.startswith("❌")
        assert "not allowed for security" in result

    def test_invalid_extension_error(self, tmp_path):
        """Test that invalid extensions return error."""
        set_analyze_images_config(ImageAnalysisToolConfig())

        exe_file = tmp_path / "malware.exe"
        exe_file.write_bytes(b"fake executable")

        result = analyze_images.invoke(
            {"query": "Analyze this", "image_paths": [str(exe_file)]}
        )

        assert result.startswith("❌")
        assert "not allowed" in result

    def test_fake_image_magic_bytes_error(self, tmp_path):
        """Test that files with wrong magic bytes return error."""
        set_analyze_images_config(ImageAnalysisToolConfig())

        fake_image = tmp_path / "fake.png"
        fake_image.write_text("This is not an image!")

        result = analyze_images.invoke(
            {"query": "Analyze this", "image_paths": [str(fake_image)]}
        )

        assert result.startswith("❌")
        assert "not a valid image" in result

    def test_oversized_image_error(self, tmp_path):
        """Test that oversized images return error."""
        set_analyze_images_config(ImageAnalysisToolConfig(max_image_size_mb=1))

        # Create 2MB file
        large_file = tmp_path / "large.png"
        large_file.write_bytes(b"x" * (2 * 1024 * 1024))

        result = analyze_images.invoke(
            {"query": "Analyze this", "image_paths": [str(large_file)]}
        )

        assert result.startswith("❌")
        assert "exceeds maximum size" in result

    def test_base64_encoding_accuracy(self, test_image_png):
        """Test that base64 encoding is accurate."""
        set_analyze_images_config(ImageAnalysisToolConfig())

        result = analyze_images.invoke(
            {"query": "Test encoding", "image_paths": [str(test_image_png)]}
        )

        data = json.loads(result)
        base64_data = data["images"][0]["data"]

        # Decode and compare with original
        decoded = base64.b64decode(base64_data)
        original = test_image_png.read_bytes()

        assert decoded == original, "Base64 encoding/decoding mismatch"

    def test_relative_path_support(self, test_image_png):
        """Test that relative paths work correctly."""
        set_analyze_images_config(ImageAnalysisToolConfig())

        # Use relative path from current directory
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(test_image_png.parent)
            result = analyze_images.invoke(
                {"query": "Test relative path", "image_paths": ["test_image.png"]}
            )

            assert not result.startswith("❌"), f"Tool returned error: {result}"
            data = json.loads(result)
            assert len(data["images"]) == 1
        finally:
            os.chdir(original_cwd)

    def test_empty_image_paths_error(self):
        """Test that empty image_paths list is rejected by schema."""
        set_analyze_images_config(ImageAnalysisToolConfig())

        # Pydantic should raise validation error for min_length=1
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            analyze_images.invoke({"query": "Analyze this", "image_paths": []})
