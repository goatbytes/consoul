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

        # Test: Instantiate without profile (explicitly set profile=None)
        console = Consoul(
            profile=None,
            model="gpt-4o",
            system_prompt="You are a legal assistant",
            tools=False,
            persist=False,
        )

        # Verify
        assert console.profile is None
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
            profile=None,
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
            profile=None,
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
    def test_backward_compat_with_profile(self, mock_load_config, mock_get_chat_model):
        """Test backward compatibility with existing profile usage."""
        # Setup mocks
        mock_config = Mock()
        mock_profile = Mock()
        mock_profile.system_prompt = "Default system prompt"
        mock_profile.conversation = Mock()
        mock_profile.conversation.db_path = Path.home() / ".consoul" / "history.db"
        mock_profile.conversation.summarize = False
        mock_profile.conversation.summarize_threshold = 20
        mock_profile.conversation.keep_recent = 10
        mock_profile.conversation.summary_model = None
        mock_profile.model = None

        mock_config.profiles = {"default": mock_profile}
        mock_config.current_model = "gpt-4o"
        mock_load_config.return_value = mock_config

        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model

        # Test: Use profile (backward compatibility)
        console = Consoul(
            profile="default",
            tools=False,
            persist=False,
        )

        # Verify profile is used
        assert console.profile == mock_profile
        assert console.model_name == "gpt-4o"

    @patch("consoul.sdk.wrapper.get_chat_model")
    @patch("consoul.sdk.wrapper.load_config")
    def test_direct_param_overrides_profile(
        self, mock_load_config, mock_get_chat_model
    ):
        """Test that direct parameters override profile settings."""
        # Setup mocks
        mock_config = Mock()
        mock_profile = Mock()
        mock_profile.system_prompt = "Default system prompt"
        mock_profile.conversation = Mock()
        mock_profile.conversation.db_path = Path.home() / ".consoul" / "history.db"
        mock_profile.conversation.summarize = False
        mock_profile.model = None

        mock_config.profiles = {"default": mock_profile}
        mock_config.current_model = "gpt-4o"
        mock_load_config.return_value = mock_config

        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model

        # Test: Override profile with direct params
        console = Consoul(
            profile="default",
            temperature=0.9,
            system_prompt="Custom system prompt",
            tools=False,
            persist=False,
        )

        # Verify overrides
        assert console.temperature == 0.9
        assert console.profile.system_prompt == "Custom system prompt"

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
            profile=None,
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
            profile=None,
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
            profile=None,
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
            profile=None,
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
            profile=None,
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
            profile=None,
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
        assert settings["profile"] is None  # No profile in profile-free mode
        assert settings["system_prompt"] == "You are a legal assistant"
        assert settings["temperature"] == 0.7

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
            profile=None,
            model="gpt-4o",
            tools=False,
            persist=False,
        )

        # Call clear - should not raise AttributeError
        console.clear()

        # Verify no errors

    @patch("consoul.sdk.wrapper.get_chat_model")
    @patch("consoul.sdk.wrapper.load_config")
    def test_profile_mode_clear_still_works(
        self, mock_load_config, mock_get_chat_model
    ):
        """Test that clear() still works correctly with profiles (backward compat)."""
        # Setup mocks
        mock_config = Mock()
        mock_profile = Mock()
        mock_profile.system_prompt = "Default system prompt"
        mock_profile.conversation = Mock()
        mock_profile.conversation.db_path = Path.home() / ".consoul" / "history.db"
        mock_profile.conversation.summarize = False
        mock_profile.conversation.summarize_threshold = 20
        mock_profile.conversation.keep_recent = 10
        mock_profile.conversation.summary_model = None
        mock_profile.model = None

        mock_config.profiles = {"default": mock_profile}
        mock_config.current_model = "gpt-4o"
        mock_load_config.return_value = mock_config

        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model

        # Test: Profile mode
        console = Consoul(
            profile="default",
            tools=False,
            persist=False,
        )

        # Call clear - should not raise AttributeError
        try:
            console.clear()
            # Success - backward compatibility maintained
        except AttributeError as e:
            pytest.fail(f"clear() raised AttributeError with profile: {e}")


