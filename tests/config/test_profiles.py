"""Tests for built-in profiles and profile loading."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from consoul.config.loader import load_config, load_profile
from consoul.config.models import (
    AnthropicModelConfig,
    OllamaModelConfig,
    OpenAIModelConfig,
    ProfileConfig,
    Provider,
)
from consoul.config.profiles import (
    get_builtin_profiles,
    get_profile_description,
    list_available_profiles,
)


class TestGetBuiltinProfiles:
    """Tests for get_builtin_profiles function."""

    def test_returns_dict(self):
        """Test that get_builtin_profiles returns a dictionary."""
        profiles = get_builtin_profiles()
        assert isinstance(profiles, dict)

    def test_contains_required_profiles(self):
        """Test that all required profiles are present."""
        profiles = get_builtin_profiles()
        assert "default" in profiles
        assert "code-review" in profiles
        assert "creative" in profiles
        assert "fast" in profiles

    def test_default_profile_structure(self):
        """Test that default profile has correct structure."""
        profiles = get_builtin_profiles()
        default = profiles["default"]

        assert default["name"] == "default"
        assert "description" in default
        assert default["model"]["provider"] == "anthropic"
        assert default["model"]["model"] == "claude-3-5-sonnet-20241022"
        assert default["model"]["temperature"] == 1.0

    def test_code_review_profile_structure(self):
        """Test that code-review profile has correct structure."""
        profiles = get_builtin_profiles()
        code_review = profiles["code-review"]

        assert code_review["name"] == "code-review"
        assert "description" in code_review
        assert code_review["model"]["provider"] == "openai"
        assert code_review["model"]["model"] == "gpt-4o"
        assert code_review["model"]["temperature"] == 0.3

    def test_creative_profile_structure(self):
        """Test that creative profile has correct structure."""
        profiles = get_builtin_profiles()
        creative = profiles["creative"]

        assert creative["name"] == "creative"
        assert "description" in creative
        assert creative["model"]["provider"] == "anthropic"
        assert creative["model"]["temperature"] == 1.5

    def test_fast_profile_structure(self):
        """Test that fast profile has correct structure."""
        profiles = get_builtin_profiles()
        fast = profiles["fast"]

        assert fast["name"] == "fast"
        assert "description" in fast
        assert fast["model"]["provider"] == "ollama"
        assert fast["model"]["model"] == "llama3"

    def test_all_profiles_validate(self):
        """Test that all built-in profiles validate correctly."""
        profiles = get_builtin_profiles()

        for name, profile_dict in profiles.items():
            # Should not raise ValidationError
            profile = ProfileConfig(**profile_dict)
            assert profile.name == name


class TestListAvailableProfiles:
    """Tests for list_available_profiles function."""

    def test_lists_builtin_profiles_only(self):
        """Test listing when only built-in profiles exist."""
        config = load_config()
        profiles = list_available_profiles(config)

        assert "default" in profiles
        assert "code-review" in profiles
        assert "creative" in profiles
        assert "fast" in profiles

    def test_combines_builtin_and_custom(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Test that custom and built-in profiles are combined."""
        # Create a custom config with a custom profile
        config_dir = tmp_path / ".consoul"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"

        config_file.write_text(
            """
profiles:
  custom-profile:
    name: custom-profile
    description: A custom profile
    model:
      provider: openai
      model: gpt-4o
      temperature: 0.5
active_profile: default
"""
        )

        monkeypatch.chdir(tmp_path)
        config = load_config()
        profiles = list_available_profiles(config)

        assert "default" in profiles
        assert "custom-profile" in profiles

    def test_custom_overrides_builtin_name(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Test that custom profile with same name as built-in appears once."""
        # Create a custom config that overrides "default"
        config_dir = tmp_path / ".consoul"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"

        config_file.write_text(
            """
profiles:
  default:
    name: default
    description: Custom default profile
    model:
      provider: openai
      model: gpt-3.5-turbo
      temperature: 0.8
active_profile: default
"""
        )

        monkeypatch.chdir(tmp_path)
        config = load_config()
        profiles = list_available_profiles(config)

        # "default" should appear only once
        assert profiles.count("default") == 1

    def test_sorted_output(self):
        """Test that profiles are returned in sorted order."""
        config = load_config()
        profiles = list_available_profiles(config)

        assert profiles == sorted(profiles)


class TestGetProfileDescription:
    """Tests for get_profile_description function."""

    def test_builtin_profile_description(self):
        """Test getting description for built-in profile."""
        config = load_config()
        description = get_profile_description("default", config)

        assert isinstance(description, str)
        assert len(description) > 0
        assert "default" in description.lower() or "balanced" in description.lower()

    def test_custom_profile_description(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Test getting description for custom profile."""
        config_dir = tmp_path / ".consoul"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"

        config_file.write_text(
            """
profiles:
  my-profile:
    name: my-profile
    description: My custom description
    model:
      provider: openai
      model: gpt-4o
      temperature: 0.7
active_profile: default
"""
        )

        monkeypatch.chdir(tmp_path)
        config = load_config()
        description = get_profile_description("my-profile", config)

        assert description == "My custom description"

    def test_nonexistent_profile_description(self):
        """Test getting description for nonexistent profile."""
        config = load_config()
        description = get_profile_description("nonexistent", config)

        assert description == "Unknown profile"


class TestLoadProfile:
    """Tests for load_profile function."""

    def test_load_builtin_profile(self):
        """Test loading a built-in profile."""
        config = load_config()
        profile = load_profile("default", config)

        assert isinstance(profile, ProfileConfig)
        assert profile.name == "default"
        assert isinstance(profile.model, AnthropicModelConfig)

    def test_load_all_builtin_profiles(self):
        """Test that all built-in profiles can be loaded."""
        config = load_config()

        for profile_name in ["default", "code-review", "creative", "fast"]:
            profile = load_profile(profile_name, config)
            assert profile.name == profile_name

    def test_load_custom_profile(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Test loading a custom profile from config."""
        config_dir = tmp_path / ".consoul"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"

        config_file.write_text(
            """
profiles:
  my-profile:
    name: my-profile
    description: Custom profile
    model:
      provider: openai
      model: gpt-4o
      temperature: 0.5
active_profile: default
"""
        )

        monkeypatch.chdir(tmp_path)
        config = load_config()
        profile = load_profile("my-profile", config)

        assert profile.name == "my-profile"
        assert isinstance(profile.model, OpenAIModelConfig)
        assert profile.model.temperature == 0.5

    def test_custom_overrides_builtin(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Test that custom profile overrides built-in with same name."""
        config_dir = tmp_path / ".consoul"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"

        config_file.write_text(
            """
profiles:
  default:
    name: default
    description: Overridden default
    model:
      provider: openai
      model: gpt-3.5-turbo
      temperature: 0.8
active_profile: default
"""
        )

        monkeypatch.chdir(tmp_path)
        config = load_config()
        profile = load_profile("default", config)

        # Should get custom profile, not built-in
        assert isinstance(profile.model, OpenAIModelConfig)
        assert profile.model.model == "gpt-3.5-turbo"
        assert profile.model.temperature == 0.8

    def test_nonexistent_profile_raises_key_error(self):
        """Test that loading nonexistent profile raises KeyError."""
        config = load_config()

        with pytest.raises(KeyError) as exc_info:
            load_profile("nonexistent", config)

        assert "nonexistent" in str(exc_info.value)
        assert "not found" in str(exc_info.value)


class TestLoadConfigWithProfile:
    """Tests for load_config with profile_name parameter."""

    def test_load_with_default_profile(self):
        """Test loading config with default profile."""
        config = load_config(profile_name="default")

        assert config.active_profile == "default"
        assert "default" in config.profiles

    def test_load_with_different_profile(self):
        """Test loading config with non-default profile."""
        config = load_config(profile_name="creative")

        assert config.active_profile == "creative"
        active_profile = config.get_active_profile()
        assert active_profile.name == "creative"

    def test_load_with_profile_overrides_config_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Test that profile_name parameter overrides config file."""
        config_dir = tmp_path / ".consoul"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"

        config_file.write_text(
            """
active_profile: fast
"""
        )

        monkeypatch.chdir(tmp_path)
        config = load_config(profile_name="code-review")

        # profile_name should override config file
        assert config.active_profile == "code-review"

    def test_nonexistent_profile_raises_validation_error(self):
        """Test that loading with nonexistent profile raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            load_config(profile_name="nonexistent")

        assert "nonexistent" in str(exc_info.value)


class TestProfileProviderTypes:
    """Tests to verify each profile uses correct provider-specific model config."""

    def test_default_uses_anthropic_config(self):
        """Test that default profile uses AnthropicModelConfig."""
        config = load_config()
        profile = config.get_active_profile()

        assert isinstance(profile.model, AnthropicModelConfig)
        assert profile.model.provider == Provider.ANTHROPIC

    def test_code_review_uses_openai_config(self):
        """Test that code-review profile uses OpenAIModelConfig."""
        config = load_config(profile_name="code-review")
        profile = config.get_active_profile()

        assert isinstance(profile.model, OpenAIModelConfig)
        assert profile.model.provider == Provider.OPENAI

    def test_creative_uses_anthropic_config(self):
        """Test that creative profile uses AnthropicModelConfig."""
        config = load_config(profile_name="creative")
        profile = config.get_active_profile()

        assert isinstance(profile.model, AnthropicModelConfig)
        assert profile.model.provider == Provider.ANTHROPIC

    def test_fast_uses_ollama_config(self):
        """Test that fast profile uses OllamaModelConfig."""
        config = load_config(profile_name="fast")
        profile = config.get_active_profile()

        assert isinstance(profile.model, OllamaModelConfig)
        assert profile.model.provider == Provider.OLLAMA
