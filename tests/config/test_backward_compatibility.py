"""Tests for backward compatibility with ProfileConfig imports (SOUL-289 Phase 2).

This module tests that old import paths still work with deprecation warnings,
ensuring a smooth migration path for existing code.

Note: The deprecation warning for consoul.config.profiles is emitted at module
import time. Since Python caches modules, subsequent imports in the same process
won't re-emit the warning. Tests that need to verify the warning message should
use importlib to force a fresh import.
"""

import importlib
import sys
import warnings

import pytest

from consoul.config.models import OpenAIModelConfig


class TestProfileConfigImportFromConfigModels:
    """Test importing ProfileConfig from config.models.

    Note: config.models.ProfileConfig does NOT emit a deprecation warning.
    It is a valid import path maintained for SDK usage. The TUI-specific
    ProfileConfig is in tui.profiles, but config.models.ProfileConfig
    remains as the SDK-level profile configuration.
    """

    def test_import_without_deprecation_warning(self):
        """Test that importing ProfileConfig from config.models works without warning.

        config.models.ProfileConfig is a valid SDK import path and should not
        emit a deprecation warning. The deprecation warning is only for
        config.profiles (which re-exports from tui.profiles).
        """
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            try:
                from consoul.config.models import ProfileConfig  # noqa: F401

                # Success - no deprecation warning
            except DeprecationWarning:
                pytest.fail(
                    "config.models.ProfileConfig raised DeprecationWarning unexpectedly"
                )

    def test_imported_profile_config_is_functional(self):
        """Test that imported ProfileConfig still works correctly."""
        from consoul.config.models import ProfileConfig

        # Should be able to create a profile
        profile = ProfileConfig(
            name="test",
            description="Test profile",
            model=OpenAIModelConfig(model="gpt-4o"),
        )

        assert profile.name == "test"
        assert profile.description == "Test profile"

    def test_profile_config_class_exists(self):
        """Test that ProfileConfig class is available from config.models."""
        from consoul.config.models import ProfileConfig

        # ProfileConfig should be a valid class
        assert ProfileConfig is not None
        assert hasattr(ProfileConfig, "model_config")


class TestProfileConfigImportFromConfigProfiles:
    """Test importing ProfileConfig from config.profiles (deprecated).

    Note: The deprecation warning is emitted at module load time. Since
    pytest may have already imported the module, we force a fresh import
    for tests that need to capture the warning.
    """

    def test_module_emits_deprecation_warning_on_fresh_import(self):
        """Test that config.profiles module emits deprecation warning on first import."""
        # Remove the module from cache to force fresh import
        mods_to_remove = [
            m for m in list(sys.modules.keys()) if "consoul.config.profiles" in m
        ]
        for m in mods_to_remove:
            del sys.modules[m]

        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always", DeprecationWarning)
            importlib.import_module("consoul.config.profiles")

            # Check for deprecation warning
            deprecation_warnings = [
                w for w in warning_list if issubclass(w.category, DeprecationWarning)
            ]
            assert len(deprecation_warnings) > 0

            warning_message = str(deprecation_warnings[0].message)
            assert "deprecated" in warning_message.lower()
            assert "tui.profiles" in warning_message

    def test_imported_profile_config_is_functional(self):
        """Test that imported ProfileConfig still works correctly."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from consoul.config.profiles import ProfileConfig

        profile = ProfileConfig(
            name="test",
            description="Test profile",
            model=OpenAIModelConfig(model="gpt-4o"),
        )

        assert profile.name == "test"


class TestBuiltinProfilesImportFromConfigProfiles:
    """Test importing builtin profile functions from config.profiles (deprecated)."""

    def test_get_builtin_profiles_functional(self):
        """Test that get_builtin_profiles from config.profiles works."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from consoul.config.profiles import get_builtin_profiles

            profiles = get_builtin_profiles()

        assert isinstance(profiles, dict)
        assert "default" in profiles

    def test_list_available_profiles_functional(self):
        """Test that list_available_profiles from config.profiles works."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from consoul.config.profiles import list_available_profiles

            # Create empty profiles dict (type is ProfileConfig but not needed for test)
            profiles: dict = {}
            profile_names = list_available_profiles(profiles)

        assert isinstance(profile_names, list)
        assert "default" in profile_names

    def test_get_profile_description_functional(self):
        """Test that get_profile_description from config.profiles works."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from consoul.config.profiles import get_profile_description

            # Create empty profiles dict (type is ProfileConfig but not needed for test)
            profiles: dict = {}
            description = get_profile_description("default", profiles)

        assert isinstance(description, str)


class TestCorrectImportPath:
    """Test that importing from tui.profiles does NOT raise warnings."""

    def test_import_from_tui_profiles_no_warning(self):
        """Test that importing from tui.profiles does not raise deprecation warning."""
        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            try:
                from consoul.tui.profiles import (  # noqa: F401
                    ProfileConfig,
                    get_builtin_profiles,
                    get_profile_description,
                    list_available_profiles,
                )
                # Success - no deprecation warning
            except DeprecationWarning:
                pytest.fail(
                    "tui.profiles import raised DeprecationWarning unexpectedly"
                )

    def test_tui_profiles_import_is_functional(self):
        """Test that tui.profiles imports work correctly."""
        from consoul.tui.profiles import (
            ProfileConfig,
            get_builtin_profiles,
        )

        # Create a profile
        profile = ProfileConfig(
            name="test",
            description="Test profile",
            model=OpenAIModelConfig(model="gpt-4o"),
        )

        assert profile.name == "test"

        # Get builtin profiles
        profiles = get_builtin_profiles()
        assert "default" in profiles