class TestProfileDeprecation:
    """Test deprecation warnings for profile parameter (SOUL-289)."""

    @patch("consoul.sdk.wrapper.get_chat_model")
    @patch("consoul.sdk.wrapper.load_config")
    def test_profile_parameter_raises_deprecation_warning(
        self, mock_load_config, mock_get_chat_model
    ):
        """Test that using profile parameter raises DeprecationWarning."""
        # Setup mocks
        mock_config = Mock()
        mock_config.profiles = {
            "default": Mock(
                model=Mock(model="gpt-4o", temperature=0.7),
                system_prompt="Test prompt",
            )
        }
        mock_config.current_model = "gpt-4o"
        mock_load_config.return_value = mock_config

        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model

        # Test: Using profile parameter should raise DeprecationWarning
        with pytest.warns(DeprecationWarning, match="profile.*deprecated"):
            Consoul(
                profile="default",
                tools=False,
                persist=False,
            )

    @patch("consoul.sdk.wrapper.get_chat_model")
    @patch("consoul.sdk.wrapper.load_config")
    def test_deprecation_warning_message_content(
        self, mock_load_config, mock_get_chat_model
    ):
        """Test that deprecation warning contains helpful migration info."""
        # Setup mocks
        mock_config = Mock()
        mock_config.profiles = {
            "default": Mock(
                model=Mock(model="gpt-4o", temperature=0.7),
                system_prompt="Test prompt",
            )
        }
        mock_config.current_model = "gpt-4o"
        mock_load_config.return_value = mock_config

        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model

        # Test: Warning should mention v1.0.0 removal and migration guide
        with pytest.warns(DeprecationWarning) as warning_list:
            Consoul(
                profile="default",
                tools=False,
                persist=False,
            )

        # Verify warning content
        warning_message = str(warning_list[0].message)
        assert "v1.0.0" in warning_message
        assert "TUI/CLI" in warning_message or "explicit parameters" in warning_message
        assert (
            "migration" in warning_message.lower()
            or "deprecated" in warning_message.lower()
        )

    @patch("consoul.sdk.wrapper.get_chat_model")
    @patch("consoul.sdk.wrapper.load_config")
    def test_profile_free_mode_no_deprecation_warning(
        self, mock_load_config, mock_get_chat_model
    ):
        """Test that profile-free mode does not raise deprecation warning."""
        # Setup mocks
        mock_config = Mock()
        mock_config.current_model = "gpt-4o"
        mock_load_config.return_value = mock_config

        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model

        # Test: Profile-free mode should NOT raise DeprecationWarning
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            try:
                Consoul(
                    model="gpt-4o",
                    system_prompt="You are a helpful assistant",
                    tools=False,
                    persist=False,
                )
                # Success - no deprecation warning
            except DeprecationWarning:
                pytest.fail("Profile-free mode raised DeprecationWarning unexpectedly")

    @patch("consoul.config.profiles.get_builtin_profiles")
    @patch("consoul.sdk.wrapper.get_chat_model")
    @patch("consoul.sdk.wrapper.load_config")
    def test_builtin_profile_also_raises_deprecation(
        self, mock_load_config, mock_get_chat_model, mock_builtin_profiles
    ):
        """Test that builtin profiles also raise deprecation warnings."""
        # Setup mocks
        mock_config = Mock()
        mock_config.profiles = {}  # No user profiles
        mock_config.current_model = "gpt-4o"
        mock_load_config.return_value = mock_config

        mock_model = Mock()
        mock_get_chat_model.return_value = mock_model

        # Mock builtin profiles
        mock_builtin_profiles.return_value = {
            "default": {
                "name": "default",
                "description": "Default profile",
                "system_prompt": "Test",
            }
        }

        # Test: Even builtin profiles should raise deprecation
        with pytest.warns(DeprecationWarning, match="profile.*deprecated"):
            Consoul(
                profile="default",
                tools=False,
                persist=False,
            )
