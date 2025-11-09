"""Tests for environment variable and .env file support."""

from pathlib import Path

import pytest
from pydantic import SecretStr

from consoul.config.env import (
    EnvSettings,
    get_api_key,
    get_ollama_api_base,
    load_env_settings,
    validate_api_key,
)
from consoul.config.models import Provider


class TestEnvSettings:
    """Tests for EnvSettings class."""

    def test_env_settings_defaults(self, monkeypatch: pytest.MonkeyPatch):
        """Test that EnvSettings has None defaults for API keys."""
        # Clear all API key env vars
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("OLLAMA_API_BASE", raising=False)

        settings = EnvSettings()
        assert settings.anthropic_api_key is None
        assert settings.openai_api_key is None
        assert settings.google_api_key is None
        assert settings.ollama_api_base == "http://localhost:11434"  # Has default value

    def test_env_settings_from_env_vars(self, monkeypatch: pytest.MonkeyPatch):
        """Test loading API keys from environment variables."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test123")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test456")
        monkeypatch.setenv("GOOGLE_API_KEY", "test789")
        monkeypatch.setenv("OLLAMA_API_BASE", "http://localhost:11434")

        settings = EnvSettings()
        assert settings.anthropic_api_key is not None
        assert settings.anthropic_api_key.get_secret_value() == "sk-ant-test123"
        assert settings.openai_api_key is not None
        assert settings.openai_api_key.get_secret_value() == "sk-test456"
        assert settings.google_api_key is not None
        assert settings.google_api_key.get_secret_value() == "test789"
        assert settings.ollama_api_base == "http://localhost:11434"

    def test_env_settings_case_insensitive(self, monkeypatch: pytest.MonkeyPatch):
        """Test that env var names are case insensitive."""
        monkeypatch.setenv("anthropic_api_key", "sk-ant-lowercase")

        settings = EnvSettings()
        assert settings.anthropic_api_key is not None
        assert settings.anthropic_api_key.get_secret_value() == "sk-ant-lowercase"

    def test_env_settings_config_overrides(self, monkeypatch: pytest.MonkeyPatch):
        """Test loading config overrides from env vars."""
        monkeypatch.setenv("CONSOUL_PROFILE", "creative")
        monkeypatch.setenv("CONSOUL_MODEL_NAME", "gpt-4o")
        monkeypatch.setenv("CONSOUL_TEMPERATURE", "0.7")
        monkeypatch.setenv("CONSOUL_MAX_TOKENS", "2048")
        monkeypatch.setenv("CONSOUL_MODEL_PROVIDER", "openai")
        monkeypatch.setenv("CONSOUL_HISTORY_FILE", "~/.consoul/custom-history.json")
        monkeypatch.setenv("CONSOUL_LOG_LEVEL", "DEBUG")

        settings = EnvSettings()
        assert settings.consoul_profile == "creative"
        assert settings.consoul_model_name == "gpt-4o"
        assert settings.consoul_temperature == 0.7
        assert settings.consoul_max_tokens == 2048
        assert settings.consoul_model_provider == "openai"
        assert settings.consoul_history_file == "~/.consoul/custom-history.json"
        assert settings.consoul_log_level == "DEBUG"

    def test_env_settings_from_env_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Test loading settings from .env file."""
        # Clear env vars first
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("CONSOUL_PROFILE", raising=False)

        env_file = tmp_path / ".env"
        env_file.write_text(
            """
ANTHROPIC_API_KEY=sk-ant-from-file
OPENAI_API_KEY=sk-from-file
CONSOUL_PROFILE=fast
"""
        )

        monkeypatch.chdir(tmp_path)
        settings = EnvSettings()

        assert settings.anthropic_api_key is not None
        assert settings.anthropic_api_key.get_secret_value() == "sk-ant-from-file"
        assert settings.openai_api_key is not None
        assert settings.openai_api_key.get_secret_value() == "sk-from-file"
        assert settings.consoul_profile == "fast"

    def test_env_vars_override_env_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Test that environment variables override .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text("ANTHROPIC_API_KEY=sk-ant-from-file")

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-from-env")

        settings = EnvSettings()
        assert settings.anthropic_api_key is not None
        assert settings.anthropic_api_key.get_secret_value() == "sk-ant-from-env"

    def test_env_settings_ignores_extra_fields(self, monkeypatch: pytest.MonkeyPatch):
        """Test that extra environment variables are ignored."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.setenv("RANDOM_VAR", "should-be-ignored")
        monkeypatch.setenv("ANOTHER_VAR", "also-ignored")

        # Should not raise validation error
        settings = EnvSettings()
        assert settings.anthropic_api_key is not None


class TestLoadEnvSettings:
    """Tests for load_env_settings function."""

    def test_load_env_settings_returns_instance(self):
        """Test that load_env_settings returns EnvSettings instance."""
        settings = load_env_settings()
        assert isinstance(settings, EnvSettings)

    def test_load_env_settings_with_api_keys(self, monkeypatch: pytest.MonkeyPatch):
        """Test loading env settings with API keys."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        settings = load_env_settings()
        assert settings.anthropic_api_key is not None
        assert settings.openai_api_key is not None


