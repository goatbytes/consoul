"""Tests for configuration loader."""

import os
from pathlib import Path

import pytest
import yaml
from pydantic import SecretStr, ValidationError

from consoul.config.loader import (
    create_default_config,
    deep_merge,
    find_project_config,
    load_config,
    load_env_config,
    load_yaml_config,
    merge_configs,
    save_config,
)
from consoul.config.models import ConsoulConfig


class TestDeepMerge:
    """Tests for deep_merge function."""

    def test_merge_simple_dicts(self):
        """Test merging simple dictionaries."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_merge_nested_dicts(self):
        """Test merging nested dictionaries."""
        base = {"outer": {"inner1": 1, "inner2": 2}}
        override = {"outer": {"inner2": 3, "inner3": 4}}
        result = deep_merge(base, override)
        assert result == {"outer": {"inner1": 1, "inner2": 3, "inner3": 4}}

    def test_merge_replaces_lists(self):
        """Test that lists are replaced, not merged."""
        base = {"items": [1, 2, 3]}
        override = {"items": [4, 5]}
        result = deep_merge(base, override)
        assert result == {"items": [4, 5]}

    def test_merge_deep_nested(self):
        """Test merging deeply nested structures."""
        base = {
            "level1": {
                "level2": {"level3": {"a": 1, "b": 2}},
                "other": "value",
            }
        }
        override = {"level1": {"level2": {"level3": {"b": 99, "c": 3}}}}
        result = deep_merge(base, override)
        assert result["level1"]["level2"]["level3"] == {"a": 1, "b": 99, "c": 3}
        assert result["level1"]["other"] == "value"

    def test_merge_empty_dicts(self):
        """Test merging with empty dictionaries."""
        base = {"a": 1}
        assert deep_merge(base, {}) == {"a": 1}
        assert deep_merge({}, base) == {"a": 1}

    def test_merge_different_types(self):
        """Test that different types replace each other."""
        base = {"key": [1, 2, 3]}
        override = {"key": "string"}
        result = deep_merge(base, override)
        assert result == {"key": "string"}


class TestMergeConfigs:
    """Tests for merge_configs function."""

    def test_merge_no_configs(self):
        """Test merging with no configs."""
        result = merge_configs()
        assert result == {}

    def test_merge_single_config(self):
        """Test merging a single config."""
        config = {"a": 1, "b": 2}
        result = merge_configs(config)
        assert result == config

    def test_merge_multiple_configs(self):
        """Test merging multiple configs in order."""
        config1 = {"a": 1, "b": 2}
        config2 = {"b": 3, "c": 4}
        config3 = {"c": 5, "d": 6}
        result = merge_configs(config1, config2, config3)
        assert result == {"a": 1, "b": 3, "c": 5, "d": 6}

    def test_merge_with_none_configs(self):
        """Test that None configs are skipped."""
        config1 = {"a": 1}
        config2 = None
        config3 = {"b": 2}
        result = merge_configs(config1, config2, config3)
        assert result == {"a": 1, "b": 2}


class TestLoadYamlConfig:
    """Tests for load_yaml_config function."""

    def test_load_valid_yaml(self, tmp_path: Path):
        """Test loading valid YAML file."""
        config_file = tmp_path / "config.yaml"
        config_data = {"profiles": {"default": {"name": "default"}}}
        config_file.write_text(yaml.safe_dump(config_data))

        result = load_yaml_config(config_file)
        assert result == config_data

    def test_load_empty_file(self, tmp_path: Path):
        """Test loading empty YAML file."""
        config_file = tmp_path / "empty.yaml"
        config_file.write_text("")

        result = load_yaml_config(config_file)
        assert result == {}

    def test_load_nonexistent_file(self, tmp_path: Path):
        """Test loading nonexistent file returns empty dict."""
        config_file = tmp_path / "nonexistent.yaml"
        result = load_yaml_config(config_file)
        assert result == {}

    def test_load_invalid_yaml(self, tmp_path: Path):
        """Test loading invalid YAML raises error."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text("{ invalid: yaml: syntax")

        with pytest.raises(yaml.YAMLError) as exc_info:
            load_yaml_config(config_file)
        assert "Invalid YAML" in str(exc_info.value)

    def test_load_non_dict_yaml(self, tmp_path: Path):
        """Test loading YAML that's not a dict raises error."""
        config_file = tmp_path / "list.yaml"
        config_file.write_text("- item1\n- item2")

        with pytest.raises(ValueError) as exc_info:
            load_yaml_config(config_file)
        assert "must contain a YAML mapping" in str(exc_info.value)

    def test_load_none_value(self):
        """Test loading None path returns empty dict."""
        result = load_yaml_config(None)
        assert result == {}


class TestCreateDefaultConfig:
    """Tests for create_default_config function."""

    def test_default_config_structure(self):
        """Test that default config has required structure."""
        config = create_default_config()

        assert "profiles" in config
        assert "default" in config["profiles"]
        assert "active_profile" in config
        assert config["active_profile"] == "default"

    def test_default_profile_has_all_sections(self):
        """Test that default profile has all required sections."""
        config = create_default_config()
        default_profile = config["profiles"]["default"]

        assert "name" in default_profile
        assert "description" in default_profile
        assert "model" in default_profile
        assert "conversation" in default_profile
        assert "context" in default_profile

    def test_default_model_config(self):
        """Test default model configuration."""
        config = create_default_config()
        model_config = config["profiles"]["default"]["model"]

        assert "provider" in model_config
        assert "model" in model_config
        assert "temperature" in model_config


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_with_defaults_only(self):
        """Test loading config with only defaults (no files)."""
        # Pass empty paths to avoid searching filesystem
        config = load_config(
            global_config_path=Path("/nonexistent/global.yaml"),
            project_config_path=Path("/nonexistent/project.yaml"),
        )

        assert isinstance(config, ConsoulConfig)
        assert config.active_profile == "default"
        assert "default" in config.profiles

    def test_load_with_global_config(self, tmp_path: Path):
        """Test loading with global config file."""
        global_config = tmp_path / "global.yaml"
        global_config.write_text(
            yaml.safe_dump(
                {
                    "profiles": {
                        "default": {
                            "name": "default",
                            "description": "Custom global default",
                            "model": {
                                "provider": "openai",
                                "model": "gpt-4o",
                                "temperature": 0.5,
                            },
                        }
                    },
                    "active_profile": "default",
                }
            )
        )

        config = load_config(
            global_config_path=global_config,
            project_config_path=Path("/nonexistent/project.yaml"),
        )

        assert config.profiles["default"].model.provider == "openai"
        assert config.profiles["default"].model.model == "gpt-4o"
        assert config.profiles["default"].model.temperature == 0.5

    def test_load_with_project_override(self, tmp_path: Path):
        """Test that project config overrides global config."""
        global_config = tmp_path / "global.yaml"
        global_config.write_text(
            yaml.safe_dump(
                {
                    "profiles": {
                        "default": {
                            "name": "default",
                            "description": "Global default",
                            "model": {
                                "provider": "openai",
                                "model": "gpt-4o",
                                "temperature": 0.7,
                            },
                        }
                    },
                    "active_profile": "default",
                }
            )
        )

        project_config = tmp_path / "project.yaml"
        project_config.write_text(
            yaml.safe_dump(
                {
                    "profiles": {
                        "default": {
                            "model": {
                                "temperature": 0.3,  # Override just temperature
                            }
                        }
                    }
                }
            )
        )

        config = load_config(
            global_config_path=global_config,
            project_config_path=project_config,
        )

        # Project config should override temperature
        assert config.profiles["default"].model.temperature == 0.3
        # But keep other values from global
        assert config.profiles["default"].model.provider == "openai"
        assert config.profiles["default"].model.model == "gpt-4o"

    def test_load_with_cli_overrides(self, tmp_path: Path):
        """Test that CLI overrides take highest precedence."""
        global_config = tmp_path / "global.yaml"
        global_config.write_text(
            yaml.safe_dump(
                {
                    "profiles": {
                        "default": {
                            "name": "default",
                            "description": "Default",
                            "model": {
                                "provider": "openai",
                                "model": "gpt-4o",
                                "temperature": 0.7,
                            },
                        }
                    },
                    "active_profile": "default",
                }
            )
        )

        cli_overrides = {
            "profiles": {
                "default": {
                    "model": {
                        "temperature": 1.5,
                        "max_tokens": 1000,
                    }
                }
            }
        }

        config = load_config(
            global_config_path=global_config,
            project_config_path=Path("/nonexistent/project.yaml"),
            cli_overrides=cli_overrides,
        )

        # CLI overrides should take precedence
        assert config.profiles["default"].model.temperature == 1.5
        assert config.profiles["default"].model.max_tokens == 1000
        # Other values from global
        assert config.profiles["default"].model.provider == "openai"

    def test_load_invalid_config_raises_validation_error(self, tmp_path: Path):
        """Test that invalid config raises Pydantic ValidationError."""
        global_config = tmp_path / "global.yaml"
        global_config.write_text(
            yaml.safe_dump(
                {
                    "profiles": {
                        "default": {
                            "name": "default",
                            "description": "Default",
                            "model": {
                                "provider": "invalid_provider",  # Invalid
                                "model": "some-model",
                            },
                        }
                    },
                    "active_profile": "default",
                }
            )
        )

        with pytest.raises(ValidationError) as exc_info:
            load_config(
                global_config_path=global_config,
                project_config_path=Path("/nonexistent/project.yaml"),
            )
        assert "provider" in str(exc_info.value).lower()

    def test_load_with_multiple_profiles(self, tmp_path: Path):
        """Test loading config with multiple profiles including custom ones."""
        global_config = tmp_path / "global.yaml"
        global_config.write_text(
            yaml.safe_dump(
                {
                    "profiles": {
                        # Override built-in default profile
                        "default": {
                            "name": "default",
                            "description": "Overridden default profile",
                            "model": {
                                "provider": "anthropic",
                                "model": "claude-3-5-sonnet-20241022",
                                "temperature": 0.8,  # Different from built-in
                            },
                        },
                        # Add custom profile
                        "custom-fast": {
                            "name": "custom-fast",
                            "description": "Custom fast profile",
                            "model": {
                                "provider": "openai",
                                "model": "gpt-3.5-turbo",
                                "temperature": 0.7,
                            },
                        },
                    },
                    "active_profile": "custom-fast",
                }
            )
        )

        config = load_config(
            global_config_path=global_config,
            project_config_path=Path("/nonexistent/project.yaml"),
        )

        # Should have all 4 built-in profiles plus custom-fast (5 total)
        # default is overridden but still counts as 1
        assert len(config.profiles) == 5
        assert "default" in config.profiles
        assert "code-review" in config.profiles
        assert "creative" in config.profiles
        assert "fast" in config.profiles
        assert "custom-fast" in config.profiles
        assert config.active_profile == "custom-fast"

        # Verify default was overridden
        assert config.profiles["default"].model.temperature == 0.8


class TestSaveConfig:
    """Tests for save_config function."""

    def test_save_config_creates_directory(self, tmp_path: Path):
        """Test that save_config creates parent directories."""
        config = load_config(
            global_config_path=Path("/nonexistent/global.yaml"),
            project_config_path=Path("/nonexistent/project.yaml"),
        )

        save_path = tmp_path / "new" / "dir" / "config.yaml"
        save_config(config, save_path)

        assert save_path.exists()
        assert save_path.parent.exists()

    def test_save_config_valid_yaml(self, tmp_path: Path):
        """Test that saved config is valid YAML."""
        config = load_config(
            global_config_path=Path("/nonexistent/global.yaml"),
            project_config_path=Path("/nonexistent/project.yaml"),
        )

        save_path = tmp_path / "config.yaml"
        save_config(config, save_path)

        # Should be able to load it back
        with save_path.open("r") as f:
            loaded = yaml.safe_load(f)

        assert isinstance(loaded, dict)
        assert "profiles" in loaded
        assert "active_profile" in loaded

    def test_save_config_excludes_api_keys(self, tmp_path: Path):
        """Test that API keys are not saved to file by default."""
        config = load_config(
            global_config_path=Path("/nonexistent/global.yaml"),
            project_config_path=Path("/nonexistent/project.yaml"),
        )
        # Add API keys
        config.api_keys["openai"] = SecretStr("sk-test-key")

        save_path = tmp_path / "config.yaml"
        save_config(config, save_path)

        # Load and verify API keys are not present
        with save_path.open("r") as f:
            saved_data = yaml.safe_load(f)

        assert "api_keys" not in saved_data

    def test_save_config_includes_api_keys_when_requested(self, tmp_path: Path):
        """Test that API keys are included when include_api_keys=True."""
        config = load_config(
            global_config_path=Path("/nonexistent/global.yaml"),
            project_config_path=Path("/nonexistent/project.yaml"),
        )
        # Add API keys
        config.api_keys["openai"] = SecretStr("sk-test-key-123")
        config.api_keys["anthropic"] = SecretStr("sk-ant-456")

        save_path = tmp_path / "config.yaml"
        save_config(config, save_path, include_api_keys=True)

        # Load and verify API keys are present
        with save_path.open("r") as f:
            saved_data = yaml.safe_load(f)

        assert "api_keys" in saved_data
        assert saved_data["api_keys"]["openai"] == "sk-test-key-123"
        assert saved_data["api_keys"]["anthropic"] == "sk-ant-456"


class TestLoadEnvConfig:
    """Tests for load_env_config function."""

    def test_load_env_config_empty(self, monkeypatch: pytest.MonkeyPatch):
        """Test loading env config with no environment variables set."""
        # Clear any CONSOUL_* env vars
        for key in list(os.environ.keys()):
            if key.startswith("CONSOUL_"):
                monkeypatch.delenv(key)

        env_config = load_env_config()
        assert env_config == {}

    def test_load_env_config_active_profile(self, monkeypatch: pytest.MonkeyPatch):
        """Test loading active profile from environment."""
        monkeypatch.setenv("CONSOUL_ACTIVE_PROFILE", "creative")

        env_config = load_env_config()
        assert env_config["active_profile"] == "creative"

    def test_load_env_config_model_overrides(self, monkeypatch: pytest.MonkeyPatch):
        """Test loading model overrides from environment."""
        monkeypatch.setenv("CONSOUL_PROVIDER", "openai")
        monkeypatch.setenv("CONSOUL_MODEL", "gpt-4o")
        monkeypatch.setenv("CONSOUL_TEMPERATURE", "0.5")
        monkeypatch.setenv("CONSOUL_MAX_TOKENS", "2048")

        env_config = load_env_config()
        assert "_model_overrides" in env_config
        overrides = env_config["_model_overrides"]
        assert overrides["provider"] == "openai"
        assert overrides["model"] == "gpt-4o"
        assert overrides["temperature"] == 0.5
        assert overrides["max_tokens"] == 2048

    def test_load_env_config_invalid_numeric_values(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """Test that invalid numeric values are ignored."""
        monkeypatch.setenv("CONSOUL_TEMPERATURE", "not-a-number")
        monkeypatch.setenv("CONSOUL_MAX_TOKENS", "invalid")

        env_config = load_env_config()
        # Invalid values should be silently ignored
        assert "_model_overrides" not in env_config

    def test_load_env_config_combined(self, monkeypatch: pytest.MonkeyPatch):
        """Test loading both profile and model overrides."""
        monkeypatch.setenv("CONSOUL_ACTIVE_PROFILE", "code-review")
        monkeypatch.setenv("CONSOUL_TEMPERATURE", "0.3")

        env_config = load_env_config()
        assert env_config["active_profile"] == "code-review"
        assert "_model_overrides" in env_config
        assert env_config["_model_overrides"]["temperature"] == 0.3


class TestLoadConfigWithEnvVars:
    """Tests for load_config with environment variable support."""

    def test_env_vars_override_config_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Test that environment variables override config files."""
        # Create global config
        global_config = tmp_path / "global.yaml"
        global_config.write_text(
            yaml.safe_dump(
                {
                    "profiles": {
                        "default": {
                            "name": "default",
                            "description": "Default",
                            "model": {
                                "provider": "anthropic",
                                "model": "claude-3-5-sonnet-20241022",
                                "temperature": 1.0,
                            },
                        }
                    },
                    "active_profile": "default",
                }
            )
        )

        # Set env var to override temperature
        monkeypatch.setenv("CONSOUL_TEMPERATURE", "0.7")
        monkeypatch.chdir(tmp_path)

        config = load_config(
            global_config_path=global_config,
            project_config_path=Path("/nonexistent/project.yaml"),
        )

        # Env var should override config file
        assert config.get_active_profile().model.temperature == 0.7

    def test_env_var_active_profile(self, monkeypatch: pytest.MonkeyPatch):
        """Test that CONSOUL_ACTIVE_PROFILE overrides config files."""
        monkeypatch.setenv("CONSOUL_ACTIVE_PROFILE", "creative")

        config = load_config(
            global_config_path=Path("/nonexistent/global.yaml"),
            project_config_path=Path("/nonexistent/project.yaml"),
        )

        assert config.active_profile == "creative"

    def test_cli_overrides_env_vars(self, monkeypatch: pytest.MonkeyPatch):
        """Test that CLI overrides have highest precedence."""
        monkeypatch.setenv("CONSOUL_ACTIVE_PROFILE", "creative")

        config = load_config(
            global_config_path=Path("/nonexistent/global.yaml"),
            project_config_path=Path("/nonexistent/project.yaml"),
            profile_name="code-review",  # CLI override
        )

        # CLI should win over env var
        assert config.active_profile == "code-review"


class TestFindProjectConfig:
    """Tests for find_project_config function."""

    def test_find_config_in_current_dir(self, tmp_path: Path, monkeypatch):
        """Test finding config in current directory."""
        # Create .consoul/config.yaml in temp directory
        consoul_dir = tmp_path / ".consoul"
        consoul_dir.mkdir()
        config_file = consoul_dir / "config.yaml"
        config_file.write_text("test: config")

        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        result = find_project_config()
        assert result == config_file

    def test_find_config_in_parent_dir(self, tmp_path: Path, monkeypatch):
        """Test finding config in parent directory."""
        # Create .consoul/config.yaml in temp directory
        consoul_dir = tmp_path / ".consoul"
        consoul_dir.mkdir()
        config_file = consoul_dir / "config.yaml"
        config_file.write_text("test: config")

        # Create subdirectory and change to it
        subdir = tmp_path / "subdir" / "nested"
        subdir.mkdir(parents=True)
        monkeypatch.chdir(subdir)

        result = find_project_config()
        assert result == config_file

    def test_find_config_stops_at_git_root(self, tmp_path: Path, monkeypatch):
        """Test that search stops at git repository root."""
        # Create .git directory (simulating git root)
        git_dir = tmp_path / ".git"
        git_dir.mkdir()

        # Create subdirectory
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        monkeypatch.chdir(subdir)

        # No .consoul directory, should stop at git root
        result = find_project_config()
        assert result is None

    def test_find_config_returns_none_if_not_found(self, tmp_path: Path, monkeypatch):
        """Test that None is returned if no config found."""
        monkeypatch.chdir(tmp_path)
        result = find_project_config()
        assert result is None
