"""Main Consoul TUI application.

This module provides the primary ConsoulApp class that implements the Textual
terminal user interface for interactive AI conversations.
"""

from __future__ import annotations

import asyncio
import gc
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Footer, Input

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import TypeVar

    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import ToolMessage
    from textual.binding import BindingType

    from consoul.ai.history import ConversationHistory
    from consoul.ai.title_generator import TitleGenerator
    from consoul.ai.tools import ToolRegistry
    from consoul.ai.tools.parser import ParsedToolCall
    from consoul.sdk.models import Attachment, ToolRequest
    from consoul.sdk.services import ConversationService, ModelService
    from consoul.tui.config import ConsoulTuiConfig
    from consoul.tui.profiles import ProfileConfig
    from consoul.tui.widgets import (
        ContextualTopBar,
        InputArea,
        StreamingResponse,
    )

    T = TypeVar("T")

from consoul.tui.config import TuiConfig
from consoul.tui.widgets import InputArea, MessageBubble

__all__ = ["ConsoulApp"]

logger = logging.getLogger(__name__)


# Custom Messages for tool approval workflow
class ContinueWithToolResults(Message):
    """Message to trigger AI continuation after tool execution.

    Using message passing instead of direct await breaks the async call chain,
    allowing Textual to process input events between operations.
    """

    pass


class TUIToolApprover:
    """Bridges SDK tool approval callbacks with TUI modal system.

    Converts SDK's ToolRequest to AI layer's ToolApprovalRequest and shows
    the approval modal, returning the user's decision via async/await.

    Creates simple Static widgets to display tool calls inline (matches v0.3.0).

    Example:
        >>> approver = TUIToolApprover(app)
        >>> service = ConversationService(..., on_tool_request=approver.on_tool_request)
        >>> # Service will call approver.on_tool_request() and await the result
    """

    def __init__(self, app: ConsoulApp) -> None:
        """Initialize tool approver with TUI app reference.

        Args:
            app: ConsoulApp instance for showing modals and chat view
        """
        self.app = app

    async def on_tool_request(self, request: ToolRequest) -> bool:
        """Request approval for tool execution via TUI modal.

        Creates simple Static widget to display tool call, then shows approval
        modal if needed.

        Args:
            request: Tool request from ConversationService

        Returns:
            True if approved, False if denied
        """
        from textual.widgets import Static

        from consoul.ai.tools.approval import ToolApprovalRequest
        from consoul.ai.tools.base import RiskLevel
        from consoul.tui.widgets import ToolApprovalModal
        from consoul.tui.widgets.tool_formatter import format_tool_header

        # Map risk_level string to RiskLevel enum
        risk_map = {
            "safe": RiskLevel.SAFE,
            "caution": RiskLevel.CAUTION,
            "dangerous": RiskLevel.DANGEROUS,
            "blocked": RiskLevel.BLOCKED,
        }

        # Format tool header with arguments (returns Rich renderable)
        header_renderable = format_tool_header(
            request.name, request.arguments, theme=self.app.theme
        )

        # Use Static widget to render Rich renderables (matches v0.3.0)
        tool_message = Static(
            header_renderable,
            classes="system-message",
        )

        # Add message to chat view
        await self.app.chat_view.add_message(tool_message)

        # Check if approval is actually needed based on policy/whitelist
        needs_approval = True
        if self.app.tool_registry:
            needs_approval = self.app.tool_registry.needs_approval(
                request.name, request.arguments
            )

        # If auto-approved by policy, return True immediately
        if not needs_approval:
            return True

        # Approval needed - show modal to user
        # Convert SDK ToolRequest to AI layer ToolApprovalRequest
        approval_request = ToolApprovalRequest(
            tool_name=request.name,
            arguments=request.arguments,
            risk_level=risk_map.get(request.risk_level.lower(), RiskLevel.CAUTION),
            tool_call_id=request.id,
            description="",  # Could fetch from tool registry if needed
        )

        # Create future to wait for modal result
        future: asyncio.Future[bool] = asyncio.Future()

        def on_modal_result(approved: bool | None) -> None:
            """Callback when modal is dismissed."""
            if not future.done():
                # Default to False if None (user dismissed without choosing)
                future.set_result(approved if approved is not None else False)

        # Show modal (non-blocking with callback)
        self.app.push_screen(ToolApprovalModal(approval_request), on_modal_result)

        # Wait for user decision
        approved = await future

        return approved