class TestGetApiKey:
    """Tests for get_api_key function."""

    def test_get_api_key_anthropic(self, monkeypatch: pytest.MonkeyPatch):
        """Test getting Anthropic API key."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test123")

        api_key = get_api_key(Provider.ANTHROPIC)
        assert api_key is not None
        assert isinstance(api_key, SecretStr)
        assert api_key.get_secret_value() == "sk-ant-test123"

    def test_get_api_key_openai(self, monkeypatch: pytest.MonkeyPatch):
        """Test getting OpenAI API key."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test456")

        api_key = get_api_key(Provider.OPENAI)
        assert api_key is not None
        assert api_key.get_secret_value() == "sk-test456"

    def test_get_api_key_google(self, monkeypatch: pytest.MonkeyPatch):
        """Test getting Google API key."""
        monkeypatch.setenv("GOOGLE_API_KEY", "test789")

        api_key = get_api_key(Provider.GOOGLE)
        assert api_key is not None
        assert api_key.get_secret_value() == "test789"

    def test_get_api_key_ollama_returns_none(self):
        """Test that Ollama returns None (uses api_base instead)."""
        api_key = get_api_key(Provider.OLLAMA)
        assert api_key is None

    def test_get_api_key_missing_returns_none(self):
        """Test that missing API key returns None."""
        api_key = get_api_key(Provider.ANTHROPIC)
        assert api_key is None

    def test_get_api_key_with_env_settings(self, monkeypatch: pytest.MonkeyPatch):
        """Test getting API key with provided EnvSettings."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        settings = load_env_settings()

        api_key = get_api_key(Provider.ANTHROPIC, settings)
        assert api_key is not None
        assert api_key.get_secret_value() == "sk-ant-test"

    def test_get_api_key_lazy_loading(self, monkeypatch: pytest.MonkeyPatch):
        """Test that API key is loaded lazily when env_settings is None."""
        # Set env var
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-lazy")

        # Should load fresh settings when None is passed
        api_key = get_api_key(Provider.ANTHROPIC, env_settings=None)
        assert api_key is not None


class TestGetOllamaApiBase:
    """Tests for get_ollama_api_base function."""

    def test_get_ollama_api_base(self, monkeypatch: pytest.MonkeyPatch):
        """Test getting Ollama API base URL."""
        monkeypatch.setenv("OLLAMA_API_BASE", "http://localhost:11434")

        api_base = get_ollama_api_base()
        assert api_base == "http://localhost:11434"

    def test_get_ollama_api_base_default(self):
        """Test that Ollama API base returns default when not set."""
        api_base = get_ollama_api_base()
        assert api_base == "http://localhost:11434"

    def test_get_ollama_api_base_with_env_settings(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Test getting Ollama API base with provided EnvSettings."""
        monkeypatch.setenv("OLLAMA_API_BASE", "http://custom:8080")
        settings = load_env_settings()

        api_base = get_ollama_api_base(settings)
        assert api_base == "http://custom:8080"


