"""Tests for Pydantic configuration models."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from consoul.config.models import (
    AnthropicModelConfig,
    ConsoulConfig,
    ContextConfig,
    ConversationConfig,
    HuggingFaceModelConfig,
    OllamaModelConfig,
    OpenAIModelConfig,
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
        assert Provider.HUGGINGFACE == "huggingface"


class TestModelConfig:
    """Tests for provider-specific model configs."""

    def test_valid_openai_model_config(self):
        """Test creating a valid OpenAI ModelConfig."""
        config = OpenAIModelConfig(
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
        config = OpenAIModelConfig(model="gpt-4o")
        assert config.temperature == 1.0

    def test_temperature_validation(self):
        """Test temperature must be between 0.0 and 2.0."""
        with pytest.raises(ValidationError) as exc_info:
            OpenAIModelConfig(model="gpt-4o", temperature=-0.1)
        assert "greater than or equal to 0" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            OpenAIModelConfig(model="gpt-4o", temperature=2.1)
        assert "less than or equal to 2" in str(exc_info.value)

    def test_top_p_validation(self):
        """Test top_p must be between 0.0 and 1.0."""
        config = OpenAIModelConfig(model="gpt-4o", top_p=0.9)
        assert config.top_p == 0.9

        with pytest.raises(ValidationError) as exc_info:
            OpenAIModelConfig(model="gpt-4o", top_p=1.1)
        assert "less than or equal to 1" in str(exc_info.value)

    def test_penalty_validation(self):
        """Test frequency and presence penalties must be between -2.0 and 2.0."""
        config = OpenAIModelConfig(
            model="gpt-4o",
            frequency_penalty=1.5,
            presence_penalty=-1.5,
        )
        assert config.frequency_penalty == 1.5
        assert config.presence_penalty == -1.5

        with pytest.raises(ValidationError) as exc_info:
            OpenAIModelConfig(model="gpt-4o", frequency_penalty=2.5)
        assert "less than or equal to 2" in str(exc_info.value)

    def test_empty_model_name_validation(self):
        """Test that empty model name is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            OpenAIModelConfig(model="")
        assert "Model name cannot be empty" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            OpenAIModelConfig(model="   ")
        assert "Model name cannot be empty" in str(exc_info.value)

    def test_model_name_stripped(self):
        """Test that model name is stripped of whitespace."""
        config = OpenAIModelConfig(model="  gpt-4o  ")
        assert config.model == "gpt-4o"

    def test_ollama_no_penalties(self):
        """Test that Ollama config doesn't have penalty parameters."""
        # Ollama config shouldn't have penalty fields
        config = OllamaModelConfig(model="llama3")
        assert not hasattr(config, "frequency_penalty")
        assert not hasattr(config, "presence_penalty")

    def test_anthropic_has_top_k(self):
        """Test that Anthropic config has top_k parameter."""
        config = AnthropicModelConfig(
            model="claude-3-5-sonnet-20241022",
            top_k=40,
        )
        assert config.top_k == 40

    def test_openai_no_top_k(self):
        """Test that OpenAI config doesn't have top_k parameter."""
        # OpenAI config shouldn't have top_k field
        config = OpenAIModelConfig(model="gpt-4o")
        assert not hasattr(config, "top_k")

    def test_stop_sequences(self):
        """Test stop sequences configuration."""
        config = OpenAIModelConfig(
            model="gpt-4o",
            stop_sequences=["END", "STOP"],
        )
        assert config.stop_sequences == ["END", "STOP"]

    def test_extra_fields_forbidden(self):
        """Test that extra fields are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            OpenAIModelConfig(
                model="gpt-4o",
                invalid_field="value",
            )
        assert "Extra inputs are not permitted" in str(exc_info.value)


class TestHuggingFaceModelConfig:
    """Tests for HuggingFaceModelConfig."""

    def test_valid_huggingface_model_config(self):
        """Test creating a valid HuggingFace ModelConfig."""
        config = HuggingFaceModelConfig(
            model="meta-llama/Llama-3.1-8B-Instruct",
            temperature=0.7,
            max_new_tokens=512,
        )
        assert config.provider == Provider.HUGGINGFACE
        assert config.model == "meta-llama/Llama-3.1-8B-Instruct"
        assert config.temperature == 0.7
        assert config.max_new_tokens == 512

    def test_default_task(self):
        """Test default task is text-generation."""
        config = HuggingFaceModelConfig(model="meta-llama/Llama-3.1-8B-Instruct")
        assert config.task == "text-generation"

    def test_task_validation(self):
        """Test task validation with valid values."""
        config = HuggingFaceModelConfig(
            model="meta-llama/Llama-3.1-8B-Instruct",
            task="text2text-generation",
        )
        assert config.task == "text2text-generation"

    def test_invalid_task(self):
        """Test that invalid task raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            HuggingFaceModelConfig(
                model="meta-llama/Llama-3.1-8B-Instruct",
                task="invalid-task",
            )
        assert "Input should be" in str(exc_info.value)

    def test_max_new_tokens_validation(self):
        """Test max_new_tokens validation."""
        config = HuggingFaceModelConfig(
            model="meta-llama/Llama-3.1-8B-Instruct",
            max_new_tokens=1024,
        )
        assert config.max_new_tokens == 1024

        # Test upper bound
        with pytest.raises(ValidationError) as exc_info:
            HuggingFaceModelConfig(
                model="meta-llama/Llama-3.1-8B-Instruct",
                max_new_tokens=5000,
            )
        assert "less than or equal to 4096" in str(exc_info.value)

    def test_repetition_penalty_validation(self):
        """Test repetition_penalty must be between 1.0 and 2.0."""
        config = HuggingFaceModelConfig(
            model="meta-llama/Llama-3.1-8B-Instruct",
            repetition_penalty=1.2,
        )
        assert config.repetition_penalty == 1.2

        with pytest.raises(ValidationError) as exc_info:
            HuggingFaceModelConfig(
                model="meta-llama/Llama-3.1-8B-Instruct",
                repetition_penalty=0.5,
            )
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_do_sample_default(self):
        """Test do_sample defaults to True."""
        config = HuggingFaceModelConfig(model="meta-llama/Llama-3.1-8B-Instruct")
        assert config.do_sample is True

    def test_model_kwargs(self):
        """Test model_kwargs for additional parameters."""
        config = HuggingFaceModelConfig(
            model="meta-llama/Llama-3.1-8B-Instruct",
            model_kwargs={"return_full_text": False, "num_beams": 4},
        )
        assert config.model_kwargs == {"return_full_text": False, "num_beams": 4}

    def test_huggingface_has_top_k_and_top_p(self):
        """Test that HuggingFace config has both top_k and top_p."""
        config = HuggingFaceModelConfig(
            model="meta-llama/Llama-3.1-8B-Instruct",
            top_k=50,
            top_p=0.95,
        )
        assert config.top_k == 50
        assert config.top_p == 0.95

    def test_huggingface_local_defaults(self):
        """Test that local execution defaults to False."""
        config = HuggingFaceModelConfig(model="meta-llama/Llama-3.1-8B-Instruct")
        assert config.local is False
        assert config.device is None
        assert config.quantization is None

    def test_huggingface_local_execution(self):
        """Test local execution configuration."""
        config = HuggingFaceModelConfig(
            model="meta-llama/Llama-3.1-8B-Instruct",
            local=True,
            device="cuda",
        )
        assert config.local is True
        assert config.device == "cuda"

    def test_huggingface_quantization_4bit(self):
        """Test 4-bit quantization configuration."""
        config = HuggingFaceModelConfig(
            model="meta-llama/Llama-3.1-8B-Instruct",
            local=True,
            quantization="4bit",
        )
        assert config.quantization == "4bit"

    def test_huggingface_quantization_8bit(self):
        """Test 8-bit quantization configuration."""
        config = HuggingFaceModelConfig(
            model="meta-llama/Llama-3.1-8B-Instruct",
            local=True,
            quantization="8bit",
        )
        assert config.quantization == "8bit"

    def test_huggingface_invalid_quantization(self):
        """Test that invalid quantization raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            HuggingFaceModelConfig(
                model="meta-llama/Llama-3.1-8B-Instruct",
                local=True,
                quantization="16bit",  # Invalid value
            )
        errors = exc_info.value.errors()
        assert any("quantization" in str(error) for error in errors)


class TestConversationConfig:
    """Tests for ConversationConfig."""

    def test_default_values(self):
        """Test default conversation configuration."""
        config = ConversationConfig()
        assert config.persist is True
        assert config.db_path == Path.home() / ".consoul" / "history.db"
        assert config.auto_resume is False
        assert config.retention_days == 0

    def test_custom_values(self):
        """Test custom conversation configuration."""
        config = ConversationConfig(
            persist=False,
            db_path=Path("/tmp/history.db"),
            auto_resume=True,
            retention_days=30,
        )
        assert config.persist is False
        assert config.db_path == Path("/tmp/history.db")
        assert config.auto_resume is True
        assert config.retention_days == 30

    def test_path_expansion(self):
        """Test that paths are expanded properly."""
        config = ConversationConfig(db_path="~/custom/history.db")
        assert config.db_path == Path.home() / "custom" / "history.db"

    def test_max_history_validation(self):
        """Test retention_days must be non-negative."""
        with pytest.raises(ValidationError) as exc_info:
            ConversationConfig(retention_days=-1)
        assert "greater than or equal to 0" in str(exc_info.value)


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

    def test_context_files_single_string(self):
        """Test that a single string is converted to a list."""
        config = ContextConfig(custom_context_files="~/context.txt")
        assert len(config.custom_context_files) == 1
        assert config.custom_context_files[0] == Path.home() / "context.txt"

    def test_context_files_single_path(self):
        """Test that a single Path is converted to a list."""
        config = ContextConfig(custom_context_files=Path("~/context.txt"))
        assert len(config.custom_context_files) == 1
        assert config.custom_context_files[0] == Path.home() / "context.txt"

    def test_context_files_invalid_type(self):
        """Test that invalid types raise an error."""
        with pytest.raises(ValidationError) as exc_info:
            ContextConfig(custom_context_files=123)
        assert "must be a string, Path, or list/tuple" in str(exc_info.value)

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
            model=OpenAIModelConfig(model="gpt-4o"),
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
            model=OpenAIModelConfig(model="gpt-4o"),
        )
        assert profile.name == "default"

    def test_profile_name_validation(self):
        """Test profile name validation."""
        # Empty name should fail
        with pytest.raises(ValidationError) as exc_info:
            ProfileConfig(
                name="",
                description="Test",
                model=OpenAIModelConfig(model="gpt-4o"),
            )
        assert "cannot be empty" in str(exc_info.value)

        # Invalid characters should fail
        with pytest.raises(ValidationError) as exc_info:
            ProfileConfig(
                name="my profile!",
                description="Test",
                model=OpenAIModelConfig(model="gpt-4o"),
            )
        assert "alphanumeric" in str(exc_info.value)

    def test_profile_with_custom_configs(self):
        """Test profile with custom conversation and context configs."""
        profile = ProfileConfig(
            name="custom",
            description="Custom profile",
            model=OpenAIModelConfig(model="gpt-4o"),
            conversation=ConversationConfig(persist=False),
            context=ContextConfig(max_context_tokens=8192),
        )
        assert profile.conversation.persist is False
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
                    model=OpenAIModelConfig(model="gpt-4o"),
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
                        model=OpenAIModelConfig(model="gpt-4o"),
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
                    model=OpenAIModelConfig(model="gpt-4o"),
                )
            },
            active_profile="Default",
        )
        assert config.active_profile == "default"

    def test_api_keys_not_serialized_json(self):
        """Test that API keys are not included in JSON serialization."""
        from pydantic import SecretStr

        config = ConsoulConfig(
            profiles={
                "default": ProfileConfig(
                    name="default",
                    description="Default",
                    model=OpenAIModelConfig(model="gpt-4o"),
                )
            },
            active_profile="default",
            api_keys={"openai": SecretStr("sk-test-key")},
        )

        # Serialize to JSON
        json_str = config.model_dump_json()
        data = json.loads(json_str)

        # API keys should not be in serialized output
        assert "api_keys" not in data

    def test_api_keys_not_serialized_python(self):
        """Test that API keys are not included in Python dict serialization."""
        from pydantic import SecretStr

        config = ConsoulConfig(
            profiles={
                "default": ProfileConfig(
                    name="default",
                    description="Default",
                    model=OpenAIModelConfig(model="gpt-4o"),
                )
            },
            active_profile="default",
            api_keys={"openai": SecretStr("sk-test-key")},
        )

        # Serialize to Python dict
        data = config.model_dump()

        # API keys should not be in serialized output (mode="wrap" excludes in all modes)
        assert "api_keys" not in data

    def test_global_settings_extensibility(self):
        """Test that global_settings allows arbitrary data."""
        config = ConsoulConfig(
            profiles={
                "default": ProfileConfig(
                    name="default",
                    description="Default",
                    model=OpenAIModelConfig(model="gpt-4o"),
                )
            },
            active_profile="default",
            global_settings={"custom_key": "custom_value", "number": 42},
        )
        assert config.global_settings["custom_key"] == "custom_value"
        assert config.global_settings["number"] == 42

    def test_extra_fields_forbidden(self):
        """Test that unknown top-level fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ConsoulConfig(
                profiles={
                    "default": ProfileConfig(
                        name="default",
                        description="Default",
                        model=OpenAIModelConfig(model="gpt-4o"),
                    )
                },
                active_profile="default",
                unknown_field="should_fail",
            )
        assert "Extra inputs are not permitted" in str(exc_info.value)

    def test_get_active_profile(self):
        """Test getting the active profile."""
        default_profile = ProfileConfig(
            name="default",
            description="Default",
            model=OpenAIModelConfig(model="gpt-4o"),
        )
        fast_profile = ProfileConfig(
            name="fast",
            description="Fast responses",
            model=OpenAIModelConfig(model="gpt-3.5-turbo"),
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
                    model=OpenAIModelConfig(model="gpt-4o"),
                ),
                "creative": ProfileConfig(
                    name="creative",
                    description="Creative writing",
                    model=AnthropicModelConfig(
                        model="claude-3-5-sonnet-20241022",
                        temperature=1.5,
                    ),
                ),
                "code": ProfileConfig(
                    name="code",
                    description="Code review",
                    model=OpenAIModelConfig(
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
