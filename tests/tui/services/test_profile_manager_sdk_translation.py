"""Tests for ProfileManager SDK translation methods (SOUL-289 Phase 2)."""

from pathlib import Path
from unittest.mock import Mock, patch

from consoul.config.models import OpenAIModelConfig
from consoul.tui.config import ConsoulTuiConfig
from consoul.tui.profiles import ProfileConfig
from consoul.tui.services.profile_manager import ProfileManager


class TestProfileToSdkParams:
    """Test profile_to_sdk_params() method."""

    def test_basic_conversion(self):
        """Test basic profile to SDK params conversion."""
        # Create a minimal profile
        profile = ProfileConfig(
            name="test-profile",
            description="Test profile",
            model=OpenAIModelConfig(
                model="gpt-4o",
                temperature=0.7,
            ),
        )

        # Create minimal config
        config = ConsoulTuiConfig(
            profiles={"test-profile": profile},
            active_profile="test-profile",
        )

        # Convert to SDK params
        params = ProfileManager.profile_to_sdk_params(profile, config)

        # Verify basic parameters
        assert params["model"] == "gpt-4o"
        assert params["temperature"] == 0.7
        assert params["tools"] is True
        assert params["persist"] is True  # Default from ConversationConfig
        assert params["summarize"] is False  # Default from ConversationConfig

    def test_with_system_prompt(self):
        """Test conversion with system prompt."""
        profile = ProfileConfig(
            name="test-profile",
            description="Test profile",
            model=OpenAIModelConfig(model="gpt-4o"),
            system_prompt="You are a helpful assistant",
        )

        config = ConsoulTuiConfig(
            profiles={"test-profile": profile},
            active_profile="test-profile",
        )

        params = ProfileManager.profile_to_sdk_params(profile, config)

        assert params["system_prompt"] == "You are a helpful assistant"

    def test_with_max_tokens(self):
        """Test conversion with max_tokens."""
        profile = ProfileConfig(
            name="test-profile",
            description="Test profile",
            model=OpenAIModelConfig(
                model="gpt-4o",
                max_tokens=2048,
            ),
        )

        config = ConsoulTuiConfig(
            profiles={"test-profile": profile},
            active_profile="test-profile",
        )

        params = ProfileManager.profile_to_sdk_params(profile, config)

        assert params["max_tokens"] == 2048

    def test_with_conversation_settings(self):
        """Test conversion with custom conversation settings."""
        from consoul.config.models import ConversationConfig

        profile = ProfileConfig(
            name="test-profile",
            description="Test profile",
            model=OpenAIModelConfig(model="gpt-4o"),
            conversation=ConversationConfig(
                persist=False,
                db_path=Path("/tmp/test.db"),
                summarize=True,
                summarize_threshold=15,
                keep_recent=8,
            ),
        )

        config = ConsoulTuiConfig(
            profiles={"test-profile": profile},
            active_profile="test-profile",
        )

        params = ProfileManager.profile_to_sdk_params(profile, config)

        assert params["persist"] is False
        assert params["db_path"] == Path("/tmp/test.db")
        assert params["summarize"] is True
        assert params["summarize_threshold"] == 15
        assert params["keep_recent"] == 8

    def test_with_summary_model(self):
        """Test conversion with separate summary model."""
        from consoul.config.models import ConversationConfig

        profile = ProfileConfig(
            name="test-profile",
            description="Test profile",
            model=OpenAIModelConfig(model="gpt-4o"),
            conversation=ConversationConfig(
                summarize=True,
                summary_model="gpt-4o-mini",
            ),
        )

        config = ConsoulTuiConfig(
            profiles={"test-profile": profile},
            active_profile="test-profile",
        )

        params = ProfileManager.profile_to_sdk_params(profile, config)

        assert params["summary_model"] == "gpt-4o-mini"

    def test_all_sdk_parameters_extracted(self):
        """Test that all 7 SDK parameters are extracted correctly."""
        from consoul.config.models import ConversationConfig

        profile = ProfileConfig(
            name="complete-profile",
            description="Complete test profile",
            model=OpenAIModelConfig(
                model="gpt-4o",
                temperature=0.8,
                max_tokens=4096,
            ),
            system_prompt="Complete system prompt",
            conversation=ConversationConfig(
                persist=False,
                db_path=Path("/custom/path.db"),
                summarize=True,
                summarize_threshold=20,
                keep_recent=12,
                summary_model="gpt-4o-mini",
            ),
        )

        config = ConsoulTuiConfig(
            profiles={"complete-profile": profile},
            active_profile="complete-profile",
        )

        params = ProfileManager.profile_to_sdk_params(profile, config)

        # Verify all expected parameters are present
        expected_params = {
            "model",
            "temperature",
            "max_tokens",
            "system_prompt",
            "persist",
            "db_path",
            "summarize",
            "summarize_threshold",
            "keep_recent",
            "summary_model",
            "tools",
        }

        assert set(params.keys()) == expected_params

        # Verify values
        assert params["model"] == "gpt-4o"
        assert params["temperature"] == 0.8
        assert params["max_tokens"] == 4096
        assert params["system_prompt"] == "Complete system prompt"
        assert params["persist"] is False
        assert params["db_path"] == Path("/custom/path.db")
        assert params["summarize"] is True
        assert params["summarize_threshold"] == 20
        assert params["keep_recent"] == 12
        assert params["summary_model"] == "gpt-4o-mini"
        assert params["tools"] is True


