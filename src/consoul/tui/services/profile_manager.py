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
        from consoul.tui.profiles import get_builtin_profiles

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

    # SDK Translation Methods
    # These methods convert ProfileConfig to explicit SDK parameters,
    # enabling profile-free SDK usage while maintaining TUI profile support

    @staticmethod
    def profile_to_sdk_params(profile: Any, config: ConsoulConfig) -> dict[str, Any]:
        """Convert ProfileConfig to explicit SDK parameters.

        This method extracts all relevant settings from a profile and returns
        them as a dictionary compatible with Consoul SDK's __init__ parameters.

        Args:
            profile: ProfileConfig instance to convert
            config: ConsoulConfig for context (provider settings, etc.)

        Returns:
            Dictionary of SDK parameters (model, temperature, system_prompt, etc.)

        Example:
            >>> profile = config.get_active_profile()
            >>> sdk_params = ProfileManager.profile_to_sdk_params(profile, config)
            >>> console = Consoul(**sdk_params)
        """
        params: dict[str, Any] = {}

        # Model configuration
        if profile.model:
            params["model"] = profile.model.model
            if hasattr(profile.model, "temperature"):
                params["temperature"] = profile.model.temperature
            if hasattr(profile.model, "max_tokens") and profile.model.max_tokens:
                params["max_tokens"] = profile.model.max_tokens

        # System prompt (will be enhanced with context by SDK)
        if profile.system_prompt:
            params["system_prompt"] = profile.system_prompt

        # Conversation settings
        params["persist"] = profile.conversation.persist
        if profile.conversation.db_path:
            params["db_path"] = profile.conversation.db_path
        params["summarize"] = profile.conversation.summarize
        params["summarize_threshold"] = profile.conversation.summarize_threshold
        params["keep_recent"] = profile.conversation.keep_recent
        if profile.conversation.summary_model:
            params["summary_model"] = profile.conversation.summary_model

        # Tools enabled by default (SDK handles tool resolution)
        params["tools"] = True

        logger.debug(f"Converted profile '{profile.name}' to SDK params")
        return params

    @staticmethod
    def build_profile_system_prompt(profile: Any, config: ConsoulConfig) -> str:
        """Build complete system prompt from profile with environment context.

        Delegates to SDK's build_enhanced_system_prompt() for consistency.

        Args:
            profile: ProfileConfig with system_prompt and context settings
            config: ConsoulConfig for additional context

        Returns:
            Complete system prompt with environment context and tool documentation

        Example:
            >>> profile = config.get_active_profile()
            >>> prompt = ProfileManager.build_profile_system_prompt(profile, config)
        """
        from consoul.ai.prompt_builder import build_enhanced_system_prompt

        # Use profile's context settings to customize prompt builder
        # Note: custom_context_files from profile.context are handled separately
        # as they need to be read and injected as context_sections
        prompt = build_enhanced_system_prompt(
            base_prompt=profile.system_prompt or "",
            include_os_info=profile.context.include_system_info,
            include_shell_info=profile.context.include_system_info,
            include_directory_info=profile.context.include_system_info,
            include_git_info=profile.context.include_git_info,
            include_datetime_info=True,
            auto_append_tools=True,  # Tools appended at runtime
        )
        return prompt if prompt is not None else ""

    @staticmethod
    def get_conversation_kwargs(profile: Any) -> dict[str, Any]:
        """Extract conversation configuration as kwargs.

        Args:
            profile: ProfileConfig with conversation settings

        Returns:
            Dictionary of conversation kwargs for ConversationService

        Example:
            >>> profile = config.get_active_profile()
            >>> conv_kwargs = ProfileManager.get_conversation_kwargs(profile)
            >>> service = ConversationService(..., **conv_kwargs)
        """
        return {
            "persist": profile.conversation.persist,
            "db_path": profile.conversation.db_path,
            "auto_resume": profile.conversation.auto_resume,
            "retention_days": profile.conversation.retention_days,
            "summarize": profile.conversation.summarize,
            "summarize_threshold": profile.conversation.summarize_threshold,
            "keep_recent": profile.conversation.keep_recent,
            "summary_model": profile.conversation.summary_model,
        }

    @staticmethod
    def get_model_name(profile: Any, config: ConsoulConfig) -> str:
        """Get model name from profile or fallback to config default.

        Args:
            profile: ProfileConfig with optional model configuration
            config: ConsoulConfig with current_model fallback

        Returns:
            Model name string

        Example:
            >>> profile = config.get_active_profile()
            >>> model = ProfileManager.get_model_name(profile, config)
        """
        if profile.model and profile.model.model:
            model_name: str = profile.model.model
            return model_name
        return config.current_model
