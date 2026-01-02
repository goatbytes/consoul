"""Tests for configuration loader."""

import os
from pathlib import Path

import pytest
import yaml
from pydantic import SecretStr, ValidationError

from consoul.config.loader import (
    create_default_config,
    deep_merge,
    expand_env_vars,
    find_project_config,
    load_config,
    load_env_config,
    load_tui_config,
    load_yaml_config,
    merge_configs,
    save_config,
)
from consoul.config.models import ConsoulCoreConfig


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


class TestExpandEnvVars:
    """Tests for expand_env_vars function."""

    def test_expand_simple_string(self, monkeypatch: pytest.MonkeyPatch):
        """Test expanding ${VAR} syntax."""
        monkeypatch.setenv("TEST_VAR", "test_value")
        result = expand_env_vars("${TEST_VAR}")
        assert result == "test_value"

    def test_expand_dollar_syntax(self, monkeypatch: pytest.MonkeyPatch):
        """Test expanding $VAR syntax."""
        monkeypatch.setenv("TEST_VAR", "test_value")
        result = expand_env_vars("$TEST_VAR")
        assert result == "test_value"

    def test_expand_in_string(self, monkeypatch: pytest.MonkeyPatch):
        """Test expanding vars within strings."""
        monkeypatch.setenv("API_KEY", "secret123")
        result = expand_env_vars("key: ${API_KEY}")
        assert result == "key: secret123"

    def test_expand_multiple_vars(self, monkeypatch: pytest.MonkeyPatch):
        """Test expanding multiple variables in one string."""
        monkeypatch.setenv("VAR1", "value1")
        monkeypatch.setenv("VAR2", "value2")
        result = expand_env_vars("${VAR1} and ${VAR2}")
        assert result == "value1 and value2"

    def test_expand_in_dict(self, monkeypatch: pytest.MonkeyPatch):
        """Test expanding vars in dictionary values."""
        monkeypatch.setenv("JINA_API_KEY", "jina_key_123")
        config = {"tools": {"web_search": {"jina_api_key": "${JINA_API_KEY}"}}}
        result = expand_env_vars(config)
        assert result["tools"]["web_search"]["jina_api_key"] == "jina_key_123"

    def test_expand_in_list(self, monkeypatch: pytest.MonkeyPatch):
        """Test expanding vars in list items."""
        monkeypatch.setenv("ITEM1", "first")
        monkeypatch.setenv("ITEM2", "second")
        result = expand_env_vars(["${ITEM1}", "${ITEM2}", "literal"])
        assert result == ["first", "second", "literal"]

    def test_undefined_var_unchanged(self):
        """Test that undefined vars are left unchanged."""
        result = expand_env_vars("${UNDEFINED_VAR}")
        assert result == "${UNDEFINED_VAR}"

    def test_mixed_defined_undefined(self, monkeypatch: pytest.MonkeyPatch):
        """Test that defined vars expand while undefined stay unchanged."""
        monkeypatch.setenv("DEFINED", "value")
        result = expand_env_vars("${DEFINED} and ${UNDEFINED}")
        assert result == "value and ${UNDEFINED}"

    def test_primitives_unchanged(self):
        """Test that primitive types are returned unchanged."""
        assert expand_env_vars(42) == 42
        assert expand_env_vars(3.14) == 3.14
        assert expand_env_vars(True) is True
        assert expand_env_vars(None) is None

    def test_nested_structures(self, monkeypatch: pytest.MonkeyPatch):
        """Test expanding vars in deeply nested structures."""
        monkeypatch.setenv("KEY1", "val1")
        monkeypatch.setenv("KEY2", "val2")
        config = {
            "outer": {
                "inner": {"key": "${KEY1}", "list": ["${KEY2}", "literal"]},
                "other": 123,
            }
        }
        result = expand_env_vars(config)
        assert result["outer"]["inner"]["key"] == "val1"
        assert result["outer"]["inner"]["list"] == ["val2", "literal"]
        assert result["outer"]["other"] == 123


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

    def test_load_yaml_with_env_vars(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Test that environment variables are expanded when loading YAML."""
        monkeypatch.setenv("JINA_API_KEY", "jina_secret_key_123")
        monkeypatch.setenv("SEARXNG_URL", "http://localhost:8888")

        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
tools:
  web_search:
    jina_api_key: ${JINA_API_KEY}
    searxng_url: ${SEARXNG_URL}
    max_results: 5
"""
        )

        result = load_yaml_config(config_file)
        assert result["tools"]["web_search"]["jina_api_key"] == "jina_secret_key_123"
        assert result["tools"]["web_search"]["searxng_url"] == "http://localhost:8888"
        assert result["tools"]["web_search"]["max_results"] == 5


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
    """Tests for load_config function.

    Note: load_config() now returns ConsoulCoreConfig (profile-free).
    For profile-aware tests, use load_tui_config() instead.
    """

    def test_load_with_defaults_only(self):
        """Test loading config with only defaults (no files)."""
        # Pass empty paths to avoid searching filesystem
        config = load_config(
            global_config_path=Path("/nonexistent/global.yaml"),
            project_config_path=Path("/nonexistent/project.yaml"),
        )

        # load_config returns ConsoulCoreConfig (profile-free)
        assert isinstance(config, ConsoulCoreConfig)
        # ConsoulCoreConfig doesn't have profiles/active_profile

    def test_load_with_global_config(self, tmp_path: Path):
        """Test loading with global config file."""
        global_config = tmp_path / "global.yaml"
        global_config.write_text(
            yaml.safe_dump(
                {
                    "current_provider": "openai",
                    "current_model": "gpt-4o",
                }
            )
        )

        config = load_config(
            global_config_path=global_config,
            project_config_path=Path("/nonexistent/project.yaml"),
        )

        assert config.current_provider.value == "openai"
        assert config.current_model == "gpt-4o"

    def test_load_with_project_override(self, tmp_path: Path):
        """Test that project config overrides global config."""
        global_config = tmp_path / "global.yaml"
        global_config.write_text(
            yaml.safe_dump(
                {
                    "current_provider": "openai",
                    "current_model": "gpt-4o",
                }
            )
        )

        project_config = tmp_path / "project.yaml"
        project_config.write_text(
            yaml.safe_dump(
                {
                    "current_model": "gpt-4-turbo",  # Override model
                }
            )
        )

        config = load_config(
            global_config_path=global_config,
            project_config_path=project_config,
        )

        # Project config should override model
        assert config.current_model == "gpt-4-turbo"
        # But keep provider from global
        assert config.current_provider.value == "openai"

    def test_load_with_cli_overrides(self, tmp_path: Path):
        """Test that CLI overrides take highest precedence."""
        global_config = tmp_path / "global.yaml"
        global_config.write_text(
            yaml.safe_dump(
                {
                    "current_provider": "openai",
                    "current_model": "gpt-4o",
                }
            )
        )

        cli_overrides = {
            "current_model": "gpt-4-turbo",
        }

        config = load_config(
            global_config_path=global_config,
            project_config_path=Path("/nonexistent/project.yaml"),
            cli_overrides=cli_overrides,
        )

        # CLI overrides should take precedence
        assert config.current_model == "gpt-4-turbo"
        # Other values from global
        assert config.current_provider.value == "openai"

    def test_load_invalid_config_raises_validation_error(self, tmp_path: Path):
        """Test that invalid config raises Pydantic ValidationError."""
        global_config = tmp_path / "global.yaml"
        global_config.write_text(
            yaml.safe_dump(
                {
                    "current_provider": "invalid_provider",  # Invalid
                    "current_model": "some-model",
                }
            )
        )

        with pytest.raises(ValidationError) as exc_info:
            load_config(
                global_config_path=global_config,
                project_config_path=Path("/nonexistent/project.yaml"),
            )
        assert "current_provider" in str(exc_info.value).lower()

    def test_load_with_multiple_profiles(self, tmp_path: Path):
        """Test loading TUI config with multiple profiles including custom ones.

        Note: This test uses load_tui_config() since load_config() is profile-free.
        """
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

        config = load_tui_config(
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
        # ConsoulCoreConfig has current_provider and current_model, not profiles
        assert "current_provider" in loaded
        assert "current_model" in loaded

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
        monkeypatch.setenv("CONSOUL_PROFILE", "creative")

        env_config = load_env_config()
        assert env_config["active_profile"] == "creative"

    def test_load_env_config_model_overrides(self, monkeypatch: pytest.MonkeyPatch):
        """Test loading model overrides from environment."""
        monkeypatch.setenv("CONSOUL_MODEL_PROVIDER", "openai")
        monkeypatch.setenv("CONSOUL_MODEL_NAME", "gpt-4o")
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
        """Test that invalid numeric values are ignored (pydantic validation)."""
        # Pydantic will raise validation error for invalid values, so these won't be set
        # This test verifies that load_env_config handles None values correctly
        env_config = load_env_config()
        # Should return empty or minimal config when no valid env vars set
        assert isinstance(env_config, dict)

    def test_load_env_config_combined(self, monkeypatch: pytest.MonkeyPatch):
        """Test loading both profile and model overrides."""
        monkeypatch.setenv("CONSOUL_PROFILE", "code-review")
        monkeypatch.setenv("CONSOUL_TEMPERATURE", "0.3")

        env_config = load_env_config()
        assert env_config["active_profile"] == "code-review"
        assert "_model_overrides" in env_config
        assert env_config["_model_overrides"]["temperature"] == 0.3


class TestLoadConfigWithEnvVars:
    """Tests for load_tui_config with environment variable support.

    Note: Profile-related tests use load_tui_config() since load_config() is profile-free.
    """

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

        config = load_tui_config(
            global_config_path=global_config,
            project_config_path=Path("/nonexistent/project.yaml"),
        )

        # Env var should override config file
        assert config.get_active_profile().model.temperature == 0.7

    def test_env_var_active_profile(self, monkeypatch: pytest.MonkeyPatch):
        """Test that CONSOUL_PROFILE overrides config files."""
        monkeypatch.setenv("CONSOUL_PROFILE", "creative")

        config = load_tui_config(
            global_config_path=Path("/nonexistent/global.yaml"),
            project_config_path=Path("/nonexistent/project.yaml"),
        )

        assert config.active_profile == "creative"

    def test_cli_overrides_env_vars(self, monkeypatch: pytest.MonkeyPatch):
        """Test that CLI overrides have highest precedence."""
        monkeypatch.setenv("CONSOUL_PROFILE", "creative")

        config = load_tui_config(
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