class ConsoulApp(App[None]):
    """Main Consoul Terminal User Interface application.

    Provides an interactive chat interface with streaming AI responses,
    conversation history, and keyboard-driven navigation.
    """

    CSS_PATH = "css/main.tcss"
    TITLE = "Consoul - AI Terminal Assistant"
    SUB_TITLE = "Powered by LangChain"

    BINDINGS: ClassVar[list[BindingType]] = [
        # Essential
        Binding("q", "quit", "Quit", priority=True),
        Binding("ctrl+c", "quit", "Quit", priority=True, show=False),
        # Conversation
        Binding("ctrl+n", "new_conversation", "New Chat", show=True),
        Binding("ctrl+l", "clear_conversation", "Clear"),
        Binding("escape", "cancel_stream", "Cancel", show=False),
        # Navigation
        Binding("ctrl+p", "switch_profile", "Profile", show=False),
        Binding("ctrl+m", "switch_model", "Model", show=False),
        Binding("ctrl+o", "browse_ollama_library", "Ollama Library", show=False),
        Binding("ctrl+e", "export_conversation", "Export", show=True),
        Binding("ctrl+i", "import_conversation", "Import", show=False),
        Binding("ctrl+s", "search_history", "Search", show=False),
        Binding("/", "focus_input", "Input", show=False),
        # UI
        Binding("ctrl+b", "toggle_sidebar", "Sidebar", show=True),
        Binding("ctrl+shift+t", "toggle_theme", "Theme", show=True),
        Binding("ctrl+comma", "settings", "Settings", show=False),
        Binding("ctrl+shift+p", "permissions", "Permissions", show=True),
        Binding("ctrl+t", "tools", "Tools", show=True),
        Binding("ctrl+shift+s", "view_system_prompt", "System Prompt", show=False),
        Binding("f1", "help", "Help", show=False),
        # Secret - Screen Saver
        Binding("ctrl+shift+l", "toggle_screensaver", show=False),
    ]

    # Reactive state
    current_profile: reactive[str] = reactive("default")
    current_model: reactive[str] = reactive("")
    conversation_id: reactive[str | None] = reactive(None)
    streaming: reactive[bool] = reactive(False)

    def __init__(
        self,
        config: TuiConfig | None = None,
        consoul_config: ConsoulTuiConfig | None = None,
        test_mode: bool = False,
    ) -> None:
        """Initialize the Consoul TUI application.

        Args:
            config: TUI configuration (uses defaults if None)
            consoul_config: Consoul configuration for AI providers (loads from file if None)
            test_mode: Enable test mode (auto-exit for testing)
        """
        super().__init__()
        self.config = config or TuiConfig()
        self.test_mode = test_mode

        # Enable Textual devtools if debug mode
        if self.config.debug:
            log_path = self.config.log_file or "textual.log"
            self.log.info(f"Debug mode enabled, logging to: {log_path}")
            # Textual automatically logs to textual.log when devtools is active

        # Store original GC state for cleanup (library-first design)
        self._original_gc_enabled = gc.isenabled()

        # GC management will be set up in on_mount (after message pump starts)
        self._gc_interval_timer: object | None = None

        # Create managed thread pool executor for async operations
        # This ensures clean shutdown on Ctrl+C
        from concurrent.futures import ThreadPoolExecutor

        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="consoul")

        # Store configs (defer loading to async init)
        self._consoul_config_provided = consoul_config
        self._needs_config_load = consoul_config is None
        self.consoul_config: ConsoulTuiConfig | None = consoul_config

        # Initialize AI components to None (populated by async init)
        self.model_service: ModelService | None = None
        self.chat_model: BaseChatModel | None = None
        self.conversation: ConversationHistory | None = None
        self.active_profile: ProfileConfig | None = None
        # NOTE: Don't override reactive properties here - they have proper defaults
        # self.current_profile is set to "default" by reactive declaration
        # self.current_model is set to "" by reactive declaration
        # self.conversation_id is set to None by reactive declaration
        self.tool_registry: ToolRegistry | None = None
        self.title_generator: TitleGenerator | None = None
        self.conversation_service: ConversationService | None = None

        # Streaming state
        self._current_stream: StreamingResponse | None = None
        self._stream_cancelled = False

        # Tool execution state
        self._pending_tool_calls: list[ParsedToolCall] = []
        self._tool_results: dict[str, ToolMessage] = {}
        self._tool_call_iterations = 0
        self._max_tool_iterations = 5
        self._current_assistant_message_id: int | None = None

        # Inline command execution state
        self._pending_command_output: tuple[str, str] | None = None

        # Initialization state flag
        self._initialization_complete = False

    async def _run_in_thread(
        self, func: Callable[..., T], *args: Any, **kwargs: Any
    ) -> T:
        """Run a blocking function in a thread pool.

        This is a helper to run blocking I/O operations without freezing the UI.
        """
        import asyncio

        return await asyncio.to_thread(func, *args, **kwargs)

    def _load_config(self) -> ConsoulTuiConfig:
        """Load Consoul TUI configuration from file.

        Returns:
            Loaded ConsoulTuiConfig instance

        Raises:
            Exception: If config loading fails
        """
        from typing import cast

        from consoul.config.loader import load_tui_config

        return cast("ConsoulTuiConfig", load_tui_config())

    def _initialize_conversation(
        self, config: ConsoulTuiConfig, model: BaseChatModel
    ) -> ConversationHistory:
        """Create conversation history with model.

        Args:
            config: ConsoulTuiConfig for conversation settings
            model: Initialized chat model

        Returns:
            ConversationHistory instance
        """
        import logging
        import time

        logger = logging.getLogger(__name__)

        from consoul.ai import ConversationHistory

        step_start = time.time()
        conv_kwargs = self._get_conversation_config()
        logger.info(
            f"[PERF-CONV] Get conversation config: {(time.time() - step_start) * 1000:.1f}ms"
        )

        step_start = time.time()
        conversation = ConversationHistory(
            model_name=config.current_model,
            model=model,
            **conv_kwargs,
        )
        logger.info(
            f"[PERF-CONV] ConversationHistory.__init__: {(time.time() - step_start) * 1000:.1f}ms"
        )

        return conversation

    def _auto_resume_if_enabled(
        self, conversation: ConversationHistory, profile: ProfileConfig
    ) -> ConversationHistory:
        """Auto-resume last conversation if enabled in profile.

        Args:
            conversation: Current conversation instance
            profile: Active profile with auto_resume settings

        Returns:
            Updated conversation (same instance or resumed one)
        """
        # Check if auto-resume is enabled
        if not (
            hasattr(profile, "conversation")
            and profile.conversation.auto_resume
            and profile.conversation.persist
        ):
            return conversation

        try:
            # Query database for latest conversation
            from consoul.ai.database import ConversationDatabase

            db = ConversationDatabase(profile.conversation.db_path)
            recent_conversations = db.list_conversations(limit=1)

            if not recent_conversations:
                return conversation

            latest_session_id = recent_conversations[0]["session_id"]

            # Only resume if it's not the session we just created
            if latest_session_id == conversation.session_id:
                return conversation

            self.log.info(f"Auto-resuming last conversation: {latest_session_id}")

            # Reload conversation with latest session
            from consoul.ai import ConversationHistory

            conv_kwargs = self._get_conversation_config()
            conv_kwargs["session_id"] = latest_session_id

            # At this point consoul_config should be set since we're in an initialized conversation
            assert self.consoul_config is not None, (
                "Config should be available when resuming conversation"
            )

            return ConversationHistory(
                model_name=self.consoul_config.current_model,
                model=conversation._model,  # Reuse same model
                **conv_kwargs,
            )
        except Exception as e:
            self.log.warning(f"Failed to auto-resume conversation: {e}")
            return conversation

    def _initialize_title_generator(
        self, config: ConsoulTuiConfig
    ) -> TitleGenerator | None:
        """Initialize title generator if enabled.

        Args:
            config: ConsoulTuiConfig with title generator settings

        Returns:
            TitleGenerator instance or None if disabled/failed
        """
        if not self.config.auto_generate_titles:
            return None

        from consoul.ai.title_generator import (
            TitleGenerator,
            auto_detect_title_config,
        )

        try:
            # Determine provider and model
            provider = self.config.auto_title_provider
            model = self.config.auto_title_model

            # Auto-detect if not specified
            if provider is None or model is None:
                detected = auto_detect_title_config(config.core)
                if detected:
                    provider = provider or detected["provider"]
                    model = model or detected["model"]
                else:
                    self.log.info(
                        "Auto-title generation disabled: no suitable model found"
                    )
                    return None

            if not (provider and model):
                return None

            title_gen = TitleGenerator(
                provider=provider,
                model_name=model,
                prompt_template=self.config.auto_title_prompt,
                max_tokens=self.config.auto_title_max_tokens,
                temperature=self.config.auto_title_temperature,
                api_key=self.config.auto_title_api_key,
                config=config.core,
            )
            self.log.info(f"Title generator initialized: {provider}/{model}")
            return title_gen

        except Exception as e:
            self.log.warning(f"Failed to initialize title generator: {e}")
            return None

    def _cleanup_old_conversations(self, profile: ProfileConfig) -> None:
        """Clean up old conversations based on retention policy.

        Args:
            profile: Active profile with retention settings
        """
        if not (
            hasattr(profile, "conversation")
            and profile.conversation.retention_days > 0
            and profile.conversation.persist
        ):
            return

        try:
            from consoul.ai.database import ConversationDatabase

            db = ConversationDatabase(profile.conversation.db_path)
            deleted_count = db.delete_conversations_older_than(
                profile.conversation.retention_days
            )

            if deleted_count > 0:
                self.log.info(
                    f"Retention cleanup: deleted {deleted_count} conversations "
                    f"older than {profile.conversation.retention_days} days"
                )
        except Exception as e:
            self.log.warning(f"Failed to cleanup old conversations: {e}")

    async def _async_initialize(self) -> None:
        """Initialize app using InitializationOrchestrator.

        Delegates the entire initialization sequence to the InitializationOrchestrator
        service, which handles progress tracking, stage orchestration, and error handling.

        Progress stages (managed by orchestrator):
            10% - Loading configuration
            40% - Connecting to AI provider
            50% - Initializing conversation
            60% - Loading tools
            80% - Binding tools to model
            90% - Restoring conversation (if auto-resume enabled)
            100% - Complete

        Raises:
            Exception: Any initialization error (caught and shown in error screen)
        """
        from consoul.tui.services import InitializationOrchestrator

        try:
            # Get loading screen reference
            loading_screen = None
            if self.config.show_loading_screen and self.screen_stack:
                loading_screen = self.screen

            # Delegate complete initialization sequence to orchestrator
            orchestrator = InitializationOrchestrator(self)
            await orchestrator.run_initialization_sequence(loading_screen)

        except Exception as e:
            # Log error and show error screen
            import traceback

            logger.error(
                f"[LOADING] Initialization failed: {e}\n{traceback.format_exc()}"
            )

            # Remove loading screen (if present)
            if loading_screen:
                try:
                    logger.info("[LOADING] Exception caught, popping loading screen")
                    self.pop_screen()
                except Exception as pop_err:
                    logger.error(f"[LOADING] Failed to pop screen: {pop_err}")

            # Show error screen with troubleshooting guidance
            from consoul.tui.widgets.initialization_error_screen import (
                InitializationErrorScreen,
            )

            logger.info("[LOADING] Showing initialization error screen")
            self.push_screen(InitializationErrorScreen(error=e, app_instance=self))

            # Set degraded mode (no AI functionality)
            self.chat_model = None
            self.conversation = None
            self._initialization_complete = False

    async def _post_initialization_setup(self) -> None:
        """Setup that must happen after initialization completes.

        This includes adding system prompt, registering themes, and starting
        background tasks like GC and polling timers.
        """
        import logging

        logger = logging.getLogger(__name__)

        # Add system prompt to conversation (if conversation exists)
        logger.info(f"[POST-INIT] Conversation exists: {self.conversation is not None}")
        if self.conversation is not None:
            logger.info("[POST-INIT] Calling _add_initial_system_prompt()")
            self._add_initial_system_prompt()
            logger.info("[POST-INIT] Added initial system prompt")
        else:
            logger.warning("[POST-INIT] No conversation, skipping system prompt")

        # Theme is now applied during initialization (before main UI shows)
        # to prevent background color flash when loading screen is disabled

        # Set up GC management (streaming-aware mode from research)
        if self.config.gc_mode == "streaming-aware":
            gc.disable()
            self._gc_interval_timer = self.set_interval(
                self.config.gc_interval_seconds, self._idle_gc
            )

        # Set up search polling timer (to avoid focus/freeze issues)
        self.set_interval(0.2, self._poll_search_query)

        # Update top bar with initial state
        self._update_top_bar_state()

        # Warm up tokenizer in background (if using lazy loading)
        # This ensures tokenizer is loaded before first message
        if self.conversation and hasattr(self.conversation, "_token_counter"):

            async def warm_up_tokenizer() -> None:
                try:
                    # Trigger tokenizer loading by counting tokens on empty message
                    from langchain_core.messages import HumanMessage

                    assert self.conversation is not None, (
                        "Conversation should be available in warmup"
                    )
                    _ = self.conversation._token_counter([HumanMessage(content="")])
                    logger.info("[POST-INIT] Tokenizer warmed up in background")
                except Exception as e:
                    logger.debug(
                        f"[POST-INIT] Tokenizer warmup failed (non-critical): {e}"
                    )

            # Run in background without blocking
            import asyncio

            self._warmup_task = asyncio.create_task(warm_up_tokenizer())

        logger.info("[POST-INIT] Post-initialization setup complete")

    def on_mount(self) -> None:
        """Mount the app and start initialization.

        Optionally shows loading screen based on config, then triggers async
        initialization. This ensures users get visual feedback when enabled,
        or instant startup when disabled.
        """
        # Conditionally push loading screen based on config
        if self.config.show_loading_screen:
            from consoul.tui.animations import AnimationStyle
            from consoul.tui.loading import ConsoulLoadingScreen

            loading_screen = ConsoulLoadingScreen(
                animation_style=AnimationStyle.CODE_STREAM,
                show_progress=True,
                theme=self.config.theme,  # Pass theme from config
            )
            self.push_screen(loading_screen)

        # Use set_timer to schedule initialization after a brief delay
        # This ensures UI is ready (with or without loading screen) before heavy work
        self.set_timer(0.1, self._start_initialization)

    def _start_initialization(self) -> None:
        """Callback to start async initialization."""
        # Use call_next to schedule the coroutine
        self.call_next(self._async_initialize)

    def on_unmount(self) -> None:
        """Cleanup when app unmounts (library-first design).

        Restores original GC state to avoid affecting embedding applications.
        """
        # Shutdown thread pool executor gracefully
        if hasattr(self, "_executor"):
            try:
                # Cancel pending futures and don't wait
                self._executor.shutdown(wait=False, cancel_futures=True)
            except Exception as e:
                self.log.warning(f"Error shutting down executor: {e}")

        # Restore original GC state
        if self._original_gc_enabled:
            gc.enable()
        else:
            gc.disable()

    def compose(self) -> ComposeResult:
        """Compose the UI layout.

        Yields:
            Widgets to display in the app
        """
        from textual.containers import Horizontal, Vertical

        from consoul.tui.widgets import (
            ChatView,
            ContextualTopBar,
            ConversationList,
            InputArea,
        )

        # Top bar
        self.top_bar = ContextualTopBar(id="top-bar")
        yield self.top_bar

        # Main content area with optional sidebar
        with Horizontal(classes="main-container"):
            # Conversation list sidebar (conditional)
            # Only show sidebar if persistence is enabled in profile
            persist_enabled = True
            if self.active_profile and hasattr(self.active_profile, "conversation"):
                persist_enabled = self.active_profile.conversation.persist

            if self.config.show_sidebar and self.consoul_config and persist_enabled:
                from consoul.ai.database import ConversationDatabase

                # Use db_path from active profile if available
                db_path = None
                if (
                    self.active_profile
                    and hasattr(self.active_profile, "conversation")
                    and self.active_profile.conversation.db_path
                ):
                    db_path = self.active_profile.conversation.db_path

                db = (
                    ConversationDatabase(db_path) if db_path else ConversationDatabase()
                )
                self.conversation_list = ConversationList(db=db)
                yield self.conversation_list

            # Chat area (vertical layout)
            with Vertical(classes="content-area"):
                # Main chat display area
                self.chat_view = ChatView()
                yield self.chat_view

                # Message input area at bottom
                self.input_area = InputArea()
                yield self.input_area

        yield Footer()

    def _get_conversation_config(self) -> dict[str, Any]:
        """Get ConversationHistory kwargs from active profile configuration.

        Delegates to conversation_config_builder utility for config construction.

        Returns:
            Dictionary of kwargs for ConversationHistory constructor
        """
        from consoul.tui.utils.conversation_config_builder import (
            build_conversation_config,
        )

        return build_conversation_config(self.active_profile, self.consoul_config)

    def _add_initial_system_prompt(self) -> None:
        """Add system prompt to conversation during app initialization.

        Called from on_mount() after logging is set up. Adds the system prompt
        with dynamic tool documentation and stores metadata for the Ctrl+Shift+S viewer.
        """
        logger = logging.getLogger(__name__)
        logger.info(
            f"[SYSPROMPT] Adding initial system prompt to conversation "
            f"(conversation exists: {self.conversation is not None}, "
            f"message count: {len(self.conversation.messages) if self.conversation else 0}, "
            f"active_profile exists: {self.active_profile is not None}, "
            f"tool_registry exists: {self.tool_registry is not None})"
        )

        if self.conversation is None:
            logger.warning("[SYSPROMPT] No conversation exists, skipping")
            return

        try:
            system_prompt = self._build_current_system_prompt()
            logger.info(
                f"[SYSPROMPT] Built prompt: {len(system_prompt) if system_prompt else 0} chars"
            )

            if system_prompt:
                logger.info("[SYSPROMPT] Adding system message to conversation")
                self.conversation.add_system_message(system_prompt)
                logger.info(
                    f"[SYSPROMPT] Added. Total messages: {len(self.conversation.messages)}"
                )

                tool_count = 0
                if self.tool_registry:
                    tool_count = len(self.tool_registry.list_tools(enabled_only=True))

                logger.info(f"[SYSPROMPT] Storing metadata (tools: {tool_count})")
                self.conversation.store_system_prompt_metadata(
                    profile_name=self.active_profile.name
                    if self.active_profile
                    else None,
                    tool_count=tool_count,
                )
                logger.info(
                    f"[SYSPROMPT] SUCCESS: Added system prompt ({tool_count} tools, {len(system_prompt)} chars)"
                )
            else:
                logger.warning("[SYSPROMPT] System prompt was empty, not adding")
        except Exception as prompt_error:
            logger.error(
                f"[SYSPROMPT] Failed to add system prompt: {prompt_error}",
                exc_info=True,
            )

    def _build_current_system_prompt(self) -> str | None:
        """Build system prompt with environment context and tool documentation.

        Delegates to SystemPromptBuilder service for prompt construction.

        Returns:
            Complete system prompt with environment context and tool docs, or None
        """
        from consoul.tui.services.system_prompt_builder import SystemPromptBuilder

        if not self.active_profile:
            return None

        builder = SystemPromptBuilder(self.active_profile, self.tool_registry)
        return builder.build()

    def _model_supports_vision(self) -> bool:
        """Check if current model supports vision/multimodal input.

        Detects vision capabilities based on model name patterns for:
        - Anthropic Claude 3+
        - OpenAI GPT-4/5 (excludes GPT-3.5)
        - Google Gemini
        - Ollama vision models (qwen2-vl, qwen3-vl, llava, bakllava)

        Returns:
            True if model supports vision, False otherwise

        Example:
            >>> app._model_supports_vision()  # claude-3-5-sonnet → True
            >>> app._model_supports_vision()  # gpt-3.5-turbo → False
        """
        if not self.consoul_config or not self.consoul_config.current_model:
            return False

        model_name = self.consoul_config.current_model.lower()
        logger.info(
            f"[IMAGE_DETECTION] Checking vision support for model: {model_name}"
        )

        vision_patterns = [
            "claude-3",
            "claude-4",  # Anthropic Claude 3+
            "gpt-4",
            "gpt-5",  # OpenAI GPT-4V/5 (excludes gpt-3.5)
            "gemini",  # Google Gemini (all versions)
            "qwen2-vl",
            "qwen3-vl",  # Ollama qwen vision
            "llava",
            "bakllava",  # Ollama llava models
        ]

        has_vision = any(pattern in model_name for pattern in vision_patterns)
        logger.info(f"[IMAGE_DETECTION] Model '{model_name}' has vision: {has_vision}")
        return has_vision

    def _sync_vision_tool_registration(self) -> None:
        """Synchronize analyze_images tool registration with current model capabilities.

        This method dynamically registers or unregisters the analyze_images tool based on:
        1. Whether image_analysis is enabled in config
        2. Whether the current model supports vision

        Called during:
        - Initial app startup (after tool registry creation)
        - Model/provider switching (to reflect new model capabilities)

        This ensures the tool registry always matches the actual model capabilities,
        preventing scenarios where:
        - Vision-capable models don't have access to analyze_images
        - Text-only models incorrectly have analyze_images registered
        """
        if not self.tool_registry or not self.consoul_config:
            return

        from consoul.ai.tools.base import RiskLevel
        from consoul.ai.tools.exceptions import ToolNotFoundError
        from consoul.ai.tools.implementations.analyze_images import analyze_images

        tool_name = "analyze_images"
        is_enabled = self.consoul_config.tools.image_analysis.enabled
        supports_vision = self._model_supports_vision()
        should_register = is_enabled and supports_vision

        # Check current registration status
        try:
            self.tool_registry.get_tool(tool_name)
            is_registered = True
        except ToolNotFoundError:
            is_registered = False

        # Sync registration state with model capabilities
        if should_register and not is_registered:
            # Register the tool (vision-capable model)
            self.tool_registry.register(
                analyze_images,
                risk_level=RiskLevel.CAUTION,
                tags=["multimodal", "vision", "filesystem", "external_api"],
                enabled=True,
            )
            self.log.info(
                f"Registered analyze_images tool for vision-capable model: {self.current_model}"
            )
        elif not should_register and is_registered:
            # Unregister the tool (text-only model or disabled)
            self.tool_registry.unregister(tool_name)
            self.log.info(
                f"Unregistered analyze_images tool: "
                f"enabled={is_enabled}, vision_support={supports_vision}, "
                f"model={self.current_model}"
            )
        else:
            # State already correct
            self.log.debug(
                f"Vision tool registration unchanged: "
                f"registered={is_registered}, should_register={should_register}"
            )

    def _create_multimodal_message(
        self, user_message: str, image_paths: list[str]
    ) -> Any:
        """Create a multimodal HumanMessage with text and images.

        Delegates to message_submission utility for multimodal message creation.

        Args:
            user_message: The user's text message
            image_paths: List of valid image file paths to include

        Returns:
            HumanMessage with multimodal content (text + images)

        Raises:
            ValueError: If config not available
            Exception: If image loading, encoding, or formatting fails
        """
        from consoul.tui.utils.message_submission import create_multimodal_message

        if not self.consoul_config:
            raise ValueError("Config not available for multimodal message creation")

        return create_multimodal_message(user_message, image_paths, self.consoul_config)

    def _update_top_bar_state(self) -> None:
        """Update ContextualTopBar reactive properties from app state.

        Delegates to top_bar_state_builder utility for state calculation.
        """
        try:
            if not hasattr(self, "top_bar"):
                return

            from consoul.tui.utils.top_bar_state_builder import build_top_bar_state

            # Get conversation count
            conversation_count = None
            if hasattr(self, "conversation_list") and self.conversation_list:
                conversation_count = self.conversation_list.conversation_count

            # Build state from app components
            state = build_top_bar_state(
                consoul_config=self.consoul_config,
                current_profile=self.current_profile,
                current_model=self.current_model,
                streaming=self.streaming,
                tool_registry=self.tool_registry,
                conversation_count=conversation_count,
            )

            # Apply state to top bar
            for key, value in state.items():
                setattr(self.top_bar, key, value)

        except Exception as e:
            logger.error(f"Error updating top bar state: {e}", exc_info=True)

    def _rebind_tools(self) -> None:
        """Rebind tools to chat model after registry changes.

        Delegates to ToolRebindingService for model rebinding and updates.
        """
        if not self.tool_registry or not self.chat_model:
            return

        try:
            from consoul.tui.services.tool_rebinding_service import (
                ToolRebindingService,
            )

            service = ToolRebindingService(
                tool_registry=self.tool_registry,
                chat_model=self.chat_model,
                conversation=self.conversation,
                consoul_config=self.consoul_config.core
                if self.consoul_config
                else None,
                active_profile=self.active_profile,
                update_top_bar_callback=self._update_top_bar_state,
                build_system_prompt_callback=self._build_current_system_prompt,
            )
            self.chat_model = service.rebind()

        except Exception as e:
            self.log.error(f"Error rebinding tools: {e}", exc_info=True)
            self.notify(f"Failed to rebind tools: {e!s}", severity="error")

    def _idle_gc(self) -> None:
        """Periodic garbage collection when not streaming.

        Called on interval defined by config.gc_interval_seconds.
        Only collects when not actively streaming.
        """
        if not self.streaming:
            gc.collect(generation=self.config.gc_generation)

    async def _stream_via_conversation_service(
        self, content: str, attachments: list[Attachment] | None = None
    ) -> None:
        """Stream AI response using ConversationService.

        Delegates to StreamingOrchestrator for complete streaming workflow.

        Args:
            content: User message content
            attachments: Optional list of file attachments
        """
        if not self.conversation_service:
            from consoul.tui.utils import create_error_bubble

            error_bubble = create_error_bubble("ConversationService not initialized")
            await self.chat_view.add_message(error_bubble)
            return

        from consoul.tui.services.streaming_orchestrator import StreamingOrchestrator

        orchestrator = StreamingOrchestrator(
            conversation_service=self.conversation_service,
            chat_view=self.chat_view,
            app=self,
        )

        try:
            await orchestrator.stream_message(content, attachments)
        finally:
            # Reset streaming state
            self.streaming = False
            self._stream_cancelled = False
            self._current_stream = None
            self._update_top_bar_state()

    async def on_input_area_message_submit(
        self, event: InputArea.MessageSubmit
    ) -> None:
        """Handle user message submission from InputArea.

        Delegates to MessageSubmissionOrchestrator for complete workflow.

        Args:
            event: MessageSubmit event containing user's message content
        """
        from consoul.tui.services.message_submission_orchestrator import (
            MessageSubmissionOrchestrator,
        )

        orchestrator = MessageSubmissionOrchestrator(self)
        await orchestrator.handle_submission(event)

    async def on_input_area_command_execute_requested(
        self, event: InputArea.CommandExecuteRequested
    ) -> None:
        """Handle inline shell command execution request.

        Args:
            event: CommandExecuteRequested event containing the command
        """
        import subprocess

        from consoul.tui.utils import CommandExecutionHandler
        from consoul.tui.widgets.command_output_bubble import CommandOutputBubble

        command = event.command
        handler = CommandExecutionHandler()

        try:
            # Execute command
            stdout, stderr, exit_code, execution_time = await handler.execute_command(
                command, cwd=Path.cwd(), run_in_thread=self._run_in_thread
            )

            # Create output bubble
            output_bubble = CommandOutputBubble(
                command=command,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                execution_time=execution_time,
            )

            # Add to chat view
            await self.chat_view.add_message(output_bubble)

            # Store output in buffer for next user message
            output_text = stdout
            if stderr:
                output_text += f"\n\n=== STDERR ===\n{stderr}"

            self._pending_command_output = (command, output_text)

        except subprocess.TimeoutExpired:
            # Command timed out
            error_bubble = CommandOutputBubble(
                command=command,
                stdout="",
                stderr=f"Command timed out after {handler.timeout} seconds",
                exit_code=124,  # Standard timeout exit code
                execution_time=handler.timeout,
            )

            await self.chat_view.add_message(error_bubble)
            self.notify(
                f"Command timed out after {handler.timeout} seconds", severity="warning"
            )

        except Exception as e:
            # Execution failed
            error_bubble = CommandOutputBubble(
                command=command,
                stdout="",
                stderr=f"Execution failed: {e}",
                exit_code=1,
                execution_time=0,
            )

            await self.chat_view.add_message(error_bubble)
            self.notify(f"Command execution failed: {e}", severity="error")

    async def on_input_area_inline_commands_requested(
        self, event: InputArea.InlineCommandsRequested
    ) -> None:
        """Handle inline command execution and replacement in message.

        Executes all !`command` patterns in the message and replaces them
        with their output inline.

        Args:
            event: InlineCommandsRequested event containing the message
        """
        from consoul.tui.utils import CommandExecutionHandler

        message = event.message
        handler = CommandExecutionHandler()

        # Detect and substitute inline commands
        processed_message = await handler.substitute_inline_commands(
            message, run_in_thread=self._run_in_thread
        )

        # Send the processed message as a regular message
        self.post_message(InputArea.MessageSubmit(processed_message))

    # Action handlers (placeholders for Phase 2+)

    async def action_new_conversation(self) -> None:
        """Start a new conversation."""
        if self.conversation is not None and self.consoul_config:
            # Clear chat view
            await self.chat_view.clear_messages()

            # Clear conversation list selection
            if self.conversation_list:
                self.conversation_list.clear_selection()

            # Create new conversation with same model and profile settings
            from consoul.ai import ConversationHistory

            conv_kwargs = self._get_conversation_config()
            self.conversation = ConversationHistory(
                model_name=self.consoul_config.current_model,
                model=self.chat_model,
                **conv_kwargs,
            )

            # Re-add system prompt if configured (with dynamic tool documentation)
            system_prompt = self._build_current_system_prompt()
            if system_prompt:
                self.conversation.add_system_message(system_prompt)
                # Store prompt metadata for debugging/viewing later
                tool_count = (
                    len(self.tool_registry.list_tools(enabled_only=True))
                    if self.tool_registry
                    else 0
                )
                self.conversation.store_system_prompt_metadata(
                    profile_name=self.active_profile.name
                    if self.active_profile
                    else None,
                    tool_count=tool_count,
                )

            self.conversation_id = self.conversation.session_id
            self.notify("Started new conversation", severity="information")
        else:
            self.notify("AI model not initialized", severity="warning")

    async def action_clear_conversation(self) -> None:
        """Clear current conversation."""
        if self.conversation is not None:
            # Clear chat view
            await self.chat_view.clear_messages()

            # Clear conversation history (preserve system message)
            self.conversation.clear(preserve_system=True)

            self.log.info("Conversation cleared")
            self.notify("Conversation cleared", severity="information")
        else:
            self.notify("No conversation to clear", severity="warning")

    def action_cancel_stream(self) -> None:
        """Cancel active streaming."""
        if self.streaming and self._current_stream:
            self._stream_cancelled = True
            self.log.info("Cancelling stream...")
            self.notify("Cancelling stream...", severity="warning")
        else:
            self.log.debug("No active stream to cancel")

    def action_switch_profile(self) -> None:
        """Show profile selection modal."""
        self.notify("Profile switcher (Phase 3)")

    def action_switch_model(self) -> None:
        """Show model selection modal."""
        self.notify("Model switcher (Phase 3)")

    def action_export_conversation(self) -> None:
        """Show export modal."""
        from consoul.tui.widgets.export_modal import ExportModal

        def on_export(filepath: str | None) -> None:
            if filepath:
                self.notify(f"Exported to {filepath}", severity="information")

        current_session_id = self.conversation.session_id if self.conversation else None
        modal = ExportModal(
            current_session_id=current_session_id, db=self.conversation_list.db
        )
        self.push_screen(modal, on_export)

    def action_import_conversation(self) -> None:
        """Show import modal."""
        from consoul.tui.widgets.import_modal import ImportModal

        async def on_import(success: bool | None) -> None:
            if success:
                self.notify("Import successful", severity="information")
                # Reload conversation list
                await self.conversation_list.load_conversations()

        modal = ImportModal(db=self.conversation_list.db)
        self.push_screen(modal, on_import)

    def action_search_history(self) -> None:
        """Focus search input in top bar."""
        try:
            from consoul.tui.widgets.search_bar import SearchBar

            search_bar = self.query_one("#search-bar", SearchBar)
            search_input = search_bar.query_one("#search-input", Input)
            search_input.focus()
            self.log.info("Focused search input via Ctrl+S")
        except Exception as e:
            self.log.warning(f"Could not focus search input: {e}")

    def action_focus_input(self) -> None:
        """Focus the input area."""
        self.notify("Focus input (Phase 2)")

    async def action_settings(self) -> None:
        """Show settings screen."""
        from consoul.tui.widgets.settings_screen import SettingsScreen

        if self.consoul_config is None:
            self.notify("Configuration not loaded", severity="error")
            return None

        result: bool | None = await self.push_screen(
            SettingsScreen(config=self.config, consoul_config=self.consoul_config)
        )
        if result:
            self.notify("Settings saved successfully", severity="information")
        return None

    async def action_permissions(self) -> None:
        """Show permission manager screen."""
        from consoul.tui.widgets.permission_manager_screen import (
            PermissionManagerScreen,
        )

        if self.consoul_config is None:
            self.notify("Configuration not loaded", severity="error")
            return None

        result: bool | None = await self.push_screen(
            PermissionManagerScreen(self.consoul_config.core)
        )
        if result:
            self.notify(
                "Permission settings saved successfully", severity="information"
            )
        return None

    async def action_tools(self) -> None:
        """Show tool manager screen."""
        from consoul.tui.widgets.tool_manager_screen import ToolManagerScreen

        if not self.tool_registry:
            self.notify("Tool registry not initialized", severity="error")
            return None

        logger = logging.getLogger(__name__)
        logger.info("[TOOL_MANAGER] About to push tool manager screen")
        result: bool | None = await self.push_screen(
            ToolManagerScreen(self.tool_registry)
        )
        logger.info(
            f"[TOOL_MANAGER] Tool manager closed, result={result}, type={type(result)}"
        )
        if result is True:
            # Changes were applied - rebind tools to model
            logger.info("[TOOL_MANAGER] Applying changes, rebinding tools")
            self._rebind_tools()
            self.notify(
                "Tool settings applied - conversation history cleared",
                severity="information",
            )
        else:
            logger.info("[TOOL_MANAGER] No changes applied")
        return None

    async def action_view_system_prompt(self) -> None:
        """Show system prompt modal with current or stored prompt."""
        from consoul.tui.utils import show_system_prompt_modal

        if not self.conversation:
            self.notify("No active conversation", severity="warning")
            return

        # Try to get stored prompt from database metadata
        system_prompt = None
        profile_name = None
        tool_count = None
        stored_at = None

        if (
            self.conversation.persist
            and self.conversation._db
            and self.conversation.session_id
        ):
            try:
                metadata = self.conversation._db.get_conversation_metadata(
                    self.conversation.session_id
                )
                if "metadata" in metadata:
                    meta = metadata["metadata"]
                    system_prompt = meta.get("system_prompt")
                    profile_name = meta.get("profile_name")
                    tool_count = meta.get("tool_count")
                    stored_at = meta.get("system_prompt_stored_at")
            except Exception as e:
                self.log.warning(f"Failed to retrieve stored prompt: {e}")

        # Fallback to current system message if no stored prompt
        if (
            not system_prompt
            and self.conversation.messages
            and isinstance(
                self.conversation.messages[0],
                __import__(
                    "langchain_core.messages", fromlist=["SystemMessage"]
                ).SystemMessage,
            )
        ):
            system_prompt = str(self.conversation.messages[0].content)
            profile_name = self.active_profile.name if self.active_profile else None
            tool_count = (
                len(self.tool_registry.list_tools(enabled_only=True))
                if self.tool_registry
                else 0
            )

        if not system_prompt:
            self.notify("No system prompt found", severity="warning")
            return

        await show_system_prompt_modal(
            self, system_prompt, profile_name, tool_count, stored_at
        )

    async def action_help(self) -> None:
        """Show help modal."""
        from consoul.tui.widgets.help_modal import HelpModal

        await self.push_screen(
            HelpModal(
                theme=self.theme,
                profile=self.current_profile,
                model=self.current_model,
            )
        )

    async def action_browse_ollama_library(self) -> None:
        """Show Ollama Library browser modal."""
        from consoul.tui.utils import show_ollama_library_modal

        try:
            await show_ollama_library_modal(self)
        except ImportError:
            self.notify(
                "Ollama Library browser requires beautifulsoup4.\n"
                "Install with: pip install consoul[ollama-library]",
                severity="warning",
                timeout=10,
            )

    def action_toggle_sidebar(self) -> None:
        """Toggle conversation list sidebar visibility."""
        if not hasattr(self, "conversation_list"):
            return

        # Toggle display
        self.conversation_list.display = not self.conversation_list.display

    def action_toggle_theme(self) -> None:
        """Cycle through available themes."""
        # Define available themes in order (matches settings screen)
        available_themes = [
            "consoul-dark",
            "consoul-oled",
            "consoul-midnight",
            "consoul-ocean",
            "consoul-forest",
            "consoul-sunset",
            "consoul-volcano",
            "consoul-matrix",
            "consoul-neon",
            "consoul-light",
            "monokai",
            "dracula",
            "nord",
            "gruvbox",
            "tokyo-night",
            "catppuccin-mocha",
            "catppuccin-latte",
            "solarized-light",
            "flexoki",
            "textual-dark",
            "textual-light",
            "textual-ansi",
        ]

        try:
            # Get current theme
            current_theme = str(self.theme)

            # Find next theme in cycle
            try:
                current_index = available_themes.index(current_theme)
                next_index = (current_index + 1) % len(available_themes)
            except ValueError:
                # Current theme not in list, default to first theme
                next_index = 0

            next_theme = available_themes[next_index]

            # Apply theme
            self.theme = next_theme

            # Update config to persist the change
            if hasattr(self, "config") and self.config:
                self.config.theme = next_theme

        except Exception as e:
            logger.error(f"Failed to toggle theme: {e}")

    async def action_toggle_screensaver(self) -> None:
        """Toggle the loading screen as a screen saver (secret binding)."""
        from consoul.tui.utils import create_screensaver_screen

        # Check if a screensaver is currently showing
        # Screens are on top of the screen stack
        if len(self.screen_stack) > 1:
            # There's a screen showing - restore docked widgets and dismiss it
            for widget in self.query("Footer, ContextualTopBar"):
                widget.display = True
            self.pop_screen()
            return

        # Create and show screensaver
        theme_name = (
            self.theme if hasattr(self, "theme") and self.theme else "consoul-dark"
        )
        screensaver = create_screensaver_screen(theme_name)
        await self.push_screen(screensaver)

    def _should_generate_title(self) -> bool:
        """Check if we should generate a title for current conversation.

        Returns:
            True if this is the first complete user/assistant exchange
        """
        if not self.conversation or not self.title_generator:
            return False

        # Count user/assistant messages (exclude system)
        user_msgs = sum(1 for m in self.conversation.messages if m.type == "human")
        assistant_msgs = sum(1 for m in self.conversation.messages if m.type == "ai")

        # Generate title after first complete exchange
        return user_msgs == 1 and assistant_msgs == 1

    def _should_display_thinking(self, thinking: str | None) -> str | None:
        """Determine if thinking should be displayed based on config.

        Args:
            thinking: Extracted thinking content (or None)

        Returns:
            Thinking content to display, or None to hide it
        """
        if not thinking or not self.consoul_config:
            return None

        show_thinking = self.consoul_config.show_thinking
        thinking_models = self.consoul_config.thinking_models

        if show_thinking == "always":
            return thinking
        elif show_thinking == "auto":
            # Show only for known reasoning models
            if any(
                model_pattern.lower() in self.current_model.lower()
                for model_pattern in thinking_models
            ):
                return thinking
        elif show_thinking == "collapsed":
            return thinking
        # "never" or unknown -> None

        return None

    async def _generate_and_save_title(
        self, session_id: str, user_msg: str, assistant_msg: str
    ) -> None:
        """Generate and save conversation title in background.

        Args:
            session_id: Conversation session ID
            user_msg: First user message
            assistant_msg: First assistant response
        """
        try:
            self.log.debug(f"Generating title for conversation {session_id}")

            # Generate title using LLM
            title = await self.title_generator.generate_title(user_msg, assistant_msg)  # type: ignore[union-attr]

            self.log.info(f"Generated title: '{title}'")

            # Save to database
            from consoul.ai.database import ConversationDatabase

            db = ConversationDatabase()
            db.update_conversation_metadata(session_id, {"title": title})

            # Update UI if conversation list is visible
            if hasattr(self, "conversation_list"):
                # Find and update the card in conversation list
                from consoul.tui.widgets.conversation_card import ConversationCard

                found = False
                for card in self.conversation_list.cards_container.query(
                    ConversationCard
                ):
                    if card.conversation_id == session_id:
                        card.update_title(title)
                        self.log.debug(f"Updated card title to: {title}")
                        found = True
                        break

                if not found:
                    self.log.warning(
                        f"Card not found for session {session_id}, reloading list"
                    )
                    # Reload conversation list if card wasn't found
                    await self.conversation_list.reload_conversations()

        except Exception as e:
            self.log.warning(f"Failed to generate title: {e}")
            # Silently fail - title generation is non-critical

    async def on_conversation_list_conversation_selected(
        self,
        event: ConversationList.ConversationSelected,  # type: ignore[name-defined]  # noqa: F821
    ) -> None:
        """Handle conversation selection from sidebar.

        Args:
            event: ConversationSelected event from ConversationList
        """
        conversation_id = event.conversation_id
        self.log.info(f"Loading conversation: {conversation_id}")

        # Load conversation from database with full metadata for UI reconstruction
        if self.consoul_config:
            try:
                from consoul.tui.utils import (
                    load_conversation_to_view,
                    reconstruct_conversation_history,
                )

                # Load and display conversation in chat view
                await load_conversation_to_view(
                    self.chat_view,
                    conversation_id,
                    self.conversation_list.db,
                    self.theme,
                    self.current_model,
                    self._should_display_thinking,
                )

                # Update conversation ID to resume this conversation
                self.conversation_id = conversation_id

                # Update the conversation object if we have one
                # Use explicit None check instead of truthiness check
                # because ConversationHistory.__len__ makes empty conversations falsy
                if self.conversation is not None and self.consoul_config is not None:
                    # Reload conversation history into current conversation object with profile settings
                    try:
                        self.conversation = reconstruct_conversation_history(
                            self.consoul_config,
                            conversation_id,
                            self.chat_model,
                            self._get_conversation_config,
                        )
                    except Exception as e:
                        logger.error(
                            f"[CONV_LOAD] Failed to create ConversationHistory: {e}",
                            exc_info=True,
                        )

            except Exception as e:
                self.log.error(f"Failed to load conversation: {e}")
                self.notify(f"Failed to load conversation: {e}", severity="error")

    async def on_conversation_list_conversation_deleted(
        self,
        event: ConversationList.ConversationDeleted,  # type: ignore[name-defined]  # noqa: F821
    ) -> None:
        """Handle conversation deletion from sidebar.

        If the deleted conversation was the active one, start a new conversation.

        Args:
            event: ConversationDeleted event from ConversationList
        """
        conversation_id = event.conversation_id
        self.log.info(f"Conversation deleted: {conversation_id}")

        # If the active conversation was deleted, start a new one
        if event.was_active:
            self.log.info("Active conversation was deleted, starting new conversation")
            await self.action_new_conversation()
            self.notify(
                "Conversation deleted. Started new conversation.",
                severity="information",
            )
        else:
            self.notify("Conversation deleted.", severity="information")

    async def on_message_bubble_branch_requested(
        self,
        event: MessageBubble.BranchRequested,
    ) -> None:
        """Handle conversation branching from a specific message.

        Creates a new conversation with all messages up to and including the
        branch point, then switches to the new conversation.

        Args:
            event: BranchRequested event from MessageBubble
        """
        message_id = event.message_id
        current_session_id = self.conversation_id

        if not current_session_id:
            self.notify("No active conversation to branch from", severity="error")
            return

        try:
            from consoul.tui.utils import create_conversation_branch

            # Branch the conversation in the database
            new_session_id = await create_conversation_branch(
                self.conversation_list.db,
                current_session_id,
                message_id,
            )

            # Reload conversation list to show the new branch
            await self.conversation_list.reload_conversations()

            # Switch to the new branched conversation
            from consoul.tui.widgets.conversation_list import ConversationList

            # Simulate conversation selection event to load the branched conversation
            branch_event = ConversationList.ConversationSelected(new_session_id)
            await self.on_conversation_list_conversation_selected(branch_event)

            # Notify user
            self.notify(
                "Conversation branched successfully! 🌿",
                severity="information",
                timeout=3,
            )

        except Exception as e:
            self.log.error(f"Failed to branch conversation: {e}")
            self.notify(
                f"Failed to branch conversation: {e}",
                severity="error",
                timeout=5,
            )

    # ContextualTopBar message handlers

    async def on_contextual_top_bar_tools_requested(
        self, event: ContextualTopBar.ToolsRequested
    ) -> None:
        """Handle tools button click from top bar."""
        await self.action_tools()

    async def on_contextual_top_bar_settings_requested(
        self, event: ContextualTopBar.SettingsRequested
    ) -> None:
        """Handle settings button click from top bar."""
        await self.action_settings()

    async def on_contextual_top_bar_help_requested(
        self, event: ContextualTopBar.HelpRequested
    ) -> None:
        """Handle help button click from top bar."""
        await self.action_help()

    async def on_contextual_top_bar_model_selection_requested(
        self, event: ContextualTopBar.ModelSelectionRequested
    ) -> None:
        """Handle model selection request from top bar."""
        if not self.consoul_config:
            self.notify("No configuration available", severity="error")
            return

        def on_model_selected(result: tuple[str, str] | None) -> None:
            if result and self.consoul_config:
                provider, model_name = result
                logger.debug(
                    f"Model picker returned: provider={provider}, model={model_name}"
                )
                logger.debug(
                    f"Current state: provider={self.consoul_config.current_provider.value}, model={self.current_model}"
                )
                if (
                    provider != self.consoul_config.current_provider.value
                    or model_name != self.current_model
                ):
                    logger.info(f"Switching to {provider}/{model_name}")
                    self._switch_provider_and_model(provider, model_name)
                else:
                    logger.debug("Model already selected, no switch needed")

        from consoul.tui.widgets import EnhancedModelPicker

        modal = EnhancedModelPicker(
            current_model=self.current_model,
            current_provider=self.consoul_config.current_provider,
            model_service=self.model_service,
        )
        self.push_screen(modal, on_model_selected)

    async def on_contextual_top_bar_sidebar_toggle_requested(
        self, event: ContextualTopBar.SidebarToggleRequested
    ) -> None:
        """Handle sidebar toggle request from top bar."""
        self.action_toggle_sidebar()

    async def on_contextual_top_bar_profile_selection_requested(
        self, event: ContextualTopBar.ProfileSelectionRequested
    ) -> None:
        """Handle profile selection request from top bar."""
        if not self.consoul_config:
            self.notify("No configuration available", severity="error")
            return

        def on_profile_action(result: tuple[str, str | None] | None) -> None:
            """Handle profile selector modal result.

            Args:
                result: Tuple of (action, profile_name) or None for cancel
                    Actions: 'select', 'create', 'edit', 'delete'
            """
            if not result:
                return

            action, profile_name = result

            if action == "select":
                if profile_name and profile_name != self.current_profile:
                    self._switch_profile(profile_name)

            elif action == "create":
                self._handle_create_profile()

            elif action == "edit":
                if profile_name:
                    self._handle_edit_profile(profile_name)

            elif action == "delete" and profile_name:
                self._handle_delete_profile(profile_name)

        from consoul.tui.profiles import get_builtin_profiles
        from consoul.tui.widgets import ProfileSelectorModal

        builtin_names = set(get_builtin_profiles().keys())

        modal = ProfileSelectorModal(
            current_profile=self.current_profile,
            profiles=self.consoul_config.profiles,
            builtin_profile_names=builtin_names,
        )
        self.push_screen(modal, on_profile_action)

    async def _poll_search_query(self) -> None:
        """Poll search query from SearchBar to avoid focus issues."""
        from consoul.tui.widgets.search_bar import SearchBar

        try:
            search_bar = self.query_one("#search-bar", SearchBar)
            current_query = search_bar.get_search_query()

            # Check if query changed
            if not hasattr(self, "_last_search_query"):
                self._last_search_query = ""

            if current_query != self._last_search_query:
                self._last_search_query = current_query

                # Perform search
                if current_query:
                    # Show sidebar if hidden (so user can see search results)
                    if not self.conversation_list.display:
                        self.conversation_list.display = True

                    await self.conversation_list.search(current_query)
                    # Update match count in search bar (only when searching)
                    from consoul.tui.widgets.conversation_card import ConversationCard

                    result_count = len(
                        self.conversation_list.cards_container.query(ConversationCard)
                    )
                    search_bar.update_match_count(result_count)
                    self.log.info(
                        f"Search query='{current_query}', results={result_count}"
                    )
                else:
                    await self.conversation_list.search("")
                    # Clear match count when search is cleared
                    search_bar.update_match_count(0)
                    self.log.info("Search cleared, showing all conversations")
        except Exception:
            pass

    def _switch_profile(self, profile_name: str) -> None:
        """Switch to a different profile WITHOUT changing model/provider.

        Profiles define HOW to use AI (system prompts, context settings).
        This method updates profile settings while preserving current model.

        Args:
            profile_name: Name of profile to switch to
        """
        from consoul.tui.services import ProfileUIOrchestrator

        ProfileUIOrchestrator.switch_profile(
            self,
            self.consoul_config.core if self.consoul_config else None,
            profile_name,
        )

    def _handle_profile_error(self, operation: str, error: Exception) -> None:
        """Handle profile operation errors with consistent formatting.

        Args:
            operation: Operation that failed (e.g., "create", "update", "delete", "switch")
            error: Exception that was raised
        """
        # Escape markup characters to avoid formatting errors
        error_msg = str(error).replace("[", "\\[")
        self.notify(f"Failed to {operation} profile: {error_msg}", severity="error")
        self.log.error(f"Profile {operation} failed: {error}", exc_info=True)

    def _handle_create_profile(self) -> None:
        """Handle create new profile action from ProfileSelectorModal."""
        from consoul.tui.services import ProfileUIOrchestrator

        ProfileUIOrchestrator.show_create_profile_modal(
            self, self.consoul_config.core if self.consoul_config else None
        )

    def _handle_edit_profile(self, profile_name: str) -> None:
        """Handle edit profile action from ProfileSelectorModal.

        Args:
            profile_name: Name of profile to edit
        """
        from consoul.tui.services import ProfileUIOrchestrator

        ProfileUIOrchestrator.show_edit_profile_modal(
            self,
            self.consoul_config.core if self.consoul_config else None,
            profile_name,
        )

    def _handle_delete_profile(self, profile_name: str) -> None:
        """Handle delete profile action from ProfileSelectorModal.

        Args:
            profile_name: Name of profile to delete
        """
        from consoul.tui.services import ProfileUIOrchestrator

        ProfileUIOrchestrator.show_delete_profile_modal(
            self,
            self.consoul_config.core if self.consoul_config else None,
            profile_name,
        )

    def _switch_provider_and_model(self, provider: str, model_name: str) -> None:
        """Switch to a different provider and model WITHOUT changing profile.

        Models/providers define WHICH AI to use.
        This method changes the AI backend while preserving profile settings.

        Args:
            provider: Provider to switch to (e.g., "openai", "anthropic")
            model_name: Name of model to switch to
        """
        from consoul.tui.services import ProfileUIOrchestrator

        ProfileUIOrchestrator.switch_provider_and_model(
            self,
            self.consoul_config.core if self.consoul_config else None,
            provider,
            model_name,
        )
