"""Tests for Pydantic configuration models."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from consoul.config.models import (
    ConsoulConfig,
    ContextConfig,
    ConversationConfig,
    ModelConfig,
    ProfileConfig,
    Provider,
)


class TestProvider:
    """Tests for Provider enum."""

    def test_provider_values(self):
        """Test that all expected providers are defined."""
        assert Provider.OPENAI == "openai"
        assert Provider.ANTHROPIC == "anthropic"
        assert Provider.GOOGLE == "google"
        assert Provider.OLLAMA == "ollama"


class TestModelConfig:
    """Tests for ModelConfig."""

    def test_valid_model_config(self):
        """Test creating a valid ModelConfig."""
        config = ModelConfig(
            provider=Provider.OPENAI,
            model="gpt-4o",
            temperature=0.7,
            max_tokens=2048,
        )
        assert config.provider == Provider.OPENAI
        assert config.model == "gpt-4o"
        assert config.temperature == 0.7
        assert config.max_tokens == 2048

    def test_default_temperature(self):
        """Test default temperature value."""
        config = ModelConfig(provider=Provider.OPENAI, model="gpt-4o")
        assert config.temperature == 1.0

    def test_temperature_validation(self):
        """Test temperature must be between 0.0 and 2.0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelConfig(provider=Provider.OPENAI, model="gpt-4o", temperature=-0.1)
        assert "greater than or equal to 0" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            ModelConfig(provider=Provider.OPENAI, model="gpt-4o", temperature=2.1)
        assert "less than or equal to 2" in str(exc_info.value)

    def test_top_p_validation(self):
        """Test top_p must be between 0.0 and 1.0."""
        config = ModelConfig(provider=Provider.OPENAI, model="gpt-4o", top_p=0.9)
        assert config.top_p == 0.9

        with pytest.raises(ValidationError) as exc_info:
            ModelConfig(provider=Provider.OPENAI, model="gpt-4o", top_p=1.1)
        assert "less than or equal to 1" in str(exc_info.value)

    def test_penalty_validation(self):
        """Test frequency and presence penalties must be between -2.0 and 2.0."""
        config = ModelConfig(
            provider=Provider.OPENAI,
            model="gpt-4o",
            frequency_penalty=1.5,
            presence_penalty=-1.5,
        )
        assert config.frequency_penalty == 1.5
        assert config.presence_penalty == -1.5

        with pytest.raises(ValidationError) as exc_info:
            ModelConfig(provider=Provider.OPENAI, model="gpt-4o", frequency_penalty=2.5)
        assert "less than or equal to 2" in str(exc_info.value)

    def test_empty_model_name_validation(self):
        """Test that empty model name is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelConfig(provider=Provider.OPENAI, model="")
        assert "Model name cannot be empty" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            ModelConfig(provider=Provider.OPENAI, model="   ")
        assert "Model name cannot be empty" in str(exc_info.value)

    def test_model_name_stripped(self):
        """Test that model name is stripped of whitespace."""
        config = ModelConfig(provider=Provider.OPENAI, model="  gpt-4o  ")
        assert config.model == "gpt-4o"

    def test_ollama_penalty_validation(self):
        """Test that Ollama provider rejects penalty parameters."""
        with pytest.raises(ValidationError) as exc_info:
            ModelConfig(
                provider=Provider.OLLAMA,
                model="llama3",
                frequency_penalty=1.0,
            )
        assert "does not support frequency_penalty" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            ModelConfig(
                provider=Provider.OLLAMA,
                model="llama3",
                presence_penalty=1.0,
            )
        assert "does not support" in str(exc_info.value)

    def test_top_k_validation(self):
        """Test that top_k is only allowed for Anthropic."""
        # Should work for Anthropic
        config = ModelConfig(
            provider=Provider.ANTHROPIC,
            model="claude-3-5-sonnet-20241022",
            top_k=40,
        )
        assert config.top_k == 40

        # Should fail for other providers
        with pytest.raises(ValidationError) as exc_info:
            ModelConfig(provider=Provider.OPENAI, model="gpt-4o", top_k=40)
        assert "does not support top_k" in str(exc_info.value)

    def test_stop_sequences(self):
        """Test stop sequences configuration."""
        config = ModelConfig(
            provider=Provider.OPENAI,
            model="gpt-4o",
            stop_sequences=["END", "STOP"],
        )
        assert config.stop_sequences == ["END", "STOP"]

    def test_extra_fields_forbidden(self):
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelConfig(
                provider=Provider.OPENAI,
                model="gpt-4o",
                invalid_field="value",
            )
        assert "Extra inputs are not permitted" in str(exc_info.value)


class TestConversationConfig:
    """Tests for ConversationConfig."""

    def test_default_values(self):
        """Test default conversation configuration."""
        config = ConversationConfig()
        assert config.save_history is True
        assert config.history_file == Path.home() / ".consoul" / "history.json"
        assert config.max_history_length == 100
        assert config.auto_save is True

    def test_custom_values(self):
        """Test custom conversation configuration."""
        config = ConversationConfig(
            save_history=False,
            history_file=Path("/tmp/history.json"),
            max_history_length=50,
            auto_save=False,
        )
        assert config.save_history is False
        assert config.history_file == Path("/tmp/history.json")
        assert config.max_history_length == 50
        assert config.auto_save is False

    def test_path_expansion(self):
        """Test that paths are expanded properly."""
        config = ConversationConfig(history_file="~/custom/history.json")
        assert config.history_file == Path.home() / "custom" / "history.json"

    def test_max_history_validation(self):
        """Test max_history_length must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            ConversationConfig(max_history_length=0)
        assert "greater than 0" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            ConversationConfig(max_history_length=-1)
        assert "greater than 0" in str(exc_info.value)


