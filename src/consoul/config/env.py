"""Environment variable and .env file support for Consoul.

This module provides functionality to load API keys and configuration
from environment variables and .env files using pydantic-settings.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import SecretStr  # noqa: TC002  # Used at runtime in BaseSettings
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from consoul.config.models import Provider


class EnvSettings(BaseSettings):
    """Environment variable settings with .env file support.

    Loads settings from:
    1. .env file in current directory
    2. .env file in ~/.consoul/
    3. Environment variables (highest precedence)

    API keys are stored as SecretStr for security.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", str(Path.home() / ".consoul" / ".env")),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API Keys (SecretStr for security)
    anthropic_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None
    google_api_key: SecretStr | None = None
    ollama_api_base: str = "http://localhost:11434"

    # Configuration overrides (SOUL-19 spec)
    consoul_profile: str | None = None
    consoul_model_provider: str | None = None
    consoul_model_name: str | None = None
    consoul_temperature: float | None = None
    consoul_max_tokens: int | None = None
    consoul_history_file: str | None = None
    consoul_log_level: str = "INFO"


def load_env_settings() -> EnvSettings:
    """Load environment settings from .env files and environment variables.

    Returns:
        EnvSettings instance with loaded values.
    """
    return EnvSettings()


def get_api_key(
    provider: Provider, env_settings: EnvSettings | None = None
) -> SecretStr | None:
    """Get API key for a provider with lazy loading.

    Args:
        provider: The provider to get the API key for.
        env_settings: Optional EnvSettings instance. If None, loads fresh settings.

    Returns:
        SecretStr containing the API key, or None if not found.
    """
    if env_settings is None:
        env_settings = load_env_settings()

    from consoul.config.models import Provider

    if provider == Provider.ANTHROPIC:
        return env_settings.anthropic_api_key
    if provider == Provider.OPENAI:
        return env_settings.openai_api_key
    if provider == Provider.GOOGLE:
        return env_settings.google_api_key
    if provider == Provider.OLLAMA:
        # Ollama uses api_base, not api_key
        return None

    return None


def get_ollama_api_base(env_settings: EnvSettings | None = None) -> str | None:
    """Get Ollama API base URL.

    Args:
        env_settings: Optional EnvSettings instance. If None, loads fresh settings.

    Returns:
        API base URL string, or None if not configured.
    """
    if env_settings is None:
        env_settings = load_env_settings()

    return env_settings.ollama_api_base


def validate_api_key(provider: Provider, api_key: SecretStr | None) -> None:
    """Validate that an API key exists for the provider.

    Args:
        provider: The provider to validate.
        api_key: The API key to validate.

    Raises:
        ValueError: If the API key is missing with a clear error message.
    """
    from consoul.config.models import Provider

    if provider == Provider.OLLAMA:
        # Ollama doesn't require an API key (runs locally)
        return

    if api_key is None:
        env_var_name = _get_env_var_name(provider)
        raise ValueError(
            f"API key for {provider.value} is required but not found. "
            f"Please set {env_var_name} in your environment or .env file."
        )


def _get_env_var_name(provider: Provider) -> str:
    """Get the environment variable name for a provider's API key.

    Args:
        provider: The provider.

    Returns:
        Environment variable name.
    """
    from consoul.config.models import Provider

    if provider == Provider.ANTHROPIC:
        return "ANTHROPIC_API_KEY"
    if provider == Provider.OPENAI:
        return "OPENAI_API_KEY"
    if provider == Provider.GOOGLE:
        return "GOOGLE_API_KEY"
    if provider == Provider.OLLAMA:
        return "OLLAMA_API_BASE"

    return f"{provider.value.upper()}_API_KEY"
