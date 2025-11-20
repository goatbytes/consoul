"""Tests for multimodal message formatting."""

import pytest
from langchain_core.messages import HumanMessage

from consoul.ai.multimodal import (
    _detect_mime_type,
    format_anthropic_vision,
    format_google_vision,
    format_ollama_vision,
    format_openai_vision,
    format_vision_message,
)
from consoul.config.models import Provider


@pytest.fixture
def sample_png_image():
    """Sample PNG image data."""
    return {
        "path": "/test/screenshot.png",
        "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        "mime_type": "image/png",
    }


@pytest.fixture
def sample_jpeg_image():
    """Sample JPEG image data."""
    return {
        "path": "/test/photo.jpg",
        "data": "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/wAALCAABAAEBAREA/8QAFAABAAAAAAAAAAAAAAAAAAAACv/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AVN//2Q==",
        "mime_type": "image/jpeg",
    }


@pytest.fixture
def sample_webp_image():
    """Sample WebP image data."""
    return {
        "path": "/test/diagram.webp",
        "data": "UklGRiQAAABXRUJQVlA4IBgAAAAwAQCdASoBAAEAAwA0JaQAA3AA/vuUAAA=",
        "mime_type": "image/webp",
    }


@pytest.fixture
def sample_gif_image():
    """Sample GIF image data."""
    return {
        "path": "/test/animation.gif",
        "data": "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7",
        "mime_type": "image/gif",
    }


class TestDetectMimeType:
    """Tests for MIME type detection."""

    def test_explicit_mime_type_takes_precedence(self):
        """Test that explicit mime_type parameter takes precedence."""
        mime = _detect_mime_type("/test/file.png", "image/custom")
        assert mime == "image/custom"

    def test_detect_from_png_extension(self):
        """Test PNG detection from file extension."""
        mime = _detect_mime_type("/test/image.png")
        assert mime == "image/png"

    def test_detect_from_jpg_extension(self):
        """Test JPEG detection from .jpg extension."""
        mime = _detect_mime_type("/test/photo.jpg")
        assert mime == "image/jpeg"

    def test_detect_from_jpeg_extension(self):
        """Test JPEG detection from .jpeg extension."""
        mime = _detect_mime_type("/test/photo.jpeg")
        assert mime == "image/jpeg"

    def test_detect_from_webp_extension(self):
        """Test WebP detection from file extension."""
        mime = _detect_mime_type("/test/diagram.webp")
        assert mime == "image/webp"

    def test_detect_from_gif_extension(self):
        """Test GIF detection from file extension."""
        mime = _detect_mime_type("/test/animation.gif")
        assert mime == "image/gif"

    def test_detect_from_bmp_extension(self):
        """Test BMP detection from file extension."""
        mime = _detect_mime_type("/test/bitmap.bmp")
        assert mime == "image/bmp"

    def test_non_image_extension_raises_error(self):
        """Test that non-image extensions raise ValueError."""
        with pytest.raises(ValueError, match="Could not detect MIME type"):
            _detect_mime_type("/test/document.pdf")


class TestFormatAnthropicVision:
    """Tests for Anthropic Claude vision formatting."""

    def test_single_image(self, sample_png_image):
        """Test formatting a single PNG image."""
        message = format_anthropic_vision("Describe this image", [sample_png_image])

        # Verify it's a HumanMessage
        assert isinstance(message, HumanMessage)
        assert len(message.content) == 2
        assert message.content[0] == {"type": "text", "text": "Describe this image"}
        assert message.content[1]["type"] == "image"
        assert message.content[1]["source"]["type"] == "base64"
        assert message.content[1]["source"]["media_type"] == "image/png"
        assert message.content[1]["source"]["data"] == sample_png_image["data"]

    def test_multiple_images(self, sample_png_image, sample_jpeg_image):
        """Test formatting multiple images."""
        message = format_anthropic_vision(
            "Compare these images", [sample_png_image, sample_jpeg_image]
        )

        assert isinstance(message, HumanMessage)
        assert len(message.content) == 3
        assert message.content[0]["type"] == "text"
        assert message.content[1]["type"] == "image"
        assert message.content[1]["source"]["media_type"] == "image/png"
        assert message.content[2]["type"] == "image"
        assert message.content[2]["source"]["media_type"] == "image/jpeg"

    def test_webp_image(self, sample_webp_image):
        """Test formatting WebP image."""
        message = format_anthropic_vision("Analyze this", [sample_webp_image])

        assert message.content[1]["source"]["media_type"] == "image/webp"
        assert message.content[1]["source"]["data"] == sample_webp_image["data"]

    def test_content_block_structure(self, sample_png_image):
        """Test that content blocks have correct structure."""
        message = format_anthropic_vision("Test query", [sample_png_image])

        # Verify required fields are present
        image_block = message.content[1]
        assert "type" in image_block
        assert "source" in image_block
        assert "type" in image_block["source"]
        assert "media_type" in image_block["source"]
        assert "data" in image_block["source"]


