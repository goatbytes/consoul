"""Pytest configuration and shared fixtures for Consoul tests."""

import pytest


@pytest.fixture
def sample_config() -> dict[str, str]:
    """Provide a sample configuration for testing.

    Returns:
        Dictionary containing test configuration values.
    """
    return {
        "api_key": "test-api-key",
        "model": "gpt-4",
        "temperature": "0.7",
    }


@pytest.fixture
def mock_ai_response() -> str:
    """Provide a mock AI response for testing.

    Returns:
        Sample AI response text.
    """
    return "This is a mock AI response for testing purposes."
