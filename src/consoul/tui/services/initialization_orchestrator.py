"""Initialization orchestrator for Consoul TUI app.

This service orchestrates the multi-stage initialization sequence with progress tracking.
Extracted from app.py to reduce complexity and improve maintainability (SOUL-270).
"""

import asyncio
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from consoul.tui.app import ConsoulApp
    from consoul.tui.config import ConsoulTuiConfig

logger = logging.getLogger(__name__)


class InitializationOrchestrator:
    """Orchestrates app initialization with progress tracking."""

    def __init__(self, app: "ConsoulApp") -> None:
        """Initialize orchestrator.

        Args:
            app: The ConsoulApp instance being initialized
        """
        self.app = app

    async def run_initialization_sequence(self, loading_screen: Any | None) -> None:
        """Run the complete initialization sequence.

        Args:
            loading_screen: Loading screen widget for progress updates (may be None)

        Raises:
            Exception: Any initialization error
        """
        import time

        # Give the screen a moment to render (if present)
        if loading_screen:
            await asyncio.sleep(0.05)

        try:
            # Step 1: Load config (10%)
            step_start = time.time()
            await self._update_progress(loading_screen, "Loading configuration...", 10)
            if loading_screen:
                await asyncio.sleep(0.1)  # Ensure loading screen is visible

            consoul_config = await self._load_config()
            logger.info(
                f"[PERF] Step 1 (Load config): {(time.time() - step_start) * 1000:.1f}ms"
            )

            # If no config, skip initialization
            if not consoul_config:
                logger.warning("No configuration available, skipping AI initialization")
                await self._complete_without_config(loading_screen)
                return

            # Set active profile
            await self._set_active_profile(consoul_config)

            # Step 2: Initialize AI model (40%)
            step_start = time.time()
            await self._update_progress(
                loading_screen, "Connecting to AI provider...", 40
            )
            await self._initialize_model(consoul_config)
            logger.info(
                f"[PERF] Step 2 (Initialize AI model): {(time.time() - step_start) * 1000:.1f}ms"
            )

            # Step 3: Create conversation (50%)
            step_start = time.time()
            await self._update_progress(
                loading_screen, "Initializing conversation...", 50
            )
            await self._initialize_conversation(consoul_config)
            logger.info(
                f"[PERF] Step 3 (Create conversation): {(time.time() - step_start) * 1000:.1f}ms"
            )

            # Step 4: Load tools and bind to model (60-80%)
            step_start = time.time()
            await self._update_progress(loading_screen, "Loading tools...", 60)
            await self._initialize_tools(loading_screen, consoul_config)
            logger.info(
                f"[PERF] Step 4 (Load tools & bind): {(time.time() - step_start) * 1000:.1f}ms"
            )

            # Step 5.5: Initialize ConversationService (SDK layer)
            step_start = time.time()
            await self._update_progress(
                loading_screen, "Initializing conversation service...", 85
            )
            await self._initialize_conversation_service(consoul_config)
            logger.info(
                f"[PERF] Step 5.5 (Initialize ConversationService): {(time.time() - step_start) * 1000:.1f}ms"
            )

            # Step 6: Auto-resume if enabled (90%)
            await self._auto_resume_conversation(loading_screen)

            # Cleanup old conversations
            await self._cleanup_conversations()

            # Initialize title generator
            step_start = time.time()
            await self._initialize_title_generator(consoul_config)
            logger.info(
                f"[PERF] Initialize title generator: {(time.time() - step_start) * 1000:.1f}ms"
            )

            # Apply theme
            step_start = time.time()
            await self._apply_theme()
            logger.info(
                f"[PERF] Apply theme: {(time.time() - step_start) * 1000:.1f}ms"
            )

            # Step 7: Complete (100%)
            await self._finalize_initialization(loading_screen)

        except Exception as e:
            # Delegate error handling to app
            await self._handle_initialization_error(e, loading_screen)

    async def _update_progress(
        self, loading_screen: Any | None, message: str, progress: int
    ) -> None:
        """Update loading screen progress.

        Args:
            loading_screen: Loading screen widget (may be None)
            message: Progress message
            progress: Progress percentage (0-100)
        """
        if loading_screen:
            loading_screen.update_progress(message, progress)

    async def _load_config(self) -> "ConsoulTuiConfig | None":
        """Load configuration.

        Returns:
            Loaded config or None if no config needs loading
        """
        if self.app._needs_config_load:
            consoul_config = await self.app._run_in_thread(self.app._load_config)
            self.app.consoul_config = consoul_config
            return consoul_config
        return self.app.consoul_config

    async def _complete_without_config(self, loading_screen: Any | None) -> None:
        """Complete initialization when no config is available.

        Args:
            loading_screen: Loading screen widget (may be None)
        """
        if loading_screen:
            loading_screen.update_progress("Ready!", 100)
            await asyncio.sleep(0.5)
            await loading_screen.fade_out(duration=0.5)
            self.app.pop_screen()
        self.app._initialization_complete = True
        await self.app._post_initialization_setup()

    async def _set_active_profile(self, config: "ConsoulTuiConfig") -> None:
        """Set active profile from config.

        Args:
            config: Consoul configuration
        """
        self.app.active_profile = config.get_active_profile()  # type: ignore[no-untyped-call]
        assert self.app.active_profile is not None, (
            "Active profile should be available from config"
        )
        self.app.current_profile = self.app.active_profile.name
        self.app.current_model = config.current_model

    async def _initialize_model(self, config: "ConsoulTuiConfig") -> None:
        """Initialize AI model.

        Args:
            config: Consoul configuration
        """
        from consoul.sdk.services import ModelService

        self.app.model_service = await self.app._run_in_thread(
            ModelService.from_config,
            config.core,
            None,  # No tool service yet
        )
        self.app.chat_model = self.app.model_service.get_model()

    async def _initialize_conversation(self, config: "ConsoulTuiConfig") -> None:
        """Initialize conversation history.

        Args:
            config: Consoul configuration
        """
        import logging as log_module

        # Add detailed profiling to understand what's slow
        conv_logger = log_module.getLogger("consoul.ai.history")
        original_level = conv_logger.level
        conv_logger.setLevel(log_module.DEBUG)

        self.app.conversation = await self.app._run_in_thread(
            self.app._initialize_conversation, config, self.app.chat_model
        )

        conv_logger.setLevel(original_level)

        # Set conversation ID for tracking
        self.app.conversation_id = self.app.conversation.session_id
        logger.info(
            f"Initialized AI model: {config.current_model}, "
            f"session: {self.app.conversation_id}"
        )

    async def _initialize_tools(
        self, loading_screen: Any | None, config: "ConsoulTuiConfig"
    ) -> None:
        """Initialize and bind tools.

        Args:
            loading_screen: Loading screen widget (may be None)
            config: Consoul configuration
        """
        if config.tools and config.tools.enabled:
            from consoul.sdk.services import ToolService

            tool_service = await self.app._run_in_thread(
                ToolService.from_config, config
            )
            self.app.tool_registry = tool_service.tool_registry

            # Set tools_total for top bar display
            if hasattr(self.app, "top_bar"):
                self.app.top_bar.tools_total = tool_service.get_tools_count()

            # Bind tools to model via ModelService
            await self._update_progress(loading_screen, "Binding tools to model...", 70)

            if self.app.model_service:
                self.app.model_service.tool_service = tool_service
                await self.app._run_in_thread(self.app.model_service._bind_tools)
                self.app.chat_model = self.app.model_service.get_model()

                # Update conversation's model reference
                if self.app.conversation:
                    self.app.conversation._model = self.app.chat_model
        else:
            self.app.tool_registry = None

    async def _initialize_conversation_service(
        self, config: "ConsoulTuiConfig"
    ) -> None:
        """Initialize conversation service.

        Args:
            config: Consoul configuration
        """
        from consoul.sdk.services.conversation import ConversationService

        self.app.conversation_service = ConversationService(
            model=self.app.chat_model,  # type: ignore[arg-type]
            conversation=self.app.conversation,  # type: ignore[arg-type]
            tool_registry=self.app.tool_registry,
            config=config.core,
        )

    async def _auto_resume_conversation(self, loading_screen: Any | None) -> None:
        """Auto-resume conversation if enabled.

        Args:
            loading_screen: Loading screen widget (may be None)
        """
        import time

        if (
            self.app.active_profile
            and hasattr(self.app.active_profile, "conversation")
            and self.app.active_profile.conversation.auto_resume
            and self.app.active_profile.conversation.persist
        ):
            step_start = time.time()
            await self._update_progress(loading_screen, "Restoring conversation...", 90)
            self.app.conversation = await self.app._run_in_thread(
                self.app._auto_resume_if_enabled,
                self.app.conversation,
                self.app.active_profile,
            )
            self.app.conversation_id = self.app.conversation.session_id
            logger.info(
                f"[PERF] Step 6 (Auto-resume): {(time.time() - step_start) * 1000:.1f}ms"
            )

    async def _cleanup_conversations(self) -> None:
        """Cleanup old and empty conversations."""
        import time

        # Cleanup old conversations (retention policy)
        if self.app.active_profile:
            step_start = time.time()
            await self.app._run_in_thread(
                self.app._cleanup_old_conversations, self.app.active_profile
            )
            logger.info(
                f"[PERF] Cleanup old conversations: {(time.time() - step_start) * 1000:.1f}ms"
            )

        # One-time cleanup of empty conversations from old versions
        if self.app.conversation and self.app.conversation._db:
            step_start = time.time()
            try:
                deleted = await self.app._run_in_thread(
                    self.app.conversation._db.delete_empty_conversations
                )
                if deleted > 0:
                    logger.info(f"Cleaned up {deleted} legacy empty conversations")
            except Exception as e:
                logger.warning(f"Failed to cleanup empty conversations: {e}")
            logger.info(
                f"[PERF] Cleanup empty conversations: {(time.time() - step_start) * 1000:.1f}ms"
            )

    async def _initialize_title_generator(self, config: "ConsoulTuiConfig") -> None:
        """Initialize title generator.

        Args:
            config: Consoul configuration
        """
        self.app.title_generator = await self.app._run_in_thread(
            self.app._initialize_title_generator, config
        )

    async def _apply_theme(self) -> None:
        """Apply theme to app."""
        from consoul.tui.themes import (
            CONSOUL_DARK,
            CONSOUL_FOREST,
            CONSOUL_LIGHT,
            CONSOUL_MATRIX,
            CONSOUL_MIDNIGHT,
            CONSOUL_NEON,
            CONSOUL_OCEAN,
            CONSOUL_OLED,
            CONSOUL_SUNSET,
            CONSOUL_VOLCANO,
        )

        # Register all themes
        self.app.register_theme(CONSOUL_DARK)
        self.app.register_theme(CONSOUL_LIGHT)
        self.app.register_theme(CONSOUL_OLED)
        self.app.register_theme(CONSOUL_MIDNIGHT)
        self.app.register_theme(CONSOUL_MATRIX)
        self.app.register_theme(CONSOUL_SUNSET)
        self.app.register_theme(CONSOUL_OCEAN)
        self.app.register_theme(CONSOUL_VOLCANO)
        self.app.register_theme(CONSOUL_NEON)
        self.app.register_theme(CONSOUL_FOREST)

        # Apply configured theme
        try:
            self.app.theme = self.app.config.theme
            logger.info(f"[PERF] Applied theme: {self.app.config.theme}")
        except Exception as e:
            logger.warning(f"Failed to set theme '{self.app.config.theme}': {e}")
            self.app.theme = "textual-dark"

        # Give Textual a moment to apply theme CSS to all widgets
        await asyncio.sleep(0.25)

    async def _finalize_initialization(self, loading_screen: Any | None) -> None:
        """Finalize initialization and show main UI.

        Args:
            loading_screen: Loading screen widget (may be None)
        """
        if loading_screen:
            loading_screen.update_progress("Ready!", 100)
            await loading_screen.fade_out(duration=0.5)
            self.app.pop_screen()

        self.app._initialization_complete = True
        await self.app._post_initialization_setup()

    async def _handle_initialization_error(
        self, error: Exception, loading_screen: Any | None
    ) -> None:
        """Handle initialization error.

        Args:
            error: The exception that occurred
            loading_screen: Loading screen widget (may be None)
        """
        import traceback

        logger.error(
            f"[LOADING] Initialization failed: {error}\n{traceback.format_exc()}"
        )

        # Remove loading screen (if present)
        if loading_screen:
            try:
                logger.info("[LOADING] Exception caught, popping loading screen")
                self.app.pop_screen()
            except Exception as pop_err:
                logger.error(f"[LOADING] Failed to pop screen: {pop_err}")

        # Show error screen with troubleshooting guidance
        from consoul.tui.widgets.initialization_error_screen import (
            InitializationErrorScreen,
        )

        logger.info("[LOADING] Showing initialization error screen")
        self.app.push_screen(
            InitializationErrorScreen(error=error, app_instance=self.app)
        )

        # Set degraded mode (no AI functionality)
        self.app.chat_model = None
        self.app.conversation = None
        self.app._initialization_complete = False
