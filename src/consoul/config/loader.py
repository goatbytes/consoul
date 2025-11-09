"""Configuration loader with YAML support and precedence handling.

This module provides functionality to load, merge, and validate Consoul
configuration from multiple sources with clear precedence rules.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from consoul.config.env import load_env_settings
from consoul.config.models import ConsoulConfig, ProfileConfig
from consoul.config.profiles import get_builtin_profiles


def find_config_files() -> tuple[Path | None, Path | None]:
    """Find global and project config files.

    Returns:
        Tuple of (global_config_path, project_config_path).
        Either or both may be None if not found.
    """
    # Global config in user's home directory
    global_config_path = Path.home() / ".consoul" / "config.yaml"
    global_config: Path | None = (
        global_config_path if global_config_path.exists() else None
    )

    # Project config - search upward from cwd to find .consoul/ or .git/
    project_config = find_project_config()

    return global_config, project_config


def find_project_config() -> Path | None:
    """Find project-specific config by walking up directory tree.

    Searches for .consoul/config.yaml starting from current directory
    and walking up to the git root or filesystem root.

    Returns:
        Path to project config file, or None if not found.
    """
    current = Path.cwd()

    # Walk up the directory tree
    while True:
        # Check for .consoul/config.yaml in current directory
        config_path = current / ".consoul" / "config.yaml"
        if config_path.exists():
            return config_path

        # Check if we've reached a git repository root
        if (current / ".git").exists():
            # Check one more time in this directory
            config_path = current / ".consoul" / "config.yaml"
            if config_path.exists():
                return config_path
            # Don't search beyond git root
            break

        # Move up one directory
        parent = current.parent
        if parent == current:  # Reached filesystem root
            break
        current = parent

    return None


def load_yaml_config(path: Path) -> dict[str, Any]:
    """Load and parse YAML config file.

    Args:
        path: Path to YAML config file.

    Returns:
        Parsed configuration dictionary, or empty dict if file doesn't exist.

    Raises:
        yaml.YAMLError: If YAML syntax is invalid.
        OSError: If file cannot be read.
    """
    if not path or not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as f:
            content = yaml.safe_load(f)
            # Handle empty files
            if content is None:
                return {}
            if not isinstance(content, dict):
                raise ValueError(
                    f"Config file must contain a YAML mapping, got {type(content).__name__}"
                )
            return content
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Invalid YAML in {path}: {e}") from e
    except OSError as e:
        raise OSError(f"Cannot read config file {path}: {e}") from e


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries.

    Args:
        base: Base dictionary (lower precedence).
        override: Override dictionary (higher precedence).

    Returns:
        Merged dictionary. Override values take precedence.
        Nested dicts are recursively merged.
        Lists and other values are replaced, not merged.
    """
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            result[key] = deep_merge(result[key], value)
        else:
            # Replace value (including lists)
            result[key] = value

    return result


def merge_configs(*configs: dict[str, Any]) -> dict[str, Any]:
    """Merge multiple config dictionaries in precedence order.

    Args:
        *configs: Configuration dictionaries in order from lowest to highest precedence.

    Returns:
        Merged configuration dictionary.
    """
    if not configs:
        return {}

    result: dict[str, Any] = {}
    for config in configs:
        if config:  # Skip None or empty dicts
            result = deep_merge(result, config)

    return result


def load_env_config(env_settings: Any | None = None) -> dict[str, Any]:
    """Load configuration from CONSOUL_* environment variables and .env files.

    This function converts EnvSettings into config dict format for merging.
    Supports both environment variables and .env file values.

    Args:
        env_settings: Optional EnvSettings instance. If None, loads fresh settings.

    Returns:
        Configuration dictionary parsed from environment variables and .env files.
    """
    if env_settings is None:
        env_settings = load_env_settings()

    env_config: dict[str, Any] = {}

    # Active profile (CONSOUL_PROFILE)
    if env_settings.consoul_profile:
        env_config["active_profile"] = env_settings.consoul_profile

    # Model configuration overrides
    model_overrides: dict[str, Any] = {}
    if env_settings.consoul_model_provider:
        model_overrides["provider"] = env_settings.consoul_model_provider
    if env_settings.consoul_model_name:
        model_overrides["model"] = env_settings.consoul_model_name
    if env_settings.consoul_temperature is not None:
        model_overrides["temperature"] = env_settings.consoul_temperature
    if env_settings.consoul_max_tokens is not None:
        model_overrides["max_tokens"] = env_settings.consoul_max_tokens

    # If we have model overrides, we need to apply them to the active profile
    # This requires knowing the active profile, which we'll handle in load_config
    if model_overrides:
        env_config["_model_overrides"] = model_overrides

    # Conversation overrides
    conversation_overrides: dict[str, Any] = {}
    if env_settings.consoul_history_file:
        conversation_overrides["history_file"] = env_settings.consoul_history_file

    if conversation_overrides:
        env_config["_conversation_overrides"] = conversation_overrides

    return env_config


