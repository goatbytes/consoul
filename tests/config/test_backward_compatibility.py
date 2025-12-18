"""Tests for backward compatibility with ProfileConfig imports (SOUL-289 Phase 2).

This module tests that old import paths still work with deprecation warnings,
ensuring a smooth migration path for existing code.
"""

import warnings

import pytest

from consoul.config.models import OpenAIModelConfig


class TestProfileConfigImportFromConfigModels:
    """Test importing ProfileConfig from config.models (deprecated)."""

    def test_import_with_deprecation_warning(self):
        """Test that importing ProfileConfig from config.models raises deprecation warning."""
        with pytest.warns(DeprecationWarning) as warning_list:
            from consoul.config.models import ProfileConfig  # noqa: F401

        # Verify warning was raised
        assert len(warning_list) > 0

        # Verify warning message contains migration guidance
        warning_message = str(warning_list[0].message)
        assert "ProfileConfig" in warning_message
        assert "deprecated" in warning_message.lower()
        assert "tui.profiles" in warning_message

    def test_imported_profile_config_is_functional(self):
        """Test that imported ProfileConfig still works correctly."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from consoul.config.models import ProfileConfig

        # Should be able to create a profile
        profile = ProfileConfig(
            name="test",
            description="Test profile",
            model=OpenAIModelConfig(model="gpt-4o"),
        )

        assert profile.name == "test"
        assert profile.description == "Test profile"

    def test_warning_contains_version_info(self):
        """Test that deprecation warning mentions when it will be removed."""
        with pytest.warns(DeprecationWarning) as warning_list:
            from consoul.config.models import ProfileConfig  # noqa: F401

        warning_message = str(warning_list[0].message)
        # Should mention removal version or timeline
        assert "v1.0.0" in warning_message or "removed" in warning_message.lower()


class TestProfileConfigImportFromConfigProfiles:
    """Test importing ProfileConfig from config.profiles (deprecated)."""

    def test_import_with_deprecation_warning(self):
        """Test that importing ProfileConfig from config.profiles raises deprecation warning."""
        with pytest.warns(DeprecationWarning) as warning_list:
            from consoul.config.profiles import ProfileConfig  # noqa: F401

        assert len(warning_list) > 0

        warning_message = str(warning_list[0].message)
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

    def test_get_builtin_profiles_with_deprecation_warning(self):
        """Test that get_builtin_profiles from config.profiles raises deprecation warning."""
        with pytest.warns(DeprecationWarning) as warning_list:
            from consoul.config.profiles import get_builtin_profiles

            # Call the function to ensure it works
            profiles = get_builtin_profiles()

        assert len(warning_list) > 0
        assert isinstance(profiles, dict)
        assert "default" in profiles

    def test_list_available_profiles_with_deprecation_warning(self):
        """Test that list_available_profiles from config.profiles raises deprecation warning."""
        with pytest.warns(DeprecationWarning) as warning_list:
            from consoul.config.loader import load_config
            from consoul.config.profiles import list_available_profiles

            config = load_config(
                global_config_path="/nonexistent/global.yaml",
                project_config_path="/nonexistent/project.yaml",
            )
            profiles = list_available_profiles(config)

        assert len(warning_list) > 0
        assert isinstance(profiles, list)

    def test_get_profile_description_with_deprecation_warning(self):
        """Test that get_profile_description from config.profiles raises deprecation warning."""
        with pytest.warns(DeprecationWarning) as warning_list:
            from consoul.config.loader import load_config
            from consoul.config.profiles import get_profile_description

            config = load_config(
                global_config_path="/nonexistent/global.yaml",
                project_config_path="/nonexistent/project.yaml",
            )
            description = get_profile_description("default", config)

        assert len(warning_list) > 0
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
    """Test that re-exported symbols are the same objects."""

    def test_profile_config_from_different_imports_same_class(self):
        """Test that ProfileConfig from different imports is the same class."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from consoul.config.models import ProfileConfig as ProfileConfig1
            from consoul.config.profiles import ProfileConfig as ProfileConfig2
            from consoul.tui.profiles import ProfileConfig as ProfileConfig3

        # All should be the same class (same identity)
        assert ProfileConfig1 is ProfileConfig3
        assert ProfileConfig2 is ProfileConfig3

    def test_builtin_profiles_from_different_imports_same_function(self):
        """Test that get_builtin_profiles from different imports is the same function."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from consoul.config.profiles import get_builtin_profiles as gbp1
            from consoul.tui.profiles import get_builtin_profiles as gbp2

        # Should be the same function
        assert gbp1 is gbp2


class TestMigrationGuidance:
    """Test that deprecation warnings provide clear migration guidance."""

    def test_config_models_warning_message_quality(self):
        """Test that config.models deprecation warning is helpful."""
        with pytest.warns(DeprecationWarning) as warning_list:
            from consoul.config.models import ProfileConfig  # noqa: F401

        warning_message = str(warning_list[0].message)

        # Should contain:
        # 1. What is deprecated
        assert "ProfileConfig" in warning_message

        # 2. Where to import from instead
        assert "tui.profiles" in warning_message

        # 3. Timeline for removal
        assert (
            "v1.0.0" in warning_message or "will be removed" in warning_message.lower()
        )

    def test_config_profiles_warning_message_quality(self):
        """Test that config.profiles deprecation warning is helpful."""
        with pytest.warns(DeprecationWarning) as warning_list:
            from consoul.config.profiles import get_builtin_profiles  # noqa: F401

        warning_message = str(warning_list[0].message)

        # Should guide users to new location
        assert "tui.profiles" in warning_message
        assert "deprecated" in warning_message.lower()

    def test_warnings_suggest_correct_import_pattern(self):
        """Test that warnings suggest the correct import pattern."""
        with pytest.warns(DeprecationWarning) as warning_list:
            from consoul.config.models import ProfileConfig  # noqa: F401

        warning_message = str(warning_list[0].message)

        # Should suggest: from consoul.tui.profiles import ProfileConfig
        assert "from consoul.tui.profiles import" in warning_message


class TestNoBreakingChanges:
    """Test that existing code continues to work (no breaking changes)."""

    def test_existing_profile_creation_code_works(self):
        """Test that existing profile creation code still works."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
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

    def test_existing_config_loader_code_works(self):
        """Test that existing config loader code still works."""
        from consoul.config.loader import load_config

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)

            # Old code pattern
            config = load_config(
                global_config_path="/nonexistent/global.yaml",
                project_config_path="/nonexistent/project.yaml",
            )

        # Should have profiles from builtin
        assert hasattr(config, "profiles")
        assert "default" in config.profiles


class TestWarningOnlyOncePerModule:
    """Test that deprecation warnings are raised appropriately."""

    def test_multiple_imports_from_same_module(self):
        """Test behavior with multiple imports from deprecated module."""
        # Python's warning system typically shows warnings once per location
        # This test verifies the warning is raised at least once

        with pytest.warns(DeprecationWarning):
            from consoul.config.models import ProfileConfig

        # Second import from same location may or may not warn
        # depending on Python's warning filter state
        # We just verify it doesn't crash
        with warnings.catch_warnings():
            warnings.simplefilter("always", DeprecationWarning)
            from consoul.config.models import ProfileConfig  # noqa: F401


class TestDeprecationWarningCategory:
    """Test that the correct warning category is used."""

    def test_uses_deprecation_warning_not_user_warning(self):
        """Test that DeprecationWarning is used, not UserWarning."""
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            from consoul.config.models import ProfileConfig  # noqa: F401

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