class TestBuildProfileSystemPrompt:
    """Test build_profile_system_prompt() method."""

    @patch("consoul.tui.services.profile_manager.build_enhanced_system_prompt")
    def test_basic_prompt_building(self, mock_build_prompt):
        """Test basic system prompt building."""
        mock_build_prompt.return_value = "Enhanced prompt with context"

        profile = ProfileConfig(
            name="test-profile",
            description="Test profile",
            model=OpenAIModelConfig(model="gpt-4o"),
            system_prompt="Base prompt",
        )

        config = ConsoulTuiConfig(
            profiles={"test-profile": profile},
            active_profile="test-profile",
        )

        result = ProfileManager.build_profile_system_prompt(profile, config)

        # Verify build_enhanced_system_prompt was called
        mock_build_prompt.assert_called_once()
        call_kwargs = mock_build_prompt.call_args.kwargs

        assert call_kwargs["base_prompt"] == "Base prompt"
        assert call_kwargs["auto_append_tools"] is True
        assert call_kwargs["include_datetime_info"] is True
        assert result == "Enhanced prompt with context"

    @patch("consoul.tui.services.profile_manager.build_enhanced_system_prompt")
    def test_with_system_context_enabled(self, mock_build_prompt):
        """Test prompt building with system context enabled."""
        from consoul.config.models import ContextConfig

        mock_build_prompt.return_value = "Prompt with system context"

        profile = ProfileConfig(
            name="test-profile",
            description="Test profile",
            model=OpenAIModelConfig(model="gpt-4o"),
            system_prompt="Base prompt",
            context=ContextConfig(include_system_info=True),
        )

        config = ConsoulTuiConfig(
            profiles={"test-profile": profile},
            active_profile="test-profile",
        )

        ProfileManager.build_profile_system_prompt(profile, config)

        call_kwargs = mock_build_prompt.call_args.kwargs
        assert call_kwargs["include_os_info"] is True
        assert call_kwargs["include_shell_info"] is True
        assert call_kwargs["include_directory_info"] is True

    @patch("consoul.tui.services.profile_manager.build_enhanced_system_prompt")
    def test_with_git_context_enabled(self, mock_build_prompt):
        """Test prompt building with git context enabled."""
        from consoul.config.models import ContextConfig

        mock_build_prompt.return_value = "Prompt with git context"

        profile = ProfileConfig(
            name="test-profile",
            description="Test profile",
            model=OpenAIModelConfig(model="gpt-4o"),
            system_prompt="Base prompt",
            context=ContextConfig(include_git_info=True),
        )

        config = ConsoulTuiConfig(
            profiles={"test-profile": profile},
            active_profile="test-profile",
        )

        ProfileManager.build_profile_system_prompt(profile, config)

        call_kwargs = mock_build_prompt.call_args.kwargs
        assert call_kwargs["include_git_info"] is True

    @patch("consoul.tui.services.profile_manager.build_enhanced_system_prompt")
    def test_empty_prompt_handling(self, mock_build_prompt):
        """Test handling of empty/None system prompt."""
        mock_build_prompt.return_value = "Default prompt"

        profile = ProfileConfig(
            name="test-profile",
            description="Test profile",
            model=OpenAIModelConfig(model="gpt-4o"),
            # No system_prompt set
        )

        config = ConsoulTuiConfig(
            profiles={"test-profile": profile},
            active_profile="test-profile",
        )

        result = ProfileManager.build_profile_system_prompt(profile, config)

        call_kwargs = mock_build_prompt.call_args.kwargs
        assert call_kwargs["base_prompt"] == ""
        assert result == "Default prompt"

    @patch("consoul.tui.services.profile_manager.build_enhanced_system_prompt")
    def test_none_return_handling(self, mock_build_prompt):
        """Test handling when build_enhanced_system_prompt returns None."""
        mock_build_prompt.return_value = None

        profile = ProfileConfig(
            name="test-profile",
            description="Test profile",
            model=OpenAIModelConfig(model="gpt-4o"),
            system_prompt="Base prompt",
        )

        config = ConsoulTuiConfig(
            profiles={"test-profile": profile},
            active_profile="test-profile",
        )

        result = ProfileManager.build_profile_system_prompt(profile, config)

        # Should return empty string when None
        assert result == ""


