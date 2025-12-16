"""Unit tests for package metadata."""

import pytest

import consoul


class TestPackageMetadata:
    """Test package-level metadata and constants."""

    def test_version_exists(self) -> None:
        """Test that __version__ is defined."""
        assert hasattr(consoul, "__version__")
        assert isinstance(consoul.__version__, str)
        assert consoul.__version__ == "0.2.0"

    def test_author_exists(self) -> None:
        """Test that __author__ is defined."""
        assert hasattr(consoul, "__author__")
        assert isinstance(consoul.__author__, str)
        assert consoul.__author__ == "GoatBytes.IO"

    def test_license_exists(self) -> None:
        """Test that __license__ is defined."""
        assert hasattr(consoul, "__license__")
        assert isinstance(consoul.__license__, str)
        assert consoul.__license__ == "Apache-2.0"

    def test_all_exports(self) -> None:
        """Test that __all__ contains expected exports."""
        assert hasattr(consoul, "__all__")
        assert isinstance(consoul.__all__, list)
        # Check that __all__ is sorted alphabetically
        assert consoul.__all__ == sorted(consoul.__all__)
        # Verify expected exports
        expected = [
            "Consoul",
            "ConsoulResponse",
            "__author__",
            "__license__",
            "__version__",
        ]
        assert consoul.__all__ == expected


@pytest.mark.unit
class TestSampleFixtures:
    """Test that fixtures are working correctly."""

    def test_sample_config_fixture(self, sample_config: dict[str, str]) -> None:
        """Test sample_config fixture."""
        assert isinstance(sample_config, dict)
        assert "api_key" in sample_config
        assert "model" in sample_config
        assert sample_config["api_key"] == "test-api-key"

    def test_mock_ai_response_fixture(self, mock_ai_response: str) -> None:
        """Test mock_ai_response fixture."""
        assert isinstance(mock_ai_response, str)
        assert len(mock_ai_response) > 0
        assert "mock" in mock_ai_response.lower()