class TestFormatOpenAIVision:
    """Tests for OpenAI GPT-4V vision formatting."""

    def test_single_image_data_uri(self, sample_jpeg_image):
        """Test formatting with data URI."""
        message = format_openai_vision("What's in this photo?", [sample_jpeg_image])

        assert len(message.content) == 2
        assert message.content[0] == {"type": "text", "text": "What's in this photo?"}
        assert message.content[1]["type"] == "image_url"
        assert "image_url" in message.content[1]
        assert message.content[1]["image_url"]["url"].startswith(
            "data:image/jpeg;base64,"
        )
        assert sample_jpeg_image["data"] in message.content[1]["image_url"]["url"]

    def test_multiple_images_data_uris(
        self, sample_png_image, sample_jpeg_image, sample_webp_image
    ):
        """Test formatting multiple images with data URIs."""
        message = format_openai_vision(
            "Compare all three",
            [sample_png_image, sample_jpeg_image, sample_webp_image],
        )

        assert len(message.content) == 4
        assert message.content[1]["image_url"]["url"].startswith(
            "data:image/png;base64,"
        )
        assert message.content[2]["image_url"]["url"].startswith(
            "data:image/jpeg;base64,"
        )
        assert message.content[3]["image_url"]["url"].startswith(
            "data:image/webp;base64,"
        )

    def test_data_uri_format(self, sample_png_image):
        """Test data URI format is correct."""
        message = format_openai_vision("Test", [sample_png_image])

        data_uri = message.content[1]["image_url"]["url"]
        assert data_uri.startswith("data:")
        assert ";base64," in data_uri
        assert data_uri.split(";base64,")[0] == "data:image/png"


class TestFormatGoogleVision:
    """Tests for Google Gemini vision formatting."""

    def test_single_image_inline_base64(self, sample_webp_image):
        """Test formatting with inline base64 data."""
        message = format_google_vision("Explain this diagram", [sample_webp_image])

        assert len(message.content) == 2
        assert message.content[0] == {"type": "text", "text": "Explain this diagram"}
        assert message.content[1]["type"] == "image"
        assert message.content[1]["base64"] == sample_webp_image["data"]
        assert message.content[1]["mime_type"] == "image/webp"

    def test_multiple_images(self, sample_png_image, sample_gif_image):
        """Test formatting multiple images."""
        message = format_google_vision(
            "Analyze both", [sample_png_image, sample_gif_image]
        )

        assert len(message.content) == 3
        assert message.content[1]["mime_type"] == "image/png"
        assert message.content[2]["mime_type"] == "image/gif"

    def test_image_structure(self, sample_jpeg_image):
        """Test that image blocks have correct structure."""
        message = format_google_vision("Test", [sample_jpeg_image])

        image_block = message.content[1]
        assert "type" in image_block
        assert "base64" in image_block
        assert "mime_type" in image_block
        assert image_block["type"] == "image"


class TestFormatOllamaVision:
    """Tests for Ollama vision models (qwen3-vl, llava, bakllava)."""

    def test_qwen3vl_single_image(self, sample_png_image):
        """Test formatting for Ollama qwen3-vl model."""
        message = format_ollama_vision("Describe this screenshot", [sample_png_image])

        assert len(message.content) == 2
        assert message.content[0] == {
            "type": "text",
            "text": "Describe this screenshot",
        }
        assert message.content[1]["type"] == "image"
        assert "url" in message.content[1]
        assert message.content[1]["url"].startswith("data:image/png;base64,")

    def test_multiple_images_for_llava(self, sample_png_image, sample_jpeg_image):
        """Test formatting multiple images for llava model."""
        message = format_ollama_vision(
            "Compare these", [sample_png_image, sample_jpeg_image]
        )

        assert len(message.content) == 3
        assert message.content[1]["url"].startswith("data:image/png;base64,")
        assert message.content[2]["url"].startswith("data:image/jpeg;base64,")

    def test_data_uri_contains_base64_data(self, sample_webp_image):
        """Test that data URI contains the actual base64 data."""
        message = format_ollama_vision("Analyze", [sample_webp_image])

        data_uri = message.content[1]["url"]
        assert sample_webp_image["data"] in data_uri

    def test_webp_support(self, sample_webp_image):
        """Test WebP image support for Ollama."""
        message = format_ollama_vision("Test WebP", [sample_webp_image])

        assert message.content[1]["url"].startswith("data:image/webp;base64,")