class TestGetConversationKwargs:
    """Test get_conversation_kwargs() method."""

    def test_default_conversation_kwargs(self):
        """Test extracting default conversation kwargs."""
        profile = ProfileConfig(
            name="test-profile",
            description="Test profile",
            model=OpenAIModelConfig(model="gpt-4o"),
        )

        kwargs = ProfileManager.get_conversation_kwargs(profile)

        # Verify all 8 conversation parameters are present
        expected_keys = {
            "persist",
            "db_path",
            "auto_resume",
            "retention_days",
            "summarize",
            "summarize_threshold",
            "keep_recent",
            "summary_model",
        }

        assert set(kwargs.keys()) == expected_keys

    def test_custom_conversation_kwargs(self):
        """Test extracting custom conversation kwargs."""
        from consoul.config.models import ConversationConfig

        profile = ProfileConfig(
            name="test-profile",
            description="Test profile",
            model=OpenAIModelConfig(model="gpt-4o"),
            conversation=ConversationConfig(
                persist=False,
                db_path=Path("/custom/db.db"),
                auto_resume=False,
                retention_days=60,
                summarize=True,
                summarize_threshold=25,
                keep_recent=15,
                summary_model="gpt-4o-mini",
            ),
        )

        kwargs = ProfileManager.get_conversation_kwargs(profile)

        assert kwargs["persist"] is False
        assert kwargs["db_path"] == Path("/custom/db.db")
        assert kwargs["auto_resume"] is False
        assert kwargs["retention_days"] == 60
        assert kwargs["summarize"] is True
        assert kwargs["summarize_threshold"] == 25
        assert kwargs["keep_recent"] == 15
        assert kwargs["summary_model"] == "gpt-4o-mini"

    def test_conversation_service_compatibility(self):
        """Test that kwargs are compatible with ConversationService initialization."""
        from consoul.config.models import ConversationConfig

        profile = ProfileConfig(
            name="test-profile",
            description="Test profile",
            model=OpenAIModelConfig(model="gpt-4o"),
            conversation=ConversationConfig(
                persist=True,
                db_path=Path.home() / ".consoul" / "test.db",
                auto_resume=True,
                retention_days=30,
                summarize=False,
                summarize_threshold=20,
                keep_recent=10,
                summary_model=None,
            ),
        )

        kwargs = ProfileManager.get_conversation_kwargs(profile)

        # These should match ConversationService.__init__ parameters
        # Verify structure is correct (no test instantiation of service needed)
        assert isinstance(kwargs["persist"], bool)
        assert isinstance(kwargs["db_path"], Path)
        assert isinstance(kwargs["auto_resume"], bool)
        assert isinstance(kwargs["retention_days"], int)
        assert isinstance(kwargs["summarize"], bool)
        assert isinstance(kwargs["summarize_threshold"], int)
        assert isinstance(kwargs["keep_recent"], int)
        assert kwargs["summary_model"] is None or isinstance(
            kwargs["summary_model"], str
        )


