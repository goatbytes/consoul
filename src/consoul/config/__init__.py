"""Configuration module for Consoul.

This module provides Pydantic models and utilities for managing Consoul configuration.
"""

from typing import Any

from consoul.config.env import (
    EnvSettings,
    get_api_key,
    get_ollama_api_base,
    load_env_settings,
    validate_api_key,
)
from consoul.config.loader import (
    create_default_config,
    deep_merge,
    find_config_files,
    find_project_config,
    load_config,
    load_env_config,
    load_profile,
    load_tui_config,
    load_yaml_config,
    merge_configs,
    save_config,
)
from consoul.config.models import (
    AnthropicModelConfig,
    BaseModelConfig,
    ConsoulConfig,
    ConsoulCoreConfig,
    ContextConfig,
    ConversationConfig,
    GoogleModelConfig,
    ModelConfig,
    OllamaModelConfig,
    OpenAIModelConfig,
    Provider,
)

# Lazy imports for deprecated profile-related items to avoid triggering warnings on module import
# ProfileConfig, get_builtin_profiles, get_profile_description, list_available_profiles
# are available via __getattr__ below

__all__ = [
    "AnthropicModelConfig",
    "BaseModelConfig",
    "ConsoulConfig",
    "ConsoulCoreConfig",
    "ContextConfig",
    "ConversationConfig",
    "EnvSettings",
    "GoogleModelConfig",
    "ModelConfig",
    "OllamaModelConfig",
    "OpenAIModelConfig",
    "ProfileConfig",  # Deprecated, lazy-loaded via __getattr__
    "Provider",
    "create_default_config",
    "deep_merge",
    "find_config_files",
    "find_project_config",
    "get_api_key",
    "get_builtin_profiles",  # Deprecated, lazy-loaded via __getattr__
    "get_ollama_api_base",
    "get_profile_description",  # Deprecated, lazy-loaded via __getattr__
    "list_available_profiles",  # Deprecated, lazy-loaded via __getattr__
    "load_config",
    "load_env_config",
    "load_env_settings",
    "load_profile",
    "load_tui_config",
    "load_yaml_config",
    "merge_configs",
    "save_config",
    "validate_api_key",
]


def __getattr__(name: str) -> Any:
    """Provide lazy imports for deprecated profile-related items.

    This allows the deprecation warnings to only be shown when these items
    are actually used, not when the config module is imported.

    Args:
        name: Attribute name being accessed

    Returns:
        The requested attribute from the appropriate module

    Raises:
        AttributeError: If the attribute doesn't exist
    """
    # Profile-related lazy imports (deprecated)
    if name == "ProfileConfig":
        from consoul.config.models import ProfileConfig as _ProfileConfig

        return _ProfileConfig
    elif name in (
        "get_builtin_profiles",
        "get_profile_description",
        "list_available_profiles",
    ):
        from consoul.config import profiles as _profiles_module

        return getattr(_profiles_module, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
