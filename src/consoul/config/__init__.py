"""Configuration module for Consoul.

This module provides Pydantic models and utilities for managing Consoul configuration.
"""

from consoul.config.loader import (
    create_default_config,
    deep_merge,
    find_config_files,
    find_project_config,
    load_config,
    load_yaml_config,
    merge_configs,
    save_config,
)
from consoul.config.models import (
    ConsoulConfig,
    ContextConfig,
    ConversationConfig,
    ModelConfig,
    ProfileConfig,
    Provider,
)

__all__ = [
    # Models
    "ConsoulConfig",
    "ContextConfig",
    "ConversationConfig",
    "ModelConfig",
    "ProfileConfig",
    "Provider",
    # Loader functions
    "create_default_config",
    "deep_merge",
    "find_config_files",
    "find_project_config",
    "load_config",
    "load_yaml_config",
    "merge_configs",
    "save_config",
]