class TestFormatVisionMessage:
    """Tests for auto-dispatch vision message formatting."""

    def test_anthropic_provider_dispatch(self, sample_png_image):
        """Test automatic dispatch to Anthropic formatter."""
        message = format_vision_message(Provider.ANTHROPIC, "Test", [sample_png_image])

        # Should return HumanMessage with Anthropic-specific structure
        assert isinstance(message, HumanMessage)
        assert message.content[1]["type"] == "image"
        assert "source" in message.content[1]
        assert message.content[1]["source"]["type"] == "base64"

    def test_openai_provider_dispatch(self, sample_jpeg_image):
        """Test automatic dispatch to OpenAI formatter."""
        message = format_vision_message(Provider.OPENAI, "Test", [sample_jpeg_image])

        # Should return HumanMessage with OpenAI-specific structure
        assert isinstance(message, HumanMessage)
        assert message.content[1]["type"] == "image_url"
        assert "image_url" in message.content[1]
        assert "url" in message.content[1]["image_url"]

    def test_google_provider_dispatch(self, sample_webp_image):
        """Test automatic dispatch to Google formatter."""
        message = format_vision_message(Provider.GOOGLE, "Test", [sample_webp_image])

        # Should return HumanMessage with Google-specific structure
        assert isinstance(message, HumanMessage)
        assert message.content[1]["type"] == "image"
        assert "base64" in message.content[1]
        assert "mime_type" in message.content[1]

    def test_ollama_provider_dispatch(self, sample_png_image):
        """Test automatic dispatch to Ollama formatter."""
        message = format_vision_message(Provider.OLLAMA, "Test", [sample_png_image])

        # Should return HumanMessage with Ollama-specific structure
        assert isinstance(message, HumanMessage)
        assert message.content[1]["type"] == "image"
        assert "url" in message.content[1]
        assert message.content[1]["url"].startswith("data:")

    def test_all_providers_return_humanmessage(self, sample_png_image):
        """Test that all providers return HumanMessage objects."""
        query = "Test query"

        for provider in [
            Provider.ANTHROPIC,
            Provider.OPENAI,
            Provider.GOOGLE,
            Provider.OLLAMA,
        ]:
            message = format_vision_message(provider, query, [sample_png_image])
            assert isinstance(message, HumanMessage)
            assert message.content[0]["type"] == "text"
            assert message.content[0]["text"] == query

    def test_unsupported_provider_raises_error(self, sample_png_image):
        """Test that unsupported providers raise ValueError."""
        with pytest.raises(ValueError, match="does not support vision"):
            format_vision_message(Provider.HUGGINGFACE, "Test", [sample_png_image])

    def test_llamacpp_not_supported(self, sample_png_image):
        """Test that LlamaCpp provider raises error."""
        with pytest.raises(ValueError, match="does not support vision"):
            format_vision_message(Provider.LLAMACPP, "Test", [sample_png_image])

    def test_mlx_not_supported(self, sample_png_image):
        """Test that MLX provider raises error."""
        with pytest.raises(ValueError, match="does not support vision"):
            format_vision_message(Provider.MLX, "Test", [sample_png_image])


class TestIntegration:
    """Integration tests simulating real workflow."""

    def test_analyze_images_output_to_anthropic(
        self, sample_png_image, sample_jpeg_image
    ):
        """Test converting analyze_images output to Anthropic format."""
        # Simulate output from analyze_images tool
        images = [sample_png_image, sample_jpeg_image]
        query = "Compare these screenshots and identify differences"

        # Format for Anthropic
        message = format_vision_message(Provider.ANTHROPIC, query, images)

        # Verify structure is valid for Anthropic API
        assert len(message.content) == 3  # 1 text + 2 images
        assert all("type" in block for block in message.content)
        assert message.content[0]["type"] == "text"
        assert message.content[1]["type"] == "image"
        assert message.content[2]["type"] == "image"

    def test_analyze_images_output_to_openai(self, sample_png_image, sample_webp_image):
        """Test converting analyze_images output to OpenAI format."""
        images = [sample_png_image, sample_webp_image]
        query = "What's the main difference between these diagrams?"

        message = format_vision_message(Provider.OPENAI, query, images)

        # Verify data URIs are correctly formatted
        assert message.content[1]["image_url"]["url"].startswith(
            "data:image/png;base64,"
        )
        assert message.content[2]["image_url"]["url"].startswith(
            "data:image/webp;base64,"
        )

    def test_analyze_images_output_to_ollama_qwen3vl(
        self, sample_png_image, sample_jpeg_image, sample_webp_image
    ):
        """Test converting analyze_images output to Ollama qwen3-vl format."""
        images = [sample_png_image, sample_jpeg_image, sample_webp_image]
        query = "Analyze all three images and summarize the content"

        message = format_vision_message(Provider.OLLAMA, query, images)

        # Verify qwen3-vl compatible format
        assert len(message.content) == 4  # 1 text + 3 images
        for i in range(1, 4):
            assert message.content[i]["type"] == "image"
            assert "url" in message.content[i]
            assert message.content[i]["url"].startswith("data:")

    def test_empty_images_list(self):
        """Test handling empty images list."""
        message = format_vision_message(Provider.ANTHROPIC, "Test query", [])

        # Should only have text block
        assert len(message.content) == 1
        assert message.content[0] == {"type": "text", "text": "Test query"}

    def test_mime_type_detection_fallback(self):
        """Test MIME type detection when not provided."""
        # Image without explicit mime_type
        image = {"path": "/test/photo.jpg", "data": "fake_base64_data"}

        message = format_anthropic_vision("Test", [image])

        # Should detect from path
        assert message.content[1]["source"]["media_type"] == "image/jpeg"
