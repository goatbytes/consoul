"""Configuration module for Consoul.

This module provides Pydantic models and utilities for managing Consoul configuration.
"""

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
    load_yaml_config,
    merge_configs,
    save_config,
)
from consoul.config.models import (
    AnthropicModelConfig,
    BaseModelConfig,
    ConsoulConfig,
    ContextConfig,
    ConversationConfig,
    GoogleModelConfig,
    ModelConfig,
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

__all__ = [
    "AnthropicModelConfig",
    "BaseModelConfig",
    "ConsoulConfig",
    "ContextConfig",
    "ConversationConfig",
    "EnvSettings",
    "GoogleModelConfig",
    "ModelConfig",
    "OllamaModelConfig",
    "OpenAIModelConfig",
    "ProfileConfig",
    "Provider",
    "create_default_config",
    "deep_merge",
    "find_config_files",
    "find_project_config",
    "get_api_key",
    "get_builtin_profiles",
    "get_ollama_api_base",
    "get_profile_description",
    "list_available_profiles",
    "load_config",
    "load_env_config",
    "load_env_settings",
    "load_profile",
    "load_yaml_config",
    "merge_configs",
    "save_config",
    "validate_api_key",
]
