"""Profile Management Service.

Handles profile configuration persistence, validation, and CRUD operations,
extracting common patterns from profile management handlers.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from consoul.config import ConsoulConfig

logger = logging.getLogger(__name__)

__all__ = ["ProfileManager"]


class ProfileManager:
    """Service for profile configuration management.

    Provides centralized logic for profile validation, persistence, and
    CRUD operations, reducing duplication across profile handlers.
    """

    @staticmethod
    def get_config_save_path() -> Path:
        """Get config file save path.

        Priority: project config > global config > default global path

        Returns:
            Path where config should be saved
        """
        from consoul.config.loader import find_config_files

        global_path, project_path = find_config_files()
        save_path = project_path if project_path else global_path

        if not save_path:
            save_path = Path.home() / ".consoul" / "config.yaml"

        return save_path

    @staticmethod
    def save_profile_config(config: ConsoulConfig) -> None:
        """Save profile configuration to disk.

        Args:
            config: Configuration to save

        Raises:
            Exception: If save fails
        """
        from consoul.config.loader import save_config

        save_path = ProfileManager.get_config_save_path()
        save_config(config, save_path)
        logger.info(f"Saved profile configuration to {save_path}")

    @staticmethod
    def is_builtin_profile(profile_name: str) -> bool:
        """Check if profile is a built-in profile.

        Args:
            profile_name: Name of profile to check

        Returns:
            True if profile is built-in
        """
        from consoul.config.profiles import get_builtin_profiles

        return profile_name in get_builtin_profiles()

    @staticmethod
    def validate_create(
        profile_name: str, existing_profiles: dict[str, Any]
    ) -> tuple[bool, str | None]:
        """Validate profile creation.

        Args:
            profile_name: Name of profile to create
            existing_profiles: Dictionary of existing profiles

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if name conflicts with built-in profile
        if ProfileManager.is_builtin_profile(profile_name):
            return (
                False,
                f"Cannot create profile '{profile_name}': name is reserved for built-in profiles",
            )

        # Check if profile already exists
        if profile_name in existing_profiles:
            return (False, f"Profile '{profile_name}' already exists")

        return (True, None)

    @staticmethod
    def validate_delete(
        profile_name: str, current_profile: str
    ) -> tuple[bool, str | None]:
        """Validate profile deletion.

        Args:
            profile_name: Name of profile to delete
            current_profile: Name of currently active profile

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if it's a built-in profile
        if ProfileManager.is_builtin_profile(profile_name):
            return (False, f"Cannot delete built-in profile '{profile_name}'")

        # Check if it's the current profile
        if profile_name == current_profile:
            return (
                False,
                f"Cannot delete current profile '{profile_name}'. Switch to another profile first.",
            )

        return (True, None)

    @staticmethod
    def validate_edit(profile_name: str) -> tuple[bool, str | None]:
        """Validate profile editing.

        Args:
            profile_name: Name of profile to edit

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if it's a built-in profile
        if ProfileManager.is_builtin_profile(profile_name):
            return (
                False,
                f"Cannot edit built-in profile '{profile_name}'. Create a copy instead.",
            )

        return (True, None)

    @staticmethod
    def create_profile(config: ConsoulConfig, profile: Any) -> None:
        """Create new profile and save to disk.

        Args:
            config: Configuration to update
            profile: Profile object to add

        Raises:
            Exception: If profile creation or save fails
        """
        # Add to config
        config.profiles[profile.name] = profile

        # Save to disk
        ProfileManager.save_profile_config(config)

        logger.info(f"Created profile: {profile.name}")

    @staticmethod
    def update_profile(
        config: ConsoulConfig, old_name: str, updated_profile: Any
    ) -> bool:
        """Update existing profile and save to disk.

        Args:
            config: Configuration to update
            old_name: Original profile name
            updated_profile: Updated profile object

        Returns:
            True if profile name changed, False otherwise

        Raises:
            Exception: If profile update or save fails
        """
        name_changed: bool = updated_profile.name != old_name

        # Remove old profile if name changed
        if name_changed:
            del config.profiles[old_name]

        # Update/add profile
        config.profiles[updated_profile.name] = updated_profile

        # Save to disk
        ProfileManager.save_profile_config(config)

        logger.info(f"Updated profile: {old_name} -> {updated_profile.name}")

        return name_changed

    @staticmethod
    def delete_profile(config: ConsoulConfig, profile_name: str) -> None:
        """Delete profile and save to disk.

        Args:
            config: Configuration to update
            profile_name: Name of profile to delete

        Raises:
            Exception: If profile deletion or save fails
        """
        # Delete from config
        del config.profiles[profile_name]

        # Save to disk
        ProfileManager.save_profile_config(config)

        logger.info(f"Deleted profile: {profile_name}")

    @staticmethod
    def switch_active_profile(config: ConsoulConfig, profile_name: str) -> Any:
        """Switch active profile and save to disk.

        Args:
            config: Configuration to update
            profile_name: Name of profile to switch to

        Returns:
            The newly activated profile object

        Raises:
            Exception: If profile switch or save fails
            KeyError: If profile doesn't exist
        """
        # Update active profile in config
        config.active_profile = profile_name
        active_profile = config.get_active_profile()

        # Save to disk
        ProfileManager.save_profile_config(config)

        logger.info(f"Switched active profile to: {profile_name}")

        return active_profile
