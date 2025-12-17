"""Tests for provider-specific kwargs in Consoul SDK (SOUL-288)."""

import pytest
from unittest.mock import Mock, patch

from consoul.sdk.wrapper import Consoul


class TestProviderKwargs:
    """Test provider-specific parameter passing."""

    @patch("consoul.sdk.wrapper.get_chat_model")
    @patch("consoul.sdk.wrapper.load_config")
    def test_openai_service_tier(self, mock_load_config, mock_get_chat_model):
        """Test OpenAI service_tier parameter is passed through."""
        # Setup mocks
        mock_config = Mock()
        mock_config.profiles = {"default": Mock(system_prompt=None)}
        mock_config.current_model = "gpt-4o"
        mock_load_config.return_value = mock_config

        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model

        # Test: Pass service_tier="flex"
        console = Consoul(
            model="gpt-4o",
            service_tier="flex",
            tools=False,
            persist=False,
        )

        # Verify get_chat_model was called with service_tier for the main model
        # Note: get_chat_model is called twice - once for main model, once for summary model
        assert mock_get_chat_model.call_count >= 1
        # Check first call (main model)
        first_call_kwargs = mock_get_chat_model.call_args_list[0].kwargs
        assert first_call_kwargs["service_tier"] == "flex"

    @patch("consoul.sdk.wrapper.get_chat_model")
    @patch("consoul.sdk.wrapper.load_config")
    def test_anthropic_thinking(self, mock_load_config, mock_get_chat_model):
        """Test Anthropic thinking parameter is passed through."""
        # Setup mocks
        mock_config = Mock()
        mock_config.profiles = {"default": Mock(system_prompt=None)}
        mock_config.current_model = "claude-sonnet-4"
        mock_load_config.return_value = mock_config

        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model

        # Test: Pass thinking configuration
        thinking_config = {"type": "enabled", "budget_tokens": 10000}
        console = Consoul(
            model="claude-sonnet-4",
            thinking=thinking_config,
            tools=False,
            persist=False,
        )

        # Verify get_chat_model was called with thinking for the main model
        assert mock_get_chat_model.call_count >= 1
        first_call_kwargs = mock_get_chat_model.call_args_list[0].kwargs
        assert first_call_kwargs["thinking"] == thinking_config

    @patch("consoul.sdk.wrapper.get_chat_model")
    @patch("consoul.sdk.wrapper.load_config")
    def test_google_safety_settings(self, mock_load_config, mock_get_chat_model):
        """Test Google safety_settings parameter is passed through."""
        # Setup mocks
        mock_config = Mock()
        mock_config.profiles = {"default": Mock(system_prompt=None)}
        mock_config.current_model = "gemini-pro"
        mock_load_config.return_value = mock_config

        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model

        # Test: Pass safety_settings
        safety_settings = {"HARM_CATEGORY_HARASSMENT": "BLOCK_NONE"}
        console = Consoul(
            model="gemini-pro",
            safety_settings=safety_settings,
            tools=False,
            persist=False,
        )

        # Verify get_chat_model was called with safety_settings for the main model
        assert mock_get_chat_model.call_count >= 1
        first_call_kwargs = mock_get_chat_model.call_args_list[0].kwargs
        assert first_call_kwargs["safety_settings"] == safety_settings

    @patch("consoul.sdk.wrapper.get_chat_model")
    @patch("consoul.sdk.wrapper.load_config")
    def test_temperature_override_with_provider_kwargs(
        self, mock_load_config, mock_get_chat_model
    ):
        """Test temperature override works with provider-specific kwargs."""
        # Setup mocks
        mock_config = Mock()
        mock_config.profiles = {"default": Mock(system_prompt=None)}
        mock_config.current_model = "gpt-4o"
        mock_load_config.return_value = mock_config

        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model

        # Test: Pass both temperature and service_tier
        console = Consoul(
            model="gpt-4o",
            temperature=0.9,
            service_tier="flex",
            tools=False,
            persist=False,
        )

        # Verify both parameters are passed for the main model
        assert mock_get_chat_model.call_count >= 1
        first_call_kwargs = mock_get_chat_model.call_args_list[0].kwargs
        assert first_call_kwargs["temperature"] == 0.9
        assert first_call_kwargs["service_tier"] == "flex"

    @patch("consoul.sdk.wrapper.get_chat_model")
    @patch("consoul.sdk.wrapper.load_config")
    def test_multiple_provider_kwargs(self, mock_load_config, mock_get_chat_model):
        """Test multiple provider-specific kwargs are all passed through."""
        # Setup mocks
        mock_config = Mock()
        mock_config.profiles = {"default": Mock(system_prompt=None)}
        mock_config.current_model = "gpt-4o"
        mock_load_config.return_value = mock_config

        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model

        # Test: Pass multiple OpenAI-specific params
        console = Consoul(
            model="gpt-4o",
            service_tier="flex",
            seed=42,
            top_p=0.95,
            frequency_penalty=0.5,
            tools=False,
            persist=False,
        )

        # Verify all parameters are passed for the main model
        assert mock_get_chat_model.call_count >= 1
        first_call_kwargs = mock_get_chat_model.call_args_list[0].kwargs
        assert first_call_kwargs["service_tier"] == "flex"
        assert first_call_kwargs["seed"] == 42
        assert first_call_kwargs["top_p"] == 0.95
        assert first_call_kwargs["frequency_penalty"] == 0.5