class TestContextConfig:
    """Tests for ContextConfig."""

    def test_default_values(self):
        """Test default context configuration."""
        config = ContextConfig()
        assert config.max_context_tokens == 4096
        assert config.include_system_info is True
        assert config.include_git_info is True
        assert config.custom_context_files == []

    def test_custom_values(self):
        """Test custom context configuration."""
        config = ContextConfig(
            max_context_tokens=8192,
            include_system_info=False,
            include_git_info=False,
            custom_context_files=[Path("/tmp/context.txt")],
        )
        assert config.max_context_tokens == 8192
        assert config.include_system_info is False
        assert config.include_git_info is False
        assert config.custom_context_files == [Path("/tmp/context.txt")]

    def test_context_files_path_expansion(self):
        """Test that custom context file paths are expanded."""
        config = ContextConfig(
            custom_context_files=["~/context1.txt", "~/context2.txt"]
        )
        assert all(isinstance(p, Path) for p in config.custom_context_files)
        assert config.custom_context_files[0] == Path.home() / "context1.txt"
        assert config.custom_context_files[1] == Path.home() / "context2.txt"

    def test_max_context_tokens_validation(self):
        """Test max_context_tokens must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            ContextConfig(max_context_tokens=0)
        assert "greater than 0" in str(exc_info.value)


class TestProfileConfig:
    """Tests for ProfileConfig."""

    def test_valid_profile(self):
        """Test creating a valid profile."""
        profile = ProfileConfig(
            name="default",
            description="Default profile",
            model=ModelConfig(provider=Provider.OPENAI, model="gpt-4o"),
        )
        assert profile.name == "default"
        assert profile.description == "Default profile"
        assert profile.model.provider == Provider.OPENAI
        assert profile.model.model == "gpt-4o"
        assert isinstance(profile.conversation, ConversationConfig)
        assert isinstance(profile.context, ContextConfig)

    def test_profile_name_normalization(self):
        """Test that profile names are normalized to lowercase."""
        profile = ProfileConfig(
            name="Default",
            description="Test",
            model=ModelConfig(provider=Provider.OPENAI, model="gpt-4o"),
        )
        assert profile.name == "default"

    def test_profile_name_validation(self):
        """Test profile name validation."""
        # Empty name should fail
        with pytest.raises(ValidationError) as exc_info:
            ProfileConfig(
                name="",
                description="Test",
                model=ModelConfig(provider=Provider.OPENAI, model="gpt-4o"),
            )
        assert "cannot be empty" in str(exc_info.value)

        # Invalid characters should fail
        with pytest.raises(ValidationError) as exc_info:
            ProfileConfig(
                name="my profile!",
                description="Test",
                model=ModelConfig(provider=Provider.OPENAI, model="gpt-4o"),
            )
        assert "alphanumeric" in str(exc_info.value)

    def test_profile_with_custom_configs(self):
        """Test profile with custom conversation and context configs."""
        profile = ProfileConfig(
            name="custom",
            description="Custom profile",
            model=ModelConfig(provider=Provider.OPENAI, model="gpt-4o"),
            conversation=ConversationConfig(save_history=False),
            context=ContextConfig(max_context_tokens=8192),
        )
        assert profile.conversation.save_history is False
        assert profile.context.max_context_tokens == 8192


class TestConsoulConfig:
    """Tests for ConsoulConfig."""

    def test_valid_config(self):
        """Test creating a valid Consoul configuration."""
        config = ConsoulConfig(
            profiles={
                "default": ProfileConfig(
                    name="default",
                    description="Default profile",
                    model=ModelConfig(provider=Provider.OPENAI, model="gpt-4o"),
                )
            },
            active_profile="default",
        )
        assert "default" in config.profiles
        assert config.active_profile == "default"
        assert config.get_active_profile().name == "default"

    def test_active_profile_validation(self):
        """Test that active profile must exist in profiles."""
        with pytest.raises(ValidationError) as exc_info:
            ConsoulConfig(
                profiles={
                    "default": ProfileConfig(
                        name="default",
                        description="Default",
                        model=ModelConfig(provider=Provider.OPENAI, model="gpt-4o"),
                    )
                },
                active_profile="nonexistent",
            )
        assert "not found in profiles" in str(exc_info.value)

    def test_active_profile_normalization(self):
        """Test that active profile name is normalized."""
        config = ConsoulConfig(
            profiles={
                "default": ProfileConfig(
                    name="default",
                    description="Default",
                    model=ModelConfig(provider=Provider.OPENAI, model="gpt-4o"),
                )
            },
            active_profile="Default",
        )
        assert config.active_profile == "default"

    def test_api_keys_not_serialized(self):
        """Test that API keys are not included in JSON serialization."""
        config = ConsoulConfig(
            profiles={
                "default": ProfileConfig(
                    name="default",
                    description="Default",
                    model=ModelConfig(provider=Provider.OPENAI, model="gpt-4o"),
                )
            },
            active_profile="default",
            api_keys={"openai": "sk-test-key"},
        )

        # Serialize to JSON
        json_str = config.model_dump_json()
        data = json.loads(json_str)

        # API keys should not be in serialized output
        assert "api_keys" not in data

    def test_global_settings_extensibility(self):
        """Test that global_settings allows arbitrary data."""
        config = ConsoulConfig(
            profiles={
                "default": ProfileConfig(
                    name="default",
                    description="Default",
                    model=ModelConfig(provider=Provider.OPENAI, model="gpt-4o"),
                )
            },
            active_profile="default",
            global_settings={"custom_key": "custom_value", "number": 42},
        )
        assert config.global_settings["custom_key"] == "custom_value"
        assert config.global_settings["number"] == 42

    def test_get_active_profile(self):
        """Test getting the active profile."""
        default_profile = ProfileConfig(
            name="default",
            description="Default",
            model=ModelConfig(provider=Provider.OPENAI, model="gpt-4o"),
        )
        fast_profile = ProfileConfig(
            name="fast",
            description="Fast responses",
            model=ModelConfig(provider=Provider.OPENAI, model="gpt-3.5-turbo"),
        )

        config = ConsoulConfig(
            profiles={"default": default_profile, "fast": fast_profile},
            active_profile="fast",
        )

        active = config.get_active_profile()
        assert active.name == "fast"
        assert active.model.model == "gpt-3.5-turbo"

    def test_multiple_profiles(self):
        """Test configuration with multiple profiles."""
        config = ConsoulConfig(
            profiles={
                "default": ProfileConfig(
                    name="default",
                    description="Default",
                    model=ModelConfig(provider=Provider.OPENAI, model="gpt-4o"),
                ),
                "creative": ProfileConfig(
                    name="creative",
                    description="Creative writing",
                    model=ModelConfig(
                        provider=Provider.ANTHROPIC,
                        model="claude-3-5-sonnet-20241022",
                        temperature=1.5,
                    ),
                ),
                "code": ProfileConfig(
                    name="code",
                    description="Code review",
                    model=ModelConfig(
                        provider=Provider.OPENAI,
                        model="gpt-4o",
                        temperature=0.3,
                    ),
                ),
            },
            active_profile="default",
        )

        assert len(config.profiles) == 3
        assert config.profiles["creative"].model.temperature == 1.5
        assert config.profiles["code"].model.temperature == 0.3
