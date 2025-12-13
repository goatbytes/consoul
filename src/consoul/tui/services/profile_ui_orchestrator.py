"""Profile and Model UI Orchestration Service.

Handles profile and model management UI flows including modals, validation,
and user interaction orchestration for profile CRUD operations and model switching.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

    from consoul.config import ConsoulConfig

logger = logging.getLogger(__name__)

__all__ = ["ProfileUIOrchestrator"]


class ProfileUIOrchestrator:
    """Service for orchestrating profile and model management UI flows.

    Centralizes modal management, form validation, and user interaction
    for profile switching, creation, editing, deletion, and model switching.
    """

    @staticmethod
    def switch_profile(
        app: Any, config: ConsoulConfig | None, profile_name: str
    ) -> None:
        """Switch to a different profile WITHOUT changing model/provider.

        Profiles define HOW to use AI (system prompts, context settings).
        This method updates profile settings while preserving current model.

        Args:
            app: ConsoulApp instance
            config: Consoul configuration
            profile_name: Name of profile to switch to
        """
        if not config:
            app.notify("No configuration available", severity="error")
            return

        try:
            # Get old database path and persist setting before switching
            old_db_path = (
                app.active_profile.conversation.db_path if app.active_profile else None
            )
            old_persist = (
                app.active_profile.conversation.persist if app.active_profile else True
            )

            # Update active profile in config
            config.active_profile = profile_name
            app.active_profile = config.get_active_profile()
            app.current_profile = profile_name

            # Get new persist setting
            assert app.active_profile is not None, (
                "Active profile should be available after switching"
            )
            new_persist = app.active_profile.conversation.persist

            # Persist profile selection to config file
            from consoul.tui.services import ProfileManager

            try:
                ProfileManager.save_profile_config(config)
                logger.info(f"Profile selection saved: {profile_name}")
            except Exception as save_error:
                # Log but don't fail the profile switch - it's already applied in memory
                logger.warning(
                    f"Failed to persist profile selection: {save_error}", exc_info=True
                )

            # NOTE: Model/provider remain unchanged - profiles are separate from models

            # Handle sidebar visibility based on persist setting changes
            assert app.active_profile is not None, (
                "Active profile should be available for db path access"
            )
            new_db_path = app.active_profile.conversation.db_path

            # Case 1: Switching from non-persist to persist profile
            if not old_persist and new_persist:
                # Need to mount sidebar if show_sidebar is enabled
                if app.config.show_sidebar and not hasattr(app, "conversation_list"):
                    from consoul.ai.database import ConversationDatabase
                    from consoul.tui.widgets.conversation_list import ConversationList

                    db = ConversationDatabase(new_db_path)
                    app.conversation_list = ConversationList(db=db)

                    # Mount sidebar in main-container before content-area
                    main_container = app.query_one(".main-container")
                    main_container.mount(app.conversation_list, before=0)

                    logger.info(
                        f"Mounted conversation sidebar for persist-enabled profile '{profile_name}'"
                    )

            # Case 2: Switching from persist to non-persist profile
            elif old_persist and not new_persist:
                # Need to unmount sidebar
                if hasattr(app, "conversation_list"):
                    app.conversation_list.remove()
                    delattr(app, "conversation_list")
                    logger.info(
                        f"Unmounted conversation sidebar for non-persist profile '{profile_name}'"
                    )

            # Case 3: Both profiles have persist=True - check if database path changed
            elif (
                old_persist
                and new_persist
                and old_db_path != new_db_path
                and hasattr(app, "conversation_list")
            ):
                # Database path changed - update conversation list database
                from consoul.ai.database import ConversationDatabase

                app.conversation_list.db = ConversationDatabase(new_db_path)
                # Reload conversations from new database
                app.run_worker(
                    app.conversation_list.reload_conversations(), exclusive=True
                )
                logger.info(
                    f"Switched to profile '{profile_name}' with database: {new_db_path}"
                )

            # Update conversation with new system prompt if needed (with dynamic tools)
            system_prompt = app._build_current_system_prompt()
            if app.conversation and system_prompt:
                # Clear and re-add system message with new prompt
                # (This preserves conversation history but updates instructions)
                app.conversation.clear(preserve_system=False)
                app.conversation.add_system_message(system_prompt)
                # Store updated prompt metadata
                tool_count = (
                    len(app.tool_registry.list_tools(enabled_only=True))
                    if app.tool_registry
                    else 0
                )
                app.conversation.store_system_prompt_metadata(
                    profile_name=app.active_profile.name if app.active_profile else None,
                    tool_count=tool_count,
                )

            # Update top bar display
            app._update_top_bar_state()

            app.notify(
                f"Switched to profile '{profile_name}' and saved to config (model unchanged: {app.current_model})",
                severity="information",
            )
            logger.info(
                f"Profile switched and saved: {profile_name}, model preserved: {app.current_model}"
            )

        except Exception as e:
            ProfileUIOrchestrator._handle_profile_error(app, "switch", e)

    @staticmethod
    def show_create_profile_modal(app: Any, config: ConsoulConfig | None) -> None:
        """Show create profile modal and handle profile creation.

        Args:
            app: ConsoulApp instance
            config: Consoul configuration
        """
        if not config:
            app.notify("No configuration available", severity="error")
            return

        def on_profile_created(new_profile: Any | None) -> None:
            """Handle ProfileEditorModal result for creation."""
            if not new_profile or not config:
                return

            try:
                from consoul.tui.services import ProfileManager

                # Validate creation
                is_valid, error = ProfileManager.validate_create(
                    new_profile.name, config.profiles
                )
                if not is_valid and error:
                    app.notify(error, severity="error")
                    return

                # Create profile and save
                ProfileManager.create_profile(config, new_profile)

                app.notify(
                    f"Profile '{new_profile.name}' created successfully",
                    severity="information",
                )
                logger.info(f"Created new profile: {new_profile.name}")

            except Exception as e:
                ProfileUIOrchestrator._handle_profile_error(app, "create", e)

        from consoul.config.profiles import get_builtin_profiles
        from consoul.tui.widgets import ProfileEditorModal

        builtin_names = set(get_builtin_profiles().keys())

        modal = ProfileEditorModal(
            existing_profile=None,  # Create mode
            existing_profiles=config.profiles,
            builtin_profile_names=builtin_names,
        )
        app.push_screen(modal, on_profile_created)

    @staticmethod
    def show_edit_profile_modal(
        app: Any, config: ConsoulConfig | None, profile_name: str
    ) -> None:
        """Show edit profile modal and handle profile update.

        Args:
            app: ConsoulApp instance
            config: Consoul configuration
            profile_name: Name of profile to edit
        """
        if not config:
            app.notify("No configuration available", severity="error")
            return

        # Get the profile to edit
        if profile_name not in config.profiles:
            app.notify(f"Profile '{profile_name}' not found", severity="error")
            return

        # Validate editing
        from consoul.tui.services import ProfileManager

        is_valid, error = ProfileManager.validate_edit(profile_name)
        if not is_valid and error:
            app.notify(error, severity="error")
            return

        profile_to_edit = config.profiles[profile_name]

        def on_profile_edited(updated_profile: Any | None) -> None:
            """Handle ProfileEditorModal result for editing."""
            if not updated_profile or not config:
                return

            try:
                # Update profile and check if name changed
                name_changed = ProfileManager.update_profile(
                    config, profile_name, updated_profile
                )

                # If name changed and this was current profile, update current_profile
                if name_changed and app.current_profile == profile_name:
                    app.current_profile = updated_profile.name
                    config.active_profile = updated_profile.name

                app.notify(
                    f"Profile '{updated_profile.name}' updated successfully",
                    severity="information",
                )
                logger.info(
                    f"Updated profile: {profile_name} -> {updated_profile.name}"
                )

                # If editing current profile, apply changes
                if app.current_profile == updated_profile.name:
                    app.active_profile = updated_profile
                    app._update_top_bar_state()

            except Exception as e:
                ProfileUIOrchestrator._handle_profile_error(app, "update", e)

        from consoul.config.profiles import get_builtin_profiles
        from consoul.tui.widgets import ProfileEditorModal

        builtin_names = set(get_builtin_profiles().keys())

        modal = ProfileEditorModal(
            existing_profile=profile_to_edit,
            existing_profiles=config.profiles,
            builtin_profile_names=builtin_names,
        )
        app.push_screen(modal, on_profile_edited)

    @staticmethod
    def show_delete_profile_modal(
        app: Any, config: ConsoulConfig | None, profile_name: str
    ) -> None:
        """Show delete profile confirmation modal and handle deletion.

        Args:
            app: ConsoulApp instance
            config: Consoul configuration
            profile_name: Name of profile to delete
        """
        if not config:
            app.notify("No configuration available", severity="error")
            return

        # Check if profile exists
        if profile_name not in config.profiles:
            app.notify(f"Profile '{profile_name}' not found", severity="error")
            return

        # Validate deletion
        from consoul.tui.services import ProfileManager

        is_valid, error = ProfileManager.validate_delete(
            profile_name, app.current_profile
        )
        if not is_valid and error:
            app.notify(error, severity="error")
            return

        # Show confirmation dialog
        def on_confirmed(confirmed: bool | None) -> None:
            """Handle confirmation result."""
            if not confirmed or not config:
                return

            try:
                # Delete profile and save
                ProfileManager.delete_profile(config, profile_name)

                app.notify(
                    f"Profile '{profile_name}' deleted successfully",
                    severity="information",
                )
                logger.info(f"Deleted profile: {profile_name}")

            except Exception as e:
                ProfileUIOrchestrator._handle_profile_error(app, "delete", e)

        # Create confirmation modal
        from textual.screen import ModalScreen
        from textual.widgets import Button, Label

        class ConfirmDeleteModal(ModalScreen[bool]):
            """Simple confirmation modal for profile deletion."""

            def compose(self) -> Any:
                from textual.containers import Horizontal, Vertical

                with Vertical():
                    yield Label(
                        f"Delete profile '{profile_name}'?",
                        id="confirm-label",
                    )
                    yield Label(
                        "This action cannot be undone.",
                        id="warning-label",
                    )
                    with Horizontal():
                        yield Button("Delete", variant="error", id="confirm-btn")
                        yield Button("Cancel", variant="default", id="cancel-btn")

            def on_button_pressed(self, event: Button.Pressed) -> None:
                if event.button.id == "confirm-btn":
                    self.dismiss(True)
                else:
                    self.dismiss(False)

        app.push_screen(ConfirmDeleteModal(), on_confirmed)

    @staticmethod
    def switch_provider_and_model(
        app: Any, config: ConsoulConfig | None, provider: str, model_name: str
    ) -> None:
        """Switch to a different provider and model WITHOUT changing profile.

        Models/providers define WHICH AI to use.
        This method changes the AI backend while preserving profile settings.

        Args:
            app: ConsoulApp instance
            config: Consoul configuration
            provider: Provider to switch to (e.g., "openai", "anthropic")
            model_name: Name of model to switch to
        """
        if not config or not app.model_service:
            app.notify("No configuration available", severity="error")
            return

        try:
            from pathlib import Path

            from consoul.config.loader import find_config_files, save_config

            old_conversation_id = app.conversation_id

            # Switch model via ModelService (handles reinitialization and tool rebinding)
            app.model_service.switch_model(model_name, provider)
            app.chat_model = app.model_service.get_model()
            app.current_model = model_name

            # Persist model selection to config file
            try:
                # Determine which config file to save to
                global_path, project_path = find_config_files()
                save_path: Path | None = (
                    project_path
                    if project_path and project_path.exists()
                    else global_path
                )

                if not save_path:
                    # Default to global config
                    save_path = Path.home() / ".consoul" / "config.yaml"

                # Save updated config (preserves user's model choice)
                save_config(config, save_path, include_api_keys=False)
                logger.info(f"Persisted model selection to {save_path}")
            except Exception as e:
                logger.warning(f"Failed to persist model selection: {e}")
                # Continue even if save fails - model is still switched in memory

            # Preserve conversation by updating model reference
            if app.conversation:
                app.conversation._model = app.chat_model
                app.conversation.model_name = app.current_model

            # Update top bar display
            app._update_top_bar_state()

            app.notify(
                f"Switched to {provider}/{model_name} (profile unchanged: {app.current_profile})",
                severity="information",
            )
            logger.info(
                f"Model/provider switched: {provider}/{model_name}, "
                f"profile preserved: {app.current_profile}, "
                f"conversation preserved: {old_conversation_id}"
            )

        except Exception as e:
            # Disable markup to avoid markup errors from Pydantic validation messages
            error_msg = str(e).replace("[", "\\[")
            app.notify(
                f"Failed to switch model/provider: {error_msg}", severity="error"
            )
            logger.error(f"Model switch failed: {e}", exc_info=True)

    @staticmethod
    def _handle_profile_error(app: Any, operation: str, error: Exception) -> None:
        """Handle profile operation errors with consistent formatting.

        Args:
            app: ConsoulApp instance
            operation: Operation that failed (e.g., "create", "update", "delete", "switch")
            error: Exception that was raised
        """
        # Escape markup characters to avoid formatting errors
        error_msg = str(error).replace("[", "\\[")
        app.notify(f"Failed to {operation} profile: {error_msg}", severity="error")
        logger.error(f"Profile {operation} failed: {error}", exc_info=True)