class TestReExportsWorkCorrectly:
    """Test that re-exported symbols work correctly.

    Note: config.models.ProfileConfig and tui.profiles.ProfileConfig are
    different classes (not identity-equal). This is by design since they
    serve different purposes (SDK vs TUI). The config.profiles module
    re-exports from tui.profiles.
    """

    def test_config_profiles_reexports_from_tui(self):
        """Test that config.profiles re-exports from tui.profiles."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from consoul.config.profiles import ProfileConfig as ProfileConfig2
            from consoul.tui.profiles import ProfileConfig as ProfileConfig3

        # config.profiles re-exports from tui.profiles, so these should be same
        assert ProfileConfig2 is ProfileConfig3

    def test_builtin_profiles_from_different_imports_same_function(self):
        """Test that get_builtin_profiles from different imports is the same function."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from consoul.config.profiles import get_builtin_profiles as gbp1
            from consoul.tui.profiles import get_builtin_profiles as gbp2

        # Should be the same function
        assert gbp1 is gbp2

    def test_both_profile_configs_are_functional(self):
        """Test that both ProfileConfig classes work correctly."""
        from consoul.config.models import ProfileConfig as SDKProfileConfig
        from consoul.tui.profiles import ProfileConfig as TUIProfileConfig

        # Both should be creatable with same parameters
        sdk_profile = SDKProfileConfig(
            name="sdk-test",
            description="SDK test profile",
            model=OpenAIModelConfig(model="gpt-4o"),
        )
        tui_profile = TUIProfileConfig(
            name="tui-test",
            description="TUI test profile",
            model=OpenAIModelConfig(model="gpt-4o"),
        )

        assert sdk_profile.name == "sdk-test"
        assert tui_profile.name == "tui-test"


class TestMigrationGuidance:
    """Test that deprecation warnings provide clear migration guidance."""

    def test_config_profiles_warning_message_quality(self):
        """Test that config.profiles deprecation warning is helpful."""
        # Force fresh import to capture warning
        mods_to_remove = [
            m for m in list(sys.modules.keys()) if "consoul.config.profiles" in m
        ]
        for m in mods_to_remove:
            del sys.modules[m]

        with warnings.catch_warnings(record=True) as warning_list:
            warnings.simplefilter("always", DeprecationWarning)
            importlib.import_module("consoul.config.profiles")

            deprecation_warnings = [
                w for w in warning_list if issubclass(w.category, DeprecationWarning)
            ]
            assert len(deprecation_warnings) > 0

            warning_message = str(deprecation_warnings[0].message)

            # Should guide users to new location
            assert "tui.profiles" in warning_message
            assert "deprecated" in warning_message.lower()


class TestNoBreakingChanges:
    """Test that existing code continues to work (no breaking changes)."""

    def test_existing_profile_creation_code_works(self):
        """Test that existing profile creation code still works."""
        from consoul.config.models import ProfileConfig

        # Old code pattern should still work
        profile = ProfileConfig(
            name="legacy-profile",
            description="Profile using old import",
            model=OpenAIModelConfig(
                model="gpt-4o",
                temperature=0.7,
            ),
        )

        assert profile.name == "legacy-profile"
        assert profile.model.model == "gpt-4o"

    def test_existing_builtin_profiles_code_works(self):
        """Test that existing builtin profiles code still works."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from consoul.config.profiles import get_builtin_profiles

        profiles = get_builtin_profiles()

        # Old code expecting builtin profiles should work
        assert "default" in profiles
        assert "code-review" in profiles
        assert "creative" in profiles
        assert "fast" in profiles

    def test_config_loader_with_path_objects(self, tmp_path):
        """Test that config loader works with Path objects."""
        from consoul.config.loader import load_config
        from consoul.config.models import ConsoulCoreConfig

        # Create test config files
        global_config = tmp_path / "global.yaml"
        project_config = tmp_path / "project.yaml"
        global_config.touch()
        project_config.touch()

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)

            # Use Path objects (correct usage)
            config = load_config(
                global_config_path=global_config,
                project_config_path=project_config,
            )

        # load_config returns ConsoulCoreConfig (SDK config without TUI profiles)
        # Profiles are TUI-only (ConsoulTuiConfig.profiles)
        assert isinstance(config, ConsoulCoreConfig)
        # Core SDK config has tools and provider settings
        assert hasattr(config, "tools")
        assert hasattr(config, "current_provider")


class TestDeprecationWarningCategory:
    """Test that the correct warning category is used."""

    def test_config_profiles_uses_deprecation_warning(self):
        """Test that config.profiles uses DeprecationWarning."""
        # Force fresh import to capture warning
        mods_to_remove = [
            m for m in list(sys.modules.keys()) if "consoul.config.profiles" in m
        ]
        for m in mods_to_remove:
            del sys.modules[m]

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            importlib.import_module("consoul.config.profiles")

            # Filter for deprecation warnings
            deprecation_warnings = [
                warning
                for warning in w
                if issubclass(warning.category, DeprecationWarning)
            ]

            assert len(deprecation_warnings) > 0
            # Verify it's specifically DeprecationWarning (or subclass)
            assert all(
                issubclass(warning.category, DeprecationWarning)
                for warning in deprecation_warnings
            )