class TestValidateApiKey:
    """Tests for validate_api_key function."""

    def test_validate_api_key_valid(self):
        """Test that validation passes with valid API key."""
        api_key = SecretStr("sk-ant-test123")
        # Should not raise
        validate_api_key(Provider.ANTHROPIC, api_key)

    def test_validate_api_key_missing_raises(self):
        """Test that missing API key raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            validate_api_key(Provider.ANTHROPIC, None)

        assert "ANTHROPIC_API_KEY" in str(exc_info.value)
        assert "required" in str(exc_info.value).lower()

    def test_validate_api_key_ollama_passes(self):
        """Test that Ollama doesn't require API key."""
        # Should not raise
        validate_api_key(Provider.OLLAMA, None)

    def test_validate_api_key_error_messages(self):
        """Test that error messages are clear for each provider."""
        providers_to_test = [
            (Provider.ANTHROPIC, "ANTHROPIC_API_KEY"),
            (Provider.OPENAI, "OPENAI_API_KEY"),
            (Provider.GOOGLE, "GOOGLE_API_KEY"),
        ]

        for provider, expected_var_name in providers_to_test:
            with pytest.raises(ValueError) as exc_info:
                validate_api_key(provider, None)

            error_msg = str(exc_info.value)
            assert expected_var_name in error_msg
            assert provider.value in error_msg
            assert "required" in error_msg.lower()


class TestEnvFileIntegration:
    """Integration tests for .env file loading."""

    def test_env_file_in_project_root(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Test loading .env file from project root."""
        env_file = tmp_path / ".env"
        env_file.write_text("ANTHROPIC_API_KEY=sk-ant-project-root")

        monkeypatch.chdir(tmp_path)
        settings = load_env_settings()

        assert settings.anthropic_api_key is not None
        assert settings.anthropic_api_key.get_secret_value() == "sk-ant-project-root"

    def test_env_file_multiple_locations(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Test that .env files can be loaded from multiple locations."""
        # Clear env vars first
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        # Create .env in current directory (project root)
        project_env = tmp_path / ".env"
        project_env.write_text(
            "ANTHROPIC_API_KEY=sk-ant-project\nOPENAI_API_KEY=sk-openai-project"
        )

        monkeypatch.chdir(tmp_path)
        settings = load_env_settings()

        # Should load from project .env
        assert settings.anthropic_api_key is not None
        assert settings.anthropic_api_key.get_secret_value() == "sk-ant-project"

    def test_project_env_overrides_consoul_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Test that project .env overrides ~/.consoul/.env."""
        # Create .env in ~/.consoul/
        consoul_dir = tmp_path / "home" / ".consoul"
        consoul_dir.mkdir(parents=True)
        consoul_env = consoul_dir / ".env"
        consoul_env.write_text("ANTHROPIC_API_KEY=sk-ant-consoul")

        # Create .env in project root
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        project_env = project_dir / ".env"
        project_env.write_text("ANTHROPIC_API_KEY=sk-ant-project")

        # Mock Path.home() to return tmp_path/home
        def mock_home() -> Path:
            return tmp_path / "home"

        monkeypatch.setattr(Path, "home", mock_home)
        monkeypatch.chdir(project_dir)

        settings = load_env_settings()

        # Project .env should take precedence
        assert settings.anthropic_api_key is not None
        assert settings.anthropic_api_key.get_secret_value() == "sk-ant-project"

    def test_empty_env_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Test that empty .env file doesn't cause errors."""
        # Clear env vars first
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        monkeypatch.delenv("OLLAMA_API_BASE", raising=False)

        env_file = tmp_path / ".env"
        env_file.write_text("")

        monkeypatch.chdir(tmp_path)
        settings = load_env_settings()

        assert settings.anthropic_api_key is None
        assert settings.openai_api_key is None
