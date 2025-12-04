"""ProfileEditorModal - Modal for creating and editing configuration profiles."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Input,
    Label,
    Static,
    Switch,
    TabbedContent,
    TabPane,
    TextArea,
)

from consoul.config.models import ProfileConfig

if TYPE_CHECKING:
    from textual.app import ComposeResult

__all__ = ["ProfileEditorModal"]

log = logging.getLogger(__name__)


class ProfileEditorModal(ModalScreen[ProfileConfig | None]):
    """Modal for creating and editing configuration profiles.

    Features:
    - Create new profiles or edit existing custom profiles
    - Tabbed interface for organized settings (Basic, System Prompt, Conversation, Context)
    - Pydantic validation on save
    - Protection against editing built-in profiles
    - Ctrl+S to save, Escape to cancel
    """

    BINDINGS: ClassVar[list[Binding | tuple[str, str] | tuple[str, str, str]]] = [
        Binding("ctrl+s", "save_profile", "Save", show=True),
        Binding("escape", "cancel", "Cancel", show=True),
    ]

    DEFAULT_CSS = """
    ProfileEditorModal {
        align: center middle;
    }

    ProfileEditorModal > Vertical {
        width: 90;
        height: auto;
        max-height: 90%;
        background: $panel;
        border: thick $primary;
        padding: 1 2;
    }

    ProfileEditorModal .modal-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        color: $text;
        margin: 0 0 1 0;
    }

    ProfileEditorModal TabbedContent {
        width: 100%;
        height: auto;
        max-height: 35;
        background: transparent;
        border: none;
        margin: 0 0 1 0;
    }

    ProfileEditorModal TabPane {
        padding: 1;
    }

    ProfileEditorModal .setting-row {
        width: 100%;
        height: auto;
        layout: horizontal;
        margin: 0 0 1 0;
    }

    ProfileEditorModal .setting-label {
        width: 40%;
        content-align: left middle;
        color: $text;
    }

    ProfileEditorModal .setting-control {
        width: 60%;
        height: auto;
    }

    ProfileEditorModal Input {
        width: 100%;
    }

    ProfileEditorModal #profile-name {
        margin-bottom: 1;
    }

    ProfileEditorModal TextArea {
        width: 100%;
        height: 15;
    }

    ProfileEditorModal Switch {
        width: auto;
    }

    ProfileEditorModal .validation-error {
        width: 100%;
        color: $error;
        text-align: center;
        margin: 0 0 1 0;
        min-height: 1;
    }

    ProfileEditorModal .info-label {
        width: 100%;
        color: $text-muted;
        margin: 0 0 1 0;
        text-align: center;
    }

    ProfileEditorModal .button-container {
        width: 100%;
        height: auto;
        align: center middle;
        layout: horizontal;
        margin: 1 0 0 0;
    }

    ProfileEditorModal Button {
        min-width: 16;
        margin: 0 1;
    }
    """

    def __init__(
        self,
        existing_profile: ProfileConfig | None = None,
        existing_profiles: dict[str, ProfileConfig] | None = None,
        builtin_profile_names: set[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize the profile editor modal.

        Args:
            existing_profile: Profile to edit (None for create mode)
            existing_profiles: Dict of all existing profiles for name validation
            builtin_profile_names: Set of built-in profile names (read-only)
        """
        super().__init__(**kwargs)
        self.existing_profile = existing_profile
        self.existing_profiles = existing_profiles or {}
        self.builtin_profile_names = builtin_profile_names or set()
        self.is_edit_mode = existing_profile is not None
        self.original_name = existing_profile.name if existing_profile else None

        # Check if editing a built-in profile (should be blocked)
        if self.is_edit_mode and self.original_name in self.builtin_profile_names:
            log.warning(
                f"Attempted to edit built-in profile '{self.original_name}' - this should be blocked at UI level"
            )

        log.info(
            f"ProfileEditorModal: mode={'edit' if self.is_edit_mode else 'create'}, "
            f"profile={self.original_name if self.is_edit_mode else 'new'}"
        )

    def compose(self) -> ComposeResult:
        """Compose the modal layout."""
        with Vertical():
            # Title
            title = (
                f"Edit Profile: {self.original_name}"
                if self.is_edit_mode
                else "Create New Profile"
            )
            yield Label(title, classes="modal-title")

            # Validation error display
            yield Static("", id="validation-error", classes="validation-error")

            # Tabbed content for organized settings
            with TabbedContent():
                # Tab 1: Basic Info
                with TabPane("Basic Info", id="basic-tab"):
                    yield Label("Profile Name:", classes="setting-label")
                    yield Input(
                        placeholder="e.g., my-custom-profile",
                        id="profile-name",
                        classes="setting-control",
                    )

                    yield Label("Description:", classes="setting-label")
                    yield Input(
                        placeholder="Brief description of this profile",
                        id="profile-description",
                        classes="setting-control",
                    )

                    yield Label("Model:", classes="setting-label")
                    yield Input(
                        placeholder="e.g., claude-3-5-sonnet-20241022",
                        id="profile-model",
                        classes="setting-control",
                    )

                    yield Label("Temperature:", classes="setting-label")
                    yield Input(
                        placeholder="0.7",
                        id="profile-temperature",
                        classes="setting-control",
                    )

                    if (
                        self.is_edit_mode
                        and self.original_name in self.builtin_profile_names
                    ):
                        yield Label(
                            "⚠ Built-in profiles cannot be modified",
                            classes="validation-error",
                        )

                # Tab 2: System Prompt
                with TabPane("System Prompt", id="prompt-tab"):
                    yield Label(
                        "Custom system prompt (optional, supports markdown):",
                        classes="info-label",
                    )
                    yield TextArea(
                        id="system-prompt",
                        language="markdown",
                    )

                # Tab 3: Conversation Settings
                with TabPane("Conversation", id="conversation-tab"):
                    # Persist
                    with Horizontal(classes="setting-row"):
                        yield Label("Enable Persistence:", classes="setting-label")
                        with Vertical(classes="setting-control"):
                            yield Switch(id="conv-persist", value=True)

                    # DB Path
                    with Horizontal(classes="setting-row"):
                        yield Label("Database Path:", classes="setting-label")
                        with Vertical(classes="setting-control"):
                            yield Input(
                                placeholder="~/.consoul/history.db",
                                value="~/.consoul/history.db",
                                id="conv-db-path",
                            )

                    # Auto Resume
                    with Horizontal(classes="setting-row"):
                        yield Label("Auto Resume:", classes="setting-label")
                        with Vertical(classes="setting-control"):
                            yield Switch(id="conv-auto-resume", value=False)

                    # Retention Days
                    with Horizontal(classes="setting-row"):
                        yield Label(
                            "Retention Days (0=disabled):", classes="setting-label"
                        )
                        with Vertical(classes="setting-control"):
                            yield Input(
                                placeholder="0",
                                id="conv-retention-days",
                                type="integer",
                            )

                    # Summarize
                    with Horizontal(classes="setting-row"):
                        yield Label("Auto Summarize:", classes="setting-label")
                        with Vertical(classes="setting-control"):
                            yield Switch(id="conv-summarize", value=False)

                    # Summarize Threshold
                    with Horizontal(classes="setting-row"):
                        yield Label("Summarize Threshold:", classes="setting-label")
                        with Vertical(classes="setting-control"):
                            yield Input(
                                placeholder="20",
                                id="conv-summarize-threshold",
                                type="integer",
                            )

                    # Keep Recent
                    with Horizontal(classes="setting-row"):
                        yield Label("Keep Recent Messages:", classes="setting-label")
                        with Vertical(classes="setting-control"):
                            yield Input(
                                placeholder="10",
                                id="conv-keep-recent",
                                type="integer",
                            )

                    # Summary Model
                    with Horizontal(classes="setting-row"):
                        yield Label(
                            "Summary Model (optional):", classes="setting-label"
                        )
                        with Vertical(classes="setting-control"):
                            yield Input(
                                placeholder="gpt-4o-mini",
                                id="conv-summary-model",
                            )

                # Tab 4: Context Settings
                with TabPane("Context", id="context-tab"):
                    # Max Context Tokens
                    with Horizontal(classes="setting-row"):
                        yield Label("Max Context Tokens:", classes="setting-label")
                        with Vertical(classes="setting-control"):
                            yield Input(
                                placeholder="4096",
                                id="ctx-max-tokens",
                                type="integer",
                            )

                    # Include System Info
                    with Horizontal(classes="setting-row"):
                        yield Label("Include System Info:", classes="setting-label")
                        with Vertical(classes="setting-control"):
                            yield Switch(id="ctx-system-info", value=True)

                    # Include Git Info
                    with Horizontal(classes="setting-row"):
                        yield Label("Include Git Info:", classes="setting-label")
                        with Vertical(classes="setting-control"):
                            yield Switch(id="ctx-git-info", value=True)

            # Info label
            yield Label(
                "Ctrl+S: save · Escape: cancel",
                classes="info-label",
            )

            # Action buttons
            with Horizontal(classes="button-container"):
                yield Button("Save", variant="primary", id="save-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    async def on_mount(self) -> None:
        """Populate fields if editing an existing profile."""
        if self.is_edit_mode and self.existing_profile:
            self._populate_fields(self.existing_profile)

        # Focus the name input
        name_input = self.query_one("#profile-name", Input)
        name_input.focus()

    def _populate_fields(self, profile: ProfileConfig) -> None:
        """Populate form fields with profile data.

        Args:
            profile: Profile to load into form
        """
        # Basic Info
        self.query_one("#profile-name", Input).value = profile.name
        self.query_one("#profile-description", Input).value = profile.description
        self.query_one("#profile-model", Input).value = profile.model.model
        self.query_one("#profile-temperature", Input).value = str(
            profile.model.temperature
        )

        # System Prompt
        if profile.system_prompt:
            self.query_one("#system-prompt", TextArea).text = profile.system_prompt

        # Conversation Settings
        self.query_one("#conv-persist", Switch).value = profile.conversation.persist
        self.query_one("#conv-db-path", Input).value = (
            str(profile.conversation.db_path) if profile.conversation.db_path else ""
        )
        self.query_one(
            "#conv-auto-resume", Switch
        ).value = profile.conversation.auto_resume
        self.query_one("#conv-retention-days", Input).value = str(
            profile.conversation.retention_days
        )
        self.query_one("#conv-summarize", Switch).value = profile.conversation.summarize
        self.query_one("#conv-summarize-threshold", Input).value = str(
            profile.conversation.summarize_threshold
        )
        self.query_one("#conv-keep-recent", Input).value = str(
            profile.conversation.keep_recent
        )
        if profile.conversation.summary_model:
            self.query_one(
                "#conv-summary-model", Input
            ).value = profile.conversation.summary_model

        # Context Settings
        self.query_one("#ctx-max-tokens", Input).value = str(
            profile.context.max_context_tokens
        )
        self.query_one(
            "#ctx-system-info", Switch
        ).value = profile.context.include_system_info
        self.query_one("#ctx-git-info", Switch).value = profile.context.include_git_info

        log.debug(f"ProfileEditorModal: Populated fields for profile '{profile.name}'")

    def _collect_form_data(self) -> dict[str, Any]:
        """Collect all form field values into a dictionary.

        Returns:
            Dictionary with profile data suitable for ProfileConfig creation
        """
        # Basic Info
        name = self.query_one("#profile-name", Input).value.strip()
        description = self.query_one("#profile-description", Input).value.strip()
        model_name = self.query_one("#profile-model", Input).value.strip()
        temperature_str = self.query_one("#profile-temperature", Input).value.strip()

        # System Prompt
        system_prompt_text = self.query_one("#system-prompt", TextArea).text.strip()
        system_prompt = system_prompt_text if system_prompt_text else None

        # Conversation Settings
        db_path_value = self.query_one("#conv-db-path", Input).value.strip()
        summary_model_value = self.query_one("#conv-summary-model", Input).value.strip()

        conversation = {
            "persist": self.query_one("#conv-persist", Switch).value,
            "db_path": db_path_value if db_path_value else None,
            "auto_resume": self.query_one("#conv-auto-resume", Switch).value,
            "retention_days": int(
                self.query_one("#conv-retention-days", Input).value or "0"
            ),
            "summarize": self.query_one("#conv-summarize", Switch).value,
            "summarize_threshold": int(
                self.query_one("#conv-summarize-threshold", Input).value or "20"
            ),
            "keep_recent": int(
                self.query_one("#conv-keep-recent", Input).value or "10"
            ),
            "summary_model": summary_model_value if summary_model_value else None,
        }

        # Context Settings
        context = {
            "max_context_tokens": int(
                self.query_one("#ctx-max-tokens", Input).value or "4096"
            ),
            "include_system_info": self.query_one("#ctx-system-info", Switch).value,
            "include_git_info": self.query_one("#ctx-git-info", Switch).value,
        }

        # Model config - detect provider from model name
        from consoul.providers import detect_provider

        temperature = float(temperature_str) if temperature_str else 0.7
        provider = detect_provider(model_name) if model_name else "anthropic"

        model = {
            "provider": provider,
            "model": model_name or "claude-3-5-sonnet-20241022",
            "temperature": temperature,
        }

        return {
            "name": name,
            "description": description,
            "system_prompt": system_prompt,
            "model": model,
            "conversation": conversation,
            "context": context,
        }

    def _validate_profile(self, profile_data: dict[str, Any]) -> tuple[bool, str]:
        """Validate profile data before saving.

        Args:
            profile_data: Dictionary with profile data

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if editing built-in profile
        if self.is_edit_mode and self.original_name in self.builtin_profile_names:
            return False, "Built-in profiles cannot be modified. Create a copy instead."

        # Check required fields
        if not profile_data["name"]:
            return False, "Profile name is required"

        if not profile_data["description"]:
            return False, "Profile description is required"

        # Check name uniqueness (skip current profile in edit mode)
        profile_name = profile_data["name"]
        if profile_name in self.existing_profiles and (
            not self.is_edit_mode or profile_name != self.original_name
        ):
            return False, f"Profile name '{profile_name}' already exists"

        # Check if trying to use a built-in name
        if profile_name in self.builtin_profile_names and not self.is_edit_mode:
            return False, f"Cannot use built-in profile name '{profile_name}'"

        # Validate with Pydantic ProfileConfig
        try:
            from consoul.config.models import ProfileConfig

            ProfileConfig(**profile_data)
            return True, ""
        except Exception as e:
            error_msg = str(e)
            # Clean up Pydantic validation error messages
            if "validation error" in error_msg.lower():
                # Extract just the field error message
                lines = error_msg.split("\n")
                if len(lines) > 1:
                    error_msg = lines[1].strip()
            return False, error_msg

    def action_save_profile(self) -> None:
        """Handle save action (Ctrl+S or Save button)."""
        # Collect form data
        profile_data = self._collect_form_data()

        # Validate
        is_valid, error_msg = self._validate_profile(profile_data)

        if not is_valid:
            # Show validation error
            error_label = self.query_one("#validation-error", Static)
            error_label.update(f"⚠ {error_msg}")
            log.warning(f"ProfileEditorModal: Validation failed - {error_msg}")
            return

        # Create ProfileConfig instance
        try:
            from consoul.config.models import ProfileConfig

            profile = ProfileConfig(**profile_data)

            log.info(
                f"ProfileEditorModal: Saving profile '{profile.name}' "
                f"(mode={'edit' if self.is_edit_mode else 'create'})"
            )

            # Return the profile (parent will handle saving to config)
            self.dismiss(profile)

        except Exception as e:
            error_label = self.query_one("#validation-error", Static)
            error_label.update(f"⚠ Failed to create profile: {e}")
            log.error(
                f"ProfileEditorModal: Failed to create profile - {e}", exc_info=True
            )

    def action_cancel(self) -> None:
        """Handle cancel action (Escape or Cancel button)."""
        log.info("ProfileEditorModal: Cancel action")
        self.dismiss(None)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "save-btn":
            self.action_save_profile()
        elif event.button.id == "cancel-btn":
            self.action_cancel()