class TestGetModelName:
    """Test get_model_name() method."""

    def test_model_from_profile(self):
        """Test getting model name from profile."""
        profile = ProfileConfig(
            name="test-profile",
            description="Test profile",
            model=OpenAIModelConfig(model="gpt-4o"),
        )

        config = ConsoulTuiConfig(
            profiles={"test-profile": profile},
            active_profile="test-profile",
            current_model="fallback-model",
        )

        model_name = ProfileManager.get_model_name(profile, config)

        assert model_name == "gpt-4o"

    def test_model_fallback_to_config(self):
        """Test fallback to config.current_model when profile has no model."""
        # Create profile without model config
        profile = ProfileConfig(
            name="test-profile",
            description="Test profile",
            model=OpenAIModelConfig(model="gpt-4o"),
        )

        # Mock profile.model to None
        profile_mock = Mock(spec=ProfileConfig)
        profile_mock.model = None

        config = ConsoulTuiConfig(
            profiles={"test-profile": profile},
            active_profile="test-profile",
            current_model="fallback-model",
        )

        model_name = ProfileManager.get_model_name(profile_mock, config)

        assert model_name == "fallback-model"

    def test_different_model_names(self):
        """Test with various model names."""
        from consoul.config.models import AnthropicModelConfig

        test_cases = [
            ("gpt-4o", OpenAIModelConfig),
            ("gpt-4o-mini", OpenAIModelConfig),
            ("claude-3-5-sonnet-20241022", AnthropicModelConfig),
            ("claude-3-5-haiku-20241022", AnthropicModelConfig),
        ]

        for model_name, model_config_class in test_cases:
            profile = ProfileConfig(
                name="test-profile",
                description="Test profile",
                model=model_config_class(model=model_name),
            )

            config = ConsoulTuiConfig(
                profiles={"test-profile": profile},
                active_profile="test-profile",
            )

            result = ProfileManager.get_model_name(profile, config)
            assert result == model_name


class TestIntegration:
    """Integration tests for SDK translation workflow."""

    def test_complete_sdk_translation_workflow(self):
        """Test complete workflow: profile -> SDK params -> SDK instantiation."""
        from consoul.config.models import ContextConfig, ConversationConfig

        # Create a comprehensive profile
        profile = ProfileConfig(
            name="integration-profile",
            description="Integration test profile",
            model=OpenAIModelConfig(
                model="gpt-4o",
                temperature=0.7,
                max_tokens=2048,
            ),
            system_prompt="You are a code review assistant",
            conversation=ConversationConfig(
                persist=True,
                summarize=True,
                summarize_threshold=15,
                keep_recent=8,
            ),
            context=ContextConfig(
                include_system_info=True,
                include_git_info=True,
            ),
        )

        config = ConsoulTuiConfig(
            profiles={"integration-profile": profile},
            active_profile="integration-profile",
        )

        # Step 1: Extract SDK params
        sdk_params = ProfileManager.profile_to_sdk_params(profile, config)

        # Step 2: Verify all essential params extracted
        assert "model" in sdk_params
        assert "temperature" in sdk_params
        assert "system_prompt" in sdk_params
        assert "persist" in sdk_params
        assert "summarize" in sdk_params

        # Step 3: Verify params are SDK-compatible types
        assert isinstance(sdk_params["model"], str)
        assert isinstance(sdk_params["temperature"], (int, float))
        assert isinstance(sdk_params["system_prompt"], str)
        assert isinstance(sdk_params["persist"], bool)
        assert isinstance(sdk_params["tools"], bool)

        # Step 4: Get model name
        model_name = ProfileManager.get_model_name(profile, config)
        assert model_name == "gpt-4o"
        assert model_name == sdk_params["model"]

        # Step 5: Get conversation kwargs
        conv_kwargs = ProfileManager.get_conversation_kwargs(profile)
        assert conv_kwargs["persist"] == sdk_params["persist"]
        assert conv_kwargs["summarize"] == sdk_params["summarize"]

    @patch("consoul.tui.services.profile_manager.build_enhanced_system_prompt")
    def test_sdk_params_with_enhanced_prompt(self, mock_build_prompt):
        """Test SDK params include enhanced system prompt."""
        mock_build_prompt.return_value = "Enhanced prompt with full context"

        profile = ProfileConfig(
            name="test-profile",
            description="Test profile",
            model=OpenAIModelConfig(model="gpt-4o"),
            system_prompt="Base prompt",
        )

        config = ConsoulTuiConfig(
            profiles={"test-profile": profile},
            active_profile="test-profile",
        )

        # Extract SDK params
        sdk_params = ProfileManager.profile_to_sdk_params(profile, config)

        # Build enhanced prompt (as SDK would do)
        enhanced_prompt = ProfileManager.build_profile_system_prompt(profile, config)

        # Verify base prompt in SDK params
        assert sdk_params["system_prompt"] == "Base prompt"

        # Verify enhanced prompt is built separately
        assert enhanced_prompt == "Enhanced prompt with full context"

        # In actual SDK usage, the enhanced prompt would replace the base prompt
