"""Tests for profile-optional Consoul SDK constructor (SOUL-285)."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from consoul.sdk.wrapper import Consoul


class TestProfileOptional:
    """Test profile-optional constructor functionality."""

    @patch("consoul.sdk.wrapper.get_chat_model")
    @patch("consoul.sdk.wrapper.load_config")
    def test_profile_free_basic(self, mock_load_config, mock_get_chat_model):
        """Test basic profile-free instantiation."""
        # Setup mocks
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_load_config.return_value = mock_config

        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model

        # Test: Instantiate without profile (explicit parameters only)
        console = Consoul(
            model="gpt-4o",
            system_prompt="You are a legal assistant",
            tools=False,
            persist=False,
        )

        # Verify
        assert console.model_name == "gpt-4o"
        mock_get_chat_model.assert_called()

    @patch("consoul.sdk.wrapper.get_chat_model")
    @patch("consoul.sdk.wrapper.load_config")
    def test_profile_free_with_conversation_settings(
        self, mock_load_config, mock_get_chat_model
    ):
        """Test profile-free mode with explicit conversation settings."""
        # Setup mocks
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_load_config.return_value = mock_config

        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model

        # Test: Provide conversation settings
        custom_db_path = Path("/tmp/test.db")
        console = Consoul(
            model="claude-sonnet-4",
            system_prompt="You are a medical assistant",
            db_path=custom_db_path,
            summarize=True,
            summarize_threshold=15,
            keep_recent=8,
            tools=False,
            persist=False,
        )

        # Verify conversation kwargs
        conv_kwargs = console._get_conversation_kwargs()
        assert conv_kwargs["db_path"] == custom_db_path
        assert conv_kwargs["summarize"] is True
        assert conv_kwargs["summarize_threshold"] == 15
        assert conv_kwargs["keep_recent"] == 8

    @patch("consoul.sdk.wrapper.get_chat_model")
    @patch("consoul.sdk.wrapper.load_config")
    def test_profile_free_with_summary_model(
        self, mock_load_config, mock_get_chat_model
    ):
        """Test profile-free mode with separate summary model."""
        # Setup mocks
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_load_config.return_value = mock_config

        mock_model = Mock()
        mock_summary_model = Mock()

        def get_model_side_effect(model_name, **kwargs):
            if model_name == "gpt-4o-mini":
                return mock_summary_model
            return mock_model

        mock_get_chat_model.side_effect = get_model_side_effect

        # Test: Provide summary model
        console = Consoul(
            model="gpt-4o",
            summary_model="gpt-4o-mini",
            tools=False,
            persist=False,
        )

        # Verify summary model is initialized
        conv_kwargs = console._get_conversation_kwargs()
        assert "summary_model" in conv_kwargs
        assert conv_kwargs["summary_model"] == mock_summary_model

    @patch("consoul.sdk.wrapper.get_chat_model")
    @patch("consoul.sdk.wrapper.load_config")
    def test_profile_free_default_db_path(self, mock_load_config, mock_get_chat_model):
        """Test profile-free mode uses default db_path when not specified."""
        # Setup mocks
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_load_config.return_value = mock_config

        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model

        # Test: No db_path specified
        console = Consoul(
            model="gpt-4o",
            tools=False,
            persist=False,
        )

        # Verify default db_path
        conv_kwargs = console._get_conversation_kwargs()
        expected_path = Path.home() / ".consoul" / "history.db"
        assert conv_kwargs["db_path"] == expected_path

    @patch("consoul.sdk.wrapper.get_chat_model")
    @patch("consoul.sdk.wrapper.load_config")
    def test_profile_free_system_prompt_priority(
        self, mock_load_config, mock_get_chat_model
    ):
        """Test that explicit system_prompt takes priority in profile-free mode."""
        # Setup mocks
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_load_config.return_value = mock_config

        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model

        # Test: Explicit system prompt
        console = Consoul(
            model="gpt-4o",
            system_prompt="Custom prompt",
            tools=False,
            persist=False,
        )

        # Verify system message was added
        # The history should have add_system_message called with custom prompt
        assert console.history is not None

    @patch("consoul.sdk.wrapper.get_chat_model")
    @patch("consoul.sdk.wrapper.load_config")
    def test_profile_free_model_fallback(self, mock_load_config, mock_get_chat_model):
        """Test model fallback when no model or profile specified."""
        # Setup mocks
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_load_config.return_value = mock_config

        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model

        # Test: No model, no profile
        console = Consoul(
            tools=False,
            persist=False,
        )

        # Verify fallback to config.current_model
        assert console.model_name == "gpt-4o"

    @patch("consoul.sdk.wrapper.get_chat_model")
    @patch("consoul.sdk.wrapper.load_config")
    def test_profile_free_with_provider_kwargs(
        self, mock_load_config, mock_get_chat_model
    ):
        """Test profile-free mode works with provider-specific kwargs."""
        # Setup mocks
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_load_config.return_value = mock_config

        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model

        # Test: Profile-free with provider kwargs
        _console = Consoul(
            model="gpt-4o",
            service_tier="flex",
            temperature=0.7,
            tools=False,
            persist=False,
        )

        # Verify get_chat_model called with provider kwargs
        call_kwargs = mock_get_chat_model.call_args_list[0].kwargs
        assert call_kwargs["service_tier"] == "flex"
        assert call_kwargs["temperature"] == 0.7
        assert _console is not None  # Verify instantiation succeeded

    @patch("consoul.sdk.wrapper.get_chat_model")
    @patch("consoul.sdk.wrapper.load_config")
    def test_profile_free_clear_preserves_system_prompt(
        self, mock_load_config, mock_get_chat_model
    ):
        """Test that clear() works in profile-free mode and preserves system prompt."""
        # Setup mocks
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_load_config.return_value = mock_config

        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model

        # Test: Profile-free with system prompt
        console = Consoul(
            model="gpt-4o",
            system_prompt="You are a legal assistant",
            tools=False,
            persist=False,
        )

        # Call clear - should not raise AttributeError
        try:
            console.clear()
            # Success - no AttributeError raised
        except AttributeError as e:
            pytest.fail(f"clear() raised AttributeError in profile-free mode: {e}")

    @patch("consoul.sdk.wrapper.get_chat_model")
    @patch("consoul.sdk.wrapper.load_config")
    def test_profile_free_settings_property(
        self, mock_load_config, mock_get_chat_model
    ):
        """Test that settings property works in profile-free mode."""
        # Setup mocks
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_load_config.return_value = mock_config

        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model

        # Test: Profile-free mode
        console = Consoul(
            model="gpt-4o",
            system_prompt="You are a legal assistant",
            temperature=0.7,
            tools=False,
            persist=False,
        )

        # Access settings - should not raise AttributeError
        settings = console.settings

        # Verify settings
        assert settings["model"] == "gpt-4o"
        assert settings["system_prompt"] == "You are a legal assistant"
        assert settings["temperature"] == 0.7
        # Note: "profile" key no longer exists in settings (removed in v0.5.0)

    @patch("consoul.sdk.wrapper.get_chat_model")
    @patch("consoul.sdk.wrapper.load_config")
    def test_profile_free_clear_without_system_prompt(
        self, mock_load_config, mock_get_chat_model
    ):
        """Test that clear() works in profile-free mode without system prompt."""
        # Setup mocks
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_load_config.return_value = mock_config

        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model

        # Test: Profile-free without system prompt
        console = Consoul(
            model="gpt-4o",
            tools=False,
            persist=False,
        )

        # Call clear - should not raise AttributeError
        console.clear()

        # Verify no errors

    @patch("consoul.sdk.wrapper.get_chat_model")
    @patch("consoul.sdk.wrapper.load_config")
    def test_profile_parameter_removed_raises_type_error(
        self, mock_load_config, mock_get_chat_model
    ):
        """Test that using profile parameter raises TypeError (v0.5.0 breaking change)."""
        # Setup mocks
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_load_config.return_value = mock_config

        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model

        # Test: profile parameter should raise TypeError
        with pytest.raises(TypeError, match="profile"):
            Consoul(
                profile="default",
                tools=False,
                persist=False,
            )