def create_default_config() -> dict[str, Any]:
    """Create default configuration with all built-in profiles.

    Returns:
        Default configuration dictionary with all built-in profiles.
    """
    return {
        "profiles": get_builtin_profiles(),
        "active_profile": "default",
        "global_settings": {},
    }


def load_profile(profile_name: str, config: ConsoulConfig) -> ProfileConfig:
    """Load a profile by name from custom or built-in profiles.

    Args:
        profile_name: Name of the profile to load.
        config: ConsoulConfig instance to check for custom profiles.

    Returns:
        ProfileConfig instance.

    Raises:
        KeyError: If the profile doesn't exist.
    """
    # Check custom profiles first (they override built-in)
    if profile_name in config.profiles:
        return config.profiles[profile_name]

    # Fall back to built-in profiles
    builtin = get_builtin_profiles()
    if profile_name in builtin:
        return ProfileConfig(**builtin[profile_name])

    # Profile not found
    available = sorted(set(config.profiles.keys()) | set(builtin.keys()))
    raise KeyError(
        f"Profile '{profile_name}' not found. "
        f"Available profiles: {', '.join(available)}"
    )


def load_config(
    global_config_path: Path | None = None,
    project_config_path: Path | None = None,
    cli_overrides: dict[str, Any] | None = None,
    profile_name: str | None = None,
) -> ConsoulConfig:
    """Load and merge configuration from all sources.

    Precedence order (lowest to highest):
    1. Defaults (built-in profiles + default settings)
    2. Global config (~/.consoul/config.yaml)
    3. Project config (.consoul/config.yaml)
    4. Environment variables (CONSOUL_*)
    5. CLI overrides (passed as argument)

    Args:
        global_config_path: Optional path to global config file.
            If None, searches in default location.
        project_config_path: Optional path to project config file.
            If None, searches upward from cwd.
        cli_overrides: Optional dictionary of CLI argument overrides.
        profile_name: Optional profile name to set as active.
            If provided, sets active_profile after loading.

    Returns:
        Validated ConsoulConfig instance.

    Raises:
        yaml.YAMLError: If config file has invalid YAML syntax.
        ValidationError: If merged config doesn't match schema.
    """
    # 1. Start with defaults
    default_config = create_default_config()

    # 2. Find config files if not provided
    if global_config_path is None or project_config_path is None:
        found_global, found_project = find_config_files()
        if global_config_path is None:
            global_config_path = found_global
        if project_config_path is None:
            project_config_path = found_project

    # 3. Load environment settings (shared for both config and API keys)
    env_settings = load_env_settings()

    # Warn if .env file exists but not in .gitignore
    from consoul.utils.security import warn_if_env_not_ignored

    warn_if_env_not_ignored()

    # 4. Load each config source
    global_config = load_yaml_config(global_config_path) if global_config_path else {}
    project_config = (
        load_yaml_config(project_config_path) if project_config_path else {}
    )
    env_config = load_env_config(env_settings)

    # 5. Determine active profile from precedence chain
    active = (
        profile_name  # CLI has highest precedence
        or env_config.get("active_profile")
        or project_config.get("active_profile")
        or global_config.get("active_profile")
        or default_config.get("active_profile", "default")
    )

    # 6. Apply model and conversation overrides from env vars to the active profile
    env_overrides: dict[str, Any] = {}
    profile_overrides: dict[str, Any] = {}

    if "_model_overrides" in env_config:
        model_overrides = env_config.pop("_model_overrides")
        profile_overrides["model"] = model_overrides

    if "_conversation_overrides" in env_config:
        conversation_overrides = env_config.pop("_conversation_overrides")
        profile_overrides["conversation"] = conversation_overrides

    if profile_overrides:
        env_overrides = {"profiles": {active: profile_overrides}}
        if "active_profile" not in env_config:
            env_overrides["active_profile"] = active

    # 7. Merge in precedence order
    merged = merge_configs(
        default_config,
        global_config,
        project_config,
        env_config,
        env_overrides,
        cli_overrides or {},
    )

    # 8. Set active profile if specified via CLI (highest precedence)
    if profile_name is not None:
        merged["active_profile"] = profile_name

    # 9. Validate with Pydantic and attach env_settings (already loaded)
    config = ConsoulConfig(**merged)
    config.env_settings = env_settings

    return config


def save_config(
    config: ConsoulConfig, path: Path, include_api_keys: bool = False
) -> None:
    """Save configuration to YAML file.

    Args:
        config: ConsoulConfig instance to save.
        path: Path where config file should be saved.
        include_api_keys: Whether to include API keys in output.
            Default False for security. WARNING: Setting this to True
            will expose sensitive API keys in the config file.

    Raises:
        OSError: If file cannot be written.
    """
    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to dict
    config_dict = config.model_dump(mode="json")

    # The serializer removes api_keys, so we need to add them back if requested
    # Warning: This exposes sensitive data!
    if include_api_keys and config.api_keys:
        config_dict["api_keys"] = {
            key: value.get_secret_value() for key, value in config.api_keys.items()
        }

    # Write YAML
    try:
        with path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(
                config_dict,
                f,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
            )
    except OSError as e:
        raise OSError(f"Cannot write config file {path}: {e}") from e
