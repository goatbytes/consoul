"""Unit tests for Consoul SDK."""

import pytest

from consoul import Consoul, ConsoulResponse


class TestConsoulResponse:
    """Test ConsoulResponse class."""

    def test_init(self) -> None:
        """Test ConsoulResponse initialization."""
        response = ConsoulResponse(
            content="Hello, world!",
            tokens=100,
            model="claude-3-5-sonnet-20241022",
        )
        assert response.content == "Hello, world!"
        assert response.tokens == 100
        assert response.model == "claude-3-5-sonnet-20241022"

    def test_init_defaults(self) -> None:
        """Test ConsoulResponse with default values."""
        response = ConsoulResponse(content="Hello")
        assert response.content == "Hello"
        assert response.tokens == 0
        assert response.model == ""

    def test_str(self) -> None:
        """Test string representation returns content."""
        response = ConsoulResponse(content="Test content", tokens=50)
        assert str(response) == "Test content"

    def test_repr(self) -> None:
        """Test repr shows detailed information."""
        response = ConsoulResponse(
            content="A" * 100,
            tokens=75,
            model="gpt-4o",
        )
        repr_str = repr(response)
        assert "ConsoulResponse" in repr_str
        assert "tokens=75" in repr_str
        assert "model='gpt-4o'" in repr_str
        # Check truncation
        assert len(repr_str) < 150


class TestConsoulInit:
    """Test Consoul initialization."""

    def test_init_invalid_temperature(self) -> None:
        """Test that invalid temperature raises ValueError."""
        with pytest.raises(
            ValueError, match=r"Temperature must be between 0\.0 and 2\.0"
        ):
            Consoul(temperature=3.0)

        with pytest.raises(
            ValueError, match=r"Temperature must be between 0\.0 and 2\.0"
        ):
            Consoul(temperature=-1.0)


class TestConsoulChat:
    """Test Consoul chat/ask methods use basic property tests."""

    def test_chat_and_ask_are_callable(self) -> None:
        """Test that Consoul has chat and ask methods."""
        # We can't easily test full functionality without real API keys
        # So just verify the class has these methods
        assert hasattr(Consoul, "chat")
        assert callable(Consoul.chat)
        assert hasattr(Consoul, "ask")
        assert callable(Consoul.ask)

    def test_clear_is_callable(self) -> None:
        """Test that Consoul has clear method."""
        assert hasattr(Consoul, "clear")
        assert callable(Consoul.clear)


class TestConsoulProperties:
    """Test Consoul has introspection properties."""

    def test_has_settings_property(self) -> None:
        """Test that Consoul class has settings property."""
        assert hasattr(Consoul, "settings")

    def test_has_last_request_property(self) -> None:
        """Test that Consoul class has last_request property."""
        assert hasattr(Consoul, "last_request")

    def test_has_last_cost_property(self) -> None:
        """Test that Consoul class has last_cost property."""
        assert hasattr(Consoul, "last_cost")
