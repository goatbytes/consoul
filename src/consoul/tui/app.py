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
    from textual import events
    from textual.binding import BindingType

    from consoul.ai.history import ConversationHistory
    from consoul.ai.title_generator import TitleGenerator
    from consoul.ai.tools import ToolRegistry
    from consoul.ai.tools.parser import ParsedToolCall
    from consoul.config import ConsoulConfig
    from consoul.config.models import ProfileConfig
    from consoul.sdk.models import Attachment, ToolRequest
    from consoul.sdk.services.conversation import ConversationService
    from consoul.tui.widgets import (
        ContextualTopBar,
        InputArea,
        StreamingResponse,
    )
    from consoul.tui.widgets.input_area import AttachedFile

    T = TypeVar("T")

from consoul.ai.reasoning import extract_reasoning
from consoul.tui.config import TuiConfig
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
from consoul.tui.widgets import InputArea, MessageBubble

__all__ = ["ConsoulApp"]

logger = logging.getLogger(__name__)


# Custom Messages for tool approval workflow
class ToolApprovalRequested(Message):
    """Message emitted when tool approval is needed.

    This message is sent to trigger the approval modal outside
    the streaming context, allowing proper modal interaction.
    """

    def __init__(
        self,
        tool_call: ParsedToolCall,
    ) -> None:
        """Initialize tool approval request message.

        Args:
            tool_call: Parsed tool call needing approval
        """
        super().__init__()
        self.tool_call = tool_call


class ToolApprovalResult(Message):
    """Message emitted after user approves/denies tool.

    This message triggers tool execution and AI continuation.
    """

    def __init__(
        self,
        tool_call: ParsedToolCall,
        approved: bool,
        reason: str | None = None,
    ) -> None:
        """Initialize tool approval result message.

        Args:
            tool_call: Parsed tool call that was approved/denied
            approved: Whether user approved execution
            reason: Reason for denial (if not approved)
        """
        super().__init__()
        self.tool_call = tool_call
        self.approved = approved
        self.reason = reason


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
        consoul_config: ConsoulConfig | None = None,
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
        self.consoul_config: ConsoulConfig | None = consoul_config

        # Initialize AI components to None (populated by async init)
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
        self._tool_call_data: dict[str, dict[str, Any]] = {}
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

    def _load_config(self) -> ConsoulConfig:
        """Load Consoul configuration from file.

        Returns:
            Loaded ConsoulConfig instance

        Raises:
            Exception: If config loading fails
        """
        from consoul.config import load_config

        return load_config()

    def _initialize_ai_model(self, config: ConsoulConfig) -> BaseChatModel:
        """Initialize AI chat model from config.

        Args:
            config: ConsoulConfig with provider/model settings

        Returns:
            Initialized BaseChatModel instance

        Raises:
            Exception: If model initialization fails
        """
        from consoul.ai import get_chat_model

        model_config = config.get_current_model_config()
        return get_chat_model(model_config, config=config)

    def _initialize_conversation(
        self, config: ConsoulConfig, model: BaseChatModel
    ) -> ConversationHistory:
        """Create conversation history with model.

        Args:
            config: ConsoulConfig for conversation settings
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

    def _initialize_tool_registry(self, config: ConsoulConfig) -> ToolRegistry | None:
        """Initialize tool registry with configured tools.

        Args:
            config: ConsoulConfig with tool settings

        Returns:
            Initialized ToolRegistry or None if tools disabled
        """
        # Check if tools are enabled
        if not config.tools or not config.tools.enabled:
            return None

        # Import all tool modules
        from consoul.ai.tools import ToolRegistry
        from consoul.ai.tools.catalog import (
            TOOL_CATALOG,
            get_all_tool_names,
            get_tool_by_name,
            get_tools_by_risk_level,
        )
        from consoul.ai.tools.implementations import (
            set_analyze_images_config,
            set_bash_config,
            set_code_search_config,
            set_file_edit_config,
            set_find_references_config,
            set_grep_search_config,
            set_read_config,
            set_read_url_config,
            set_web_search_config,
            set_wikipedia_config,
        )
        from consoul.ai.tools.providers import CliApprovalProvider

        # Configure bash tool with profile settings
        if config.tools.bash:
            set_bash_config(config.tools.bash)

        # Configure read tool with profile settings
        if config.tools.read:
            set_read_config(config.tools.read)

        # Configure grep_search tool with profile settings
        if config.tools.grep_search:
            set_grep_search_config(config.tools.grep_search)

        # Configure code_search tool with profile settings
        if config.tools.code_search:
            set_code_search_config(config.tools.code_search)

        # Configure find_references tool with profile settings
        if config.tools.find_references:
            set_find_references_config(config.tools.find_references)

        # Configure web_search tool with profile settings
        if config.tools.web_search:
            set_web_search_config(config.tools.web_search)

        # Configure wikipedia_search tool with profile settings
        if config.tools.wikipedia:
            set_wikipedia_config(config.tools.wikipedia)

        # Configure read_url tool with profile settings
        if config.tools.read_url:
            set_read_url_config(config.tools.read_url)

        # Configure file_edit tool with profile settings
        if config.tools.file_edit:
            set_file_edit_config(config.tools.file_edit)

        # Configure image_analysis tool with profile settings
        if config.tools.image_analysis:
            set_analyze_images_config(config.tools.image_analysis)

        # Determine which tools to register based on config
        # Note: We always register ALL tools in the registry so Tool Manager can show them all
        # The enabled/disabled state is set based on config (allowed_tools, risk_filter, or default)

        # Get all available tools
        all_tools = list(TOOL_CATALOG.values())

        # Determine which tools should be ENABLED based on config
        # Precedence: allowed_tools > risk_filter > all tools (default)
        enabled_tool_names = set()  # Set of tool.name values that should be enabled

        if config.tools.allowed_tools is not None:
            # Explicit whitelist takes precedence (even if empty)
            normalized_tool_names = []  # Actual tool.name values for registry
            invalid_tools = []

            for tool_name in config.tools.allowed_tools:
                result = get_tool_by_name(tool_name)
                if result:
                    tool, risk_level, _categories = result
                    # Store the actual tool.name for execution whitelist
                    normalized_tool_names.append(tool.name)
                    enabled_tool_names.add(tool.name)
                else:
                    invalid_tools.append(tool_name)

            # Error if any invalid tool names
            if invalid_tools:
                available = get_all_tool_names()
                raise ValueError(
                    f"Invalid tool names in allowed_tools: {invalid_tools}. "
                    f"Available tools: {available}"
                )

            # Normalize allowed_tools to actual tool.name values for execution checks
            # This ensures friendly names like "bash" work with ToolRegistry.is_allowed()
            # which checks against tool.name like "bash_execute"
            config.tools.allowed_tools = normalized_tool_names

            self.log.info(
                f"Enabled {len(enabled_tool_names)} tools from allowed_tools "
                f"{'(chat-only mode)' if len(enabled_tool_names) == 0 else 'whitelist'}"
            )

        elif config.tools.risk_filter:
            # Risk-based filtering: enable tools up to specified risk level
            tools_by_risk = get_tools_by_risk_level(config.tools.risk_filter)

            # Enable tools that match risk filter
            for tool, _risk_level, _categories in tools_by_risk:
                enabled_tool_names.add(tool.name)

            # DO NOT populate allowed_tools - leave empty for risk_filter.
            #
            # Why: Populating allowed_tools would bypass risk-based approval workflow.
            # The approval flow checks _is_whitelisted() BEFORE checking risk levels,
            # so adding all filtered tools to allowed_tools would auto-approve them
            # regardless of permission_policy settings (src/consoul/ai/tools/permissions/policy.py:307).
            #
            # Security model:
            # - risk_filter controls which tools are ENABLED
            # - permission_policy controls APPROVAL (which tools need confirmation)
            # - Both work together: risk_filter limits capabilities, policy controls UX
            #
            # Example: risk_filter="caution" + permission_policy="balanced"
            # - Enables: SAFE + CAUTION tools (12 total)
            # - Auto-approves: SAFE tools only
            # - Prompts for: CAUTION tools (file edits, bash, etc.)
            #
            # Note: risk_filter is incompatible with approval_mode="whitelist".
            # Use permission_policy (BALANCED/TRUSTING/etc) instead.

            self.log.info(
                f"Enabled {len(enabled_tool_names)} tools with "
                f"risk_filter='{config.tools.risk_filter}'"
            )

        else:
            # Default: enable all tools (backward compatible)
            for tool, _risk_level, _categories in all_tools:
                enabled_tool_names.add(tool.name)

            self.log.info(
                f"Enabled all {len(enabled_tool_names)} available tools (no filters specified)"
            )

        # Create registry with CLI provider (we override approval in _request_tool_approval)
        # The provider is required by registry but we don't use it - we show our own modal
        # NOTE: If allowed_tools was specified, it has been normalized to actual tool names
        tool_registry = ToolRegistry(
            config=config.tools,
            approval_provider=CliApprovalProvider(),  # Required but unused
        )

        # Register ALL tools with appropriate enabled state
        # This ensures Tool Manager shows all available tools (not just enabled ones)
        for tool, risk_level, _categories in all_tools:
            # Tool is enabled if its name is in the enabled_tool_names set
            is_enabled = tool.name in enabled_tool_names
            tool_registry.register(tool, risk_level=risk_level, enabled=is_enabled)

        # NOTE: analyze_images tool registration disabled for SOUL-116
        # The tool is meant for LLM-initiated image analysis, but for SOUL-116
        # we handle image references directly by creating multimodal messages.
        # Re-enable this when implementing SOUL-115 use case.
        # self._sync_vision_tool_registration()

        # Get tool metadata list
        tool_metadata_list = tool_registry.list_tools(enabled_only=True)

        self.log.info(
            f"Initialized tool registry with {len(tool_metadata_list)} enabled tools"
        )

        # Set tools_total for top bar display (total registered tools)
        if hasattr(self, "top_bar"):
            self.top_bar.tools_total = len(all_tools)

        return tool_registry

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

    def _bind_tools_to_model(
        self, model: BaseChatModel, tool_registry: ToolRegistry
    ) -> BaseChatModel:
        """Bind tools to chat model if supported.

        Args:
            model: Chat model to bind tools to
            tool_registry: Registry with enabled tools

        Returns:
            Model with tools bound (or original if not supported)
        """
        from typing import cast

        from consoul.ai.providers import supports_tool_calling

        # Get enabled tools
        tool_metadata_list = tool_registry.list_tools(enabled_only=True)

        if not tool_metadata_list:
            return model

        # Check if model supports tool calling
        if not supports_tool_calling(model):
            self.log.warning(
                f"Model {self.current_model} does not support tool calling. "
                "Tools are disabled for this model."
            )
            return model

        # Bind tools
        tools = [meta.tool for meta in tool_metadata_list]
        # bind_tools() returns a Runnable, but it's compatible with BaseChatModel interface
        bound_model = cast("BaseChatModel", model.bind_tools(tools))
        self.log.info(f"Bound {len(tools)} tools to chat model")

        # Update conversation's model reference if conversation exists
        if self.conversation:
            self.conversation._model = bound_model

        return bound_model

    def _initialize_title_generator(
        self, config: ConsoulConfig
    ) -> TitleGenerator | None:
        """Initialize title generator if enabled.

        Args:
            config: ConsoulConfig with title generator settings

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
                detected = auto_detect_title_config(config)
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
                config=config,
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
        """Initialize app components asynchronously with progress updates.

        This method orchestrates the entire initialization sequence, calling
        each extracted initialization method in order while updating the
        loading screen with progress (if enabled).

        Progress stages:
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
        import asyncio
        import logging
        import time

        logger = logging.getLogger(__name__)

        # Get reference to the loading screen (may be None if disabled)
        loading_screen = None
        if self.config.show_loading_screen and self.screen_stack:
            loading_screen = self.screen

        # Give the screen a moment to render (if present)
        if loading_screen:
            await asyncio.sleep(0.05)

        try:
            # Step 1: Load config (10%)
            step_start = time.time()
            if loading_screen:
                loading_screen.update_progress("Loading configuration...", 10)  # type: ignore[attr-defined]
                await asyncio.sleep(0.1)  # Ensure loading screen is visible

            consoul_config: ConsoulConfig | None
            if self._needs_config_load:
                consoul_config = await self._run_in_thread(self._load_config)
                self.consoul_config = consoul_config
            else:
                consoul_config = self.consoul_config
            logger.info(
                f"[PERF] Step 1 (Load config): {(time.time() - step_start) * 1000:.1f}ms"
            )

            # If no config, skip initialization
            if not consoul_config:
                logger.warning("No configuration available, skipping AI initialization")
                if loading_screen:
                    loading_screen.update_progress("Ready!", 100)  # type: ignore[attr-defined]
                    await asyncio.sleep(0.5)
                    await loading_screen.fade_out(duration=0.5)  # type: ignore[attr-defined]
                    self.pop_screen()
                self._initialization_complete = True
                # Still do post-init setup
                await self._post_initialization_setup()
                return

            # Set active profile
            self.active_profile = consoul_config.get_active_profile()
            assert self.active_profile is not None, (
                "Active profile should be available from config"
            )
            self.current_profile = self.active_profile.name
            self.current_model = consoul_config.current_model

            # Step 2: Initialize AI model (40%)
            step_start = time.time()
            if loading_screen:
                loading_screen.update_progress("Connecting to AI provider...", 40)  # type: ignore[attr-defined]
            self.chat_model = await self._run_in_thread(
                self._initialize_ai_model, consoul_config
            )
            logger.info(
                f"[PERF] Step 2 (Initialize AI model): {(time.time() - step_start) * 1000:.1f}ms"
            )

            # Step 3: Create conversation (50%)
            step_start = time.time()
            if loading_screen:
                loading_screen.update_progress("Initializing conversation...", 50)  # type: ignore[attr-defined]

            # Add detailed profiling to understand what's slow
            import logging as log_module

            conv_logger = log_module.getLogger("consoul.ai.history")
            original_level = conv_logger.level
            conv_logger.setLevel(log_module.DEBUG)

            self.conversation = await self._run_in_thread(
                self._initialize_conversation, consoul_config, self.chat_model
            )

            conv_logger.setLevel(original_level)
            logger.info(
                f"[PERF] Step 3 (Create conversation): {(time.time() - step_start) * 1000:.1f}ms"
            )

            # Set conversation ID for tracking
            self.conversation_id = self.conversation.session_id
            logger.info(
                f"Initialized AI model: {consoul_config.current_model}, "
                f"session: {self.conversation_id}"
            )

            # Step 4: Load tools (60%)
            step_start = time.time()
            if loading_screen:
                loading_screen.update_progress("Loading tools...", 60)  # type: ignore[attr-defined]
            self.tool_registry = await self._run_in_thread(
                self._initialize_tool_registry, consoul_config
            )
            logger.info(
                f"[PERF] Step 4 (Load tools): {(time.time() - step_start) * 1000:.1f}ms"
            )

            # Step 5: Bind tools (80%)
            if self.tool_registry:
                step_start = time.time()
                if loading_screen:
                    loading_screen.update_progress("Binding tools to model...", 80)  # type: ignore[attr-defined]
                self.chat_model = await self._run_in_thread(
                    self._bind_tools_to_model, self.chat_model, self.tool_registry
                )
                logger.info(
                    f"[PERF] Step 5 (Bind tools): {(time.time() - step_start) * 1000:.1f}ms"
                )

            # Step 5.5: Initialize ConversationService (SDK layer)
            step_start = time.time()
            if loading_screen:
                loading_screen.update_progress(  # type: ignore[attr-defined]
                    "Initializing conversation service...", 85
                )

            from consoul.sdk.services.conversation import ConversationService

            self.conversation_service = ConversationService(
                model=self.chat_model,
                conversation=self.conversation,
                tool_registry=self.tool_registry,
                config=consoul_config,
            )
            logger.info(
                f"[PERF] Step 5.5 (Initialize ConversationService): {(time.time() - step_start) * 1000:.1f}ms"
            )

            # Step 6: Auto-resume if enabled (90%)
            if (
                self.active_profile
                and hasattr(self.active_profile, "conversation")
                and self.active_profile.conversation.auto_resume
                and self.active_profile.conversation.persist
            ):
                step_start = time.time()
                if loading_screen:
                    loading_screen.update_progress("Restoring conversation...", 90)  # type: ignore[attr-defined]
                self.conversation = await self._run_in_thread(
                    self._auto_resume_if_enabled, self.conversation, self.active_profile
                )
                self.conversation_id = self.conversation.session_id
                logger.info(
                    f"[PERF] Step 6 (Auto-resume): {(time.time() - step_start) * 1000:.1f}ms"
                )

            # Cleanup old conversations (retention policy)
            if self.active_profile:
                step_start = time.time()
                await self._run_in_thread(
                    self._cleanup_old_conversations, self.active_profile
                )
                logger.info(
                    f"[PERF] Cleanup old conversations: {(time.time() - step_start) * 1000:.1f}ms"
                )

            # One-time cleanup of empty conversations from old versions
            # (Before deferred conversation creation was implemented)
            if self.conversation and self.conversation._db:
                step_start = time.time()
                try:
                    deleted = await self._run_in_thread(
                        self.conversation._db.delete_empty_conversations
                    )
                    if deleted > 0:
                        logger.info(f"Cleaned up {deleted} legacy empty conversations")
                except Exception as e:
                    logger.warning(f"Failed to cleanup empty conversations: {e}")
                logger.info(
                    f"[PERF] Cleanup empty conversations: {(time.time() - step_start) * 1000:.1f}ms"
                )

            # Initialize title generator
            step_start = time.time()
            self.title_generator = await self._run_in_thread(
                self._initialize_title_generator, consoul_config
            )
            logger.info(
                f"[PERF] Initialize title generator: {(time.time() - step_start) * 1000:.1f}ms"
            )

            # Apply theme BEFORE showing main UI (prevents background color flash)
            step_start = time.time()
            self.register_theme(CONSOUL_DARK)
            self.register_theme(CONSOUL_LIGHT)
            self.register_theme(CONSOUL_OLED)
            self.register_theme(CONSOUL_MIDNIGHT)
            self.register_theme(CONSOUL_MATRIX)
            self.register_theme(CONSOUL_SUNSET)
            self.register_theme(CONSOUL_OCEAN)
            self.register_theme(CONSOUL_VOLCANO)
            self.register_theme(CONSOUL_NEON)
            self.register_theme(CONSOUL_FOREST)
            try:
                self.theme = self.config.theme
                logger.info(f"[PERF] Applied theme: {self.config.theme}")
            except Exception as e:
                logger.warning(f"Failed to set theme '{self.config.theme}': {e}")
                self.theme = "textual-dark"

            # Give Textual a moment to apply theme CSS to all widgets
            await asyncio.sleep(0.25)

            logger.info(
                f"[PERF] Apply theme: {(time.time() - step_start) * 1000:.1f}ms"
            )

            # Step 7: Complete (100%)
            if loading_screen:
                loading_screen.update_progress("Ready!", 100)  # type: ignore[attr-defined]
                await loading_screen.fade_out(duration=0.5)  # type: ignore[attr-defined]
                self.pop_screen()

            self._initialization_complete = True

            # Post-initialization setup
            await self._post_initialization_setup()

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

        Extracts all conversation settings from the profile and prepares them
        for passing to ConversationHistory constructor. Handles summary_model
        initialization if specified.

        Returns:
            Dictionary of kwargs for ConversationHistory constructor with keys:
            persist, db_path, summarize, summarize_threshold, keep_recent,
            summary_model, max_tokens

        Note:
            session_id should be added separately when resuming conversations.
        """
        from consoul.ai import get_chat_model

        kwargs: dict[str, Any] = {}

        if self.active_profile and hasattr(self.active_profile, "conversation"):
            conv_config = self.active_profile.conversation

            # Basic persistence settings
            kwargs["persist"] = conv_config.persist
            if conv_config.db_path:
                kwargs["db_path"] = conv_config.db_path

            # Summarization settings
            kwargs["summarize"] = conv_config.summarize
            kwargs["summarize_threshold"] = conv_config.summarize_threshold
            kwargs["keep_recent"] = conv_config.keep_recent

            # Summary model (needs to be initialized as ChatModel instance)
            if conv_config.summary_model and self.consoul_config:
                try:
                    kwargs["summary_model"] = get_chat_model(
                        conv_config.summary_model, config=self.consoul_config
                    )
                except Exception as e:
                    self.log.warning(
                        f"Failed to initialize summary_model '{conv_config.summary_model}': {e}"
                    )
                    kwargs["summary_model"] = None
            else:
                kwargs["summary_model"] = None

            # Context settings - pass max_context_tokens from profile
            # Note: 0 or None in ConversationHistory means auto-size to 75% of model capacity
            if hasattr(self.active_profile, "context"):
                context_config = self.active_profile.context
                kwargs["max_tokens"] = context_config.max_context_tokens
        else:
            # Fallback to defaults if profile not available
            kwargs = {
                "persist": True,
                "summarize": False,
                "summarize_threshold": 20,
                "keep_recent": 10,
                "summary_model": None,
                "max_tokens": None,  # Auto-size
            }

        return kwargs

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

        Injects environment context (OS, working directory, git info) based on
        profile settings, then replaces {AVAILABLE_TOOLS} marker with dynamically
        generated tool documentation.

        Returns:
            Complete system prompt with environment context and tool docs, or None
        """
        from consoul.ai.environment import get_environment_context
        from consoul.ai.prompt_builder import build_system_prompt

        if not self.active_profile or not self.active_profile.system_prompt:
            return None

        # Start with base system prompt
        base_prompt = self.active_profile.system_prompt

        # Inject environment context if enabled
        include_system = (
            self.active_profile.context.include_system_info
            if hasattr(self.active_profile, "context")
            else True
        )
        include_git = (
            self.active_profile.context.include_git_info
            if hasattr(self.active_profile, "context")
            else True
        )

        if include_system or include_git:
            env_context = get_environment_context(
                include_system_info=include_system,
                include_git_info=include_git,
            )
            if env_context:
                # Prepend environment context to system prompt
                base_prompt = f"{env_context}\n\n{base_prompt}"
                self.log.debug(
                    f"Injected environment context ({len(env_context)} chars)"
                )

        # Build final system prompt with tool documentation
        return build_system_prompt(base_prompt, self.tool_registry)

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

        Loads and encodes images, then formats them according to the current
        provider's requirements (Anthropic, OpenAI, Google, Ollama).

        Args:
            user_message: The user's text message
            image_paths: List of valid image file paths to include

        Returns:
            HumanMessage with multimodal content (text + images)

        Raises:
            Exception: If image loading, encoding, or formatting fails
        """
        logger.info("[IMAGE_DETECTION] _create_multimodal_message called")
        import base64
        import mimetypes
        from pathlib import Path

        from consoul.ai.multimodal import format_vision_message

        # Load and encode images
        encoded_images = []
        logger.info(f"[IMAGE_DETECTION] Loading {len(image_paths)} image(s)")
        for path_str in image_paths:
            path = Path(path_str)

            # Detect MIME type
            mime_type, _ = mimetypes.guess_type(str(path))
            if not mime_type or not mime_type.startswith("image/"):
                raise ValueError(f"Invalid MIME type for {path.name}: {mime_type}")

            # Read and encode image
            with open(path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            encoded_images.append(
                {"path": str(path), "data": image_data, "mime_type": mime_type}
            )

        # Get current provider from model config
        if not self.consoul_config:
            raise ValueError("Config not available for multimodal message creation")

        model_config = self.consoul_config.get_current_model_config()
        provider = model_config.provider
        logger.info(f"[IMAGE_DETECTION] Using provider: {provider}")

        # Format message for the provider
        logger.info(
            f"[IMAGE_DETECTION] Calling format_vision_message with {len(encoded_images)} image(s)"
        )
        result = format_vision_message(provider, user_message, encoded_images)
        logger.info(f"[IMAGE_DETECTION] format_vision_message returned: {type(result)}")
        return result

    def _update_top_bar_state(self) -> None:
        """Update ContextualTopBar reactive properties from app state."""
        try:
            if not hasattr(self, "top_bar"):
                return

            # Update provider and model (from config, not profile)
            if self.consoul_config:
                self.top_bar.current_provider = (
                    self.consoul_config.current_provider.value
                )
                self.top_bar.current_model = self.consoul_config.current_model
            else:
                self.top_bar.current_provider = ""
                self.top_bar.current_model = self.current_model

            # Update profile name
            self.top_bar.current_profile = self.current_profile

            # Update streaming status
            self.top_bar.streaming = self.streaming

            # Update conversation count
            if hasattr(self, "conversation_list") and self.conversation_list:
                self.top_bar.conversation_count = (
                    self.conversation_list.conversation_count
                )
            else:
                self.top_bar.conversation_count = 0

            # Update tool status
            if self.tool_registry:
                # Get enabled tools
                enabled_tools = self.tool_registry.list_tools(enabled_only=True)
                self.top_bar.tools_enabled = len(enabled_tools)

                # Determine highest risk level
                if not enabled_tools:
                    self.top_bar.highest_risk = "none"
                else:
                    from consoul.ai.tools.base import RiskLevel

                    # Find highest risk among enabled tools
                    risk_hierarchy = {
                        RiskLevel.SAFE: 0,
                        RiskLevel.CAUTION: 1,
                        RiskLevel.DANGEROUS: 2,
                    }

                    max_risk = max(
                        risk_hierarchy.get(meta.risk_level, 0) for meta in enabled_tools
                    )

                    # Map back to string
                    if max_risk == 2:
                        self.top_bar.highest_risk = "dangerous"
                    elif max_risk == 1:
                        self.top_bar.highest_risk = "caution"
                    else:
                        self.top_bar.highest_risk = "safe"
            else:
                # No registry (shouldn't happen, but defensive)
                self.top_bar.tools_enabled = 0
                self.top_bar.highest_risk = "none"

        except Exception as e:
            logger.error(f"Error updating top bar state: {e}", exc_info=True)

    def _rebind_tools(self) -> None:
        """Rebind tools to chat model after registry changes.

        Called after tool manager applies changes to refresh the model's
        available tools based on current enabled state.
        """
        if not self.tool_registry or not self.chat_model:
            return

        try:
            from consoul.ai.providers import supports_tool_calling

            # Get currently enabled tools
            enabled_tools = self.tool_registry.list_tools(enabled_only=True)

            if enabled_tools and supports_tool_calling(self.chat_model):
                # Extract BaseTool instances
                tools = [meta.tool for meta in enabled_tools]

                # Rebind tools to model
                self.chat_model = self.chat_model.bind_tools(tools)  # type: ignore[assignment]

                self.log.info(f"Rebound {len(tools)} tools to chat model")

                # Update conversation's model reference so it uses the rebound model
                if self.conversation:
                    self.conversation._model = self.chat_model

                # Update top bar to reflect changes
                self._update_top_bar_state()

                # Update system prompt to reflect new tool availability
                system_prompt = self._build_current_system_prompt()
                if self.conversation is not None and system_prompt:
                    self.conversation.clear(preserve_system=False)
                    self.conversation.add_system_message(system_prompt)
                    # Store updated prompt metadata
                    self.conversation.store_system_prompt_metadata(
                        profile_name=self.active_profile.name
                        if self.active_profile
                        else None,
                        tool_count=len(enabled_tools),
                    )
                    self.log.info("Updated system prompt with new tool availability")
            elif not enabled_tools:
                # No tools enabled - need to recreate model without tool bindings
                # LangChain doesn't provide an "unbind" method, so we recreate the model
                self.log.info("No tools enabled - recreating model without tools")

                from consoul.ai import get_chat_model

                if self.consoul_config:
                    model_config = self.consoul_config.get_current_model_config()
                    self.chat_model = get_chat_model(
                        model_config, config=self.consoul_config
                    )

                    # Update conversation's model reference
                    if self.conversation:
                        self.conversation._model = self.chat_model

                    self.log.info("Recreated model without tool bindings")

                self._update_top_bar_state()

                # Update system prompt to show no tools available
                system_prompt = self._build_current_system_prompt()
                if self.conversation is not None and system_prompt:
                    self.conversation.clear(preserve_system=False)
                    self.conversation.add_system_message(system_prompt)
                    # Store updated prompt metadata
                    self.conversation.store_system_prompt_metadata(
                        profile_name=self.active_profile.name
                        if self.active_profile
                        else None,
                        tool_count=0,
                    )
                    self.log.info("Updated system prompt - no tools available")

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

        Simplified streaming that delegates all business logic to the service layer,
        keeping only UI presentation logic in the TUI.

        Args:
            content: User message content
            attachments: Optional list of file attachments
        """
        from consoul.tui.widgets import MessageBubble, StreamingResponse

        if not self.conversation_service:
            error_bubble = MessageBubble(
                "ConversationService not initialized",
                role="error",
                show_metadata=False,
            )
            await self.chat_view.add_message(error_bubble)
            return

        # Update streaming state
        self.streaming = True
        self._update_top_bar_state()

        try:
            # Create tool approver for this conversation
            tool_approver = TUIToolApprover(self)

            # Stream tokens from service
            collected_content = []
            total_cost = 0.0
            stream_widget = None
            first_token = True

            async for token in self.conversation_service.send_message(
                content,
                attachments=attachments,
                on_tool_request=tool_approver.on_tool_request,
            ):
                # On first token, hide typing indicator and show stream widget
                if first_token:
                    await self.chat_view.hide_typing_indicator()
                    stream_widget = StreamingResponse(renderer="hybrid")
                    await self.chat_view.add_message(stream_widget)
                    self._current_stream = stream_widget
                    first_token = False

                # Check for cancellation
                if self._stream_cancelled:
                    break

                # Collect content
                collected_content.append(token.content)

                # Update cost if available
                if token.cost is not None:
                    total_cost += token.cost

                # Update streaming widget
                if stream_widget:
                    await stream_widget.add_token(token.content)

            # If cancelled, remove stream widget
            if self._stream_cancelled:
                if stream_widget:
                    await stream_widget.remove()
                return

            # Finalize stream if we got any tokens
            if stream_widget:
                final_content = "".join(collected_content)
                await stream_widget.finalize_stream()

                # Remove stream widget
                await stream_widget.remove()

                # Extract tool call data from conversation for MessageBubble button
                tool_calls_list = None
                if self.conversation:
                    from langchain_core.messages import AIMessage, ToolMessage

                    # Find the most recent AIMessage with tool_calls
                    ai_message = None
                    for msg in reversed(self.conversation.messages):
                        if isinstance(msg, AIMessage) and msg.tool_calls:
                            ai_message = msg
                            break

                    if ai_message and ai_message.tool_calls:
                        # Build tool_calls_list with results from ToolMessages
                        tool_calls_data = []
                        for tool_call in ai_message.tool_calls:
                            # Find corresponding ToolMessage result
                            result = None
                            status = "SUCCESS"
                            for msg in self.conversation.messages:
                                if (
                                    isinstance(msg, ToolMessage)
                                    and msg.tool_call_id == tool_call["id"]
                                ):
                                    result = msg.content
                                    # Check if result indicates error
                                    if (
                                        isinstance(result, str)
                                        and "error" in result.lower()
                                    ):
                                        status = "ERROR"
                                    break

                            tool_calls_data.append(
                                {
                                    "name": tool_call["name"],
                                    "arguments": tool_call["args"],
                                    "status": status,
                                    "result": result,
                                }
                            )

                        if tool_calls_data:
                            tool_calls_list = tool_calls_data

                # Convert to message bubble
                final_bubble = MessageBubble(
                    final_content,
                    role="assistant",
                    show_metadata=True,
                    estimated_cost=total_cost if total_cost > 0 else None,
                    tool_calls=tool_calls_list,
                )

                # Add final bubble to chat view
                await self.chat_view.add_message(final_bubble)
            else:
                # No tokens received - hide typing indicator and show error
                await self.chat_view.hide_typing_indicator()
                error_bubble = MessageBubble(
                    "No response received from AI",
                    role="error",
                    show_metadata=False,
                )
                await self.chat_view.add_message(error_bubble)

        except Exception as e:
            logger.error(f"Error streaming via ConversationService: {e}", exc_info=True)
            # Hide typing indicator if still showing
            await self.chat_view.hide_typing_indicator()
            error_bubble = MessageBubble(
                f"Error: {e!s}",
                role="error",
                show_metadata=False,
            )
            await self.chat_view.add_message(error_bubble)

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

        Args:
            event: MessageSubmit event containing user's message content
        """
        from consoul.tui.widgets import MessageBubble

        user_message = event.content

        # Inject pending command output if available
        if self._pending_command_output:
            command, output = self._pending_command_output
            prefix = f"""<shell_command>
Command: {command}
Output:
{output}
</shell_command>

"""
            user_message = prefix + user_message
            # Clear buffer after injection
            self._pending_command_output = None
            self.log.info("[COMMAND_INJECT] Injected command output into user message")

        # Check if AI model is available
        if self.chat_model is None or self.conversation is None:
            # Display error message
            error_bubble = MessageBubble(
                "AI model not initialized. Please check your configuration.\n\n"
                "Ensure you have:\n"
                "- A valid profile with model configuration\n"
                "- Required API keys set in environment or .env file\n"
                "- Provider packages installed (e.g., langchain-openai)",
                role="error",
                show_metadata=False,
            )
            await self.chat_view.add_message(error_bubble)
            return

        # Reset tool call tracking for new user message
        self._tool_call_data = {}
        self._tool_results = {}
        self._tool_call_iterations = 0
        if hasattr(self, "_last_tool_signature"):
            del self._last_tool_signature

        # Clear the "user scrolled away" flag when they submit a new message
        # This re-enables auto-scroll for the new conversation turn
        # IMPORTANT: Clear this BEFORE adding the message so add_message() will scroll
        self.chat_view._user_scrolled_away = False

        # Add user message to chat view FIRST for immediate visual feedback
        user_bubble = MessageBubble(user_message, role="user", show_metadata=True)
        await self.chat_view.add_message(user_bubble)

        # Show typing indicator immediately
        await self.chat_view.show_typing_indicator()

        # The real issue: everything after this point blocks the event loop
        # We need to move ALL remaining work to a background worker
        # so the UI stays responsive during "Thinking..." phase

        # Track if this is the first message (conversation not yet in DB)
        is_first_message = (
            self.conversation.persist and not self.conversation._conversation_created
        )
        logger.debug(
            f"[MESSAGE_SUBMIT] is_first_message={is_first_message}, "
            f"persist={self.conversation.persist}, "
            f"_conversation_created={self.conversation._conversation_created}, "
            f"session_id={self.conversation.session_id}, "
            f"message_count={len(self.conversation.messages)}"
        )

        # Note: Message adding is now handled by ConversationService.send_message()
        # No need to manually create HumanMessage

        # Get attached files from InputArea
        input_area = self.query_one(InputArea)
        attached_files = input_area.attached_files.copy()

        # Separate images from text files
        attached_images = [f.path for f in attached_files if f.type == "image"]
        attached_text_files = [
            f for f in attached_files if f.type in {"code", "document", "data"}
        ]

        # Check for image references in the user message
        from consoul.tui.utils.image_parser import extract_image_paths

        # Get image analysis config to check if auto-detection is enabled
        auto_detect_enabled = False
        if self.consoul_config and self.consoul_config.tools:
            image_tool_config = self.consoul_config.tools.image_analysis
            auto_detect_enabled = getattr(
                image_tool_config, "auto_detect_in_messages", False
            )

        _original_message, auto_detected_paths = extract_image_paths(user_message)

        # Combine attached images with auto-detected paths and deduplicate
        all_image_paths = list(set(attached_images + auto_detected_paths))

        # Debug logging
        logger.info(
            f"[IMAGE_DETECTION] Auto-detect enabled: {auto_detect_enabled}, "
            f"Attached images: {len(attached_images)}, Auto-detected: {len(auto_detected_paths)}, "
            f"Total (deduplicated): {len(all_image_paths)}"
        )
        if all_image_paths:
            logger.info(f"[IMAGE_DETECTION] Image paths: {all_image_paths}")
        model_supports_vision = self._model_supports_vision()
        logger.info(f"[IMAGE_DETECTION] Model supports vision: {model_supports_vision}")

        # Handle text file attachments - prepend to message
        final_message = user_message
        if attached_text_files:
            text_content_parts = []
            for file in attached_text_files:
                try:
                    from pathlib import Path

                    path_obj = Path(file.path)
                    # Limit to 10KB per file
                    if path_obj.stat().st_size > 10 * 1024:
                        logger.warning(
                            f"Skipping large file {path_obj.name} ({path_obj.stat().st_size} bytes)"
                        )
                        continue

                    content = path_obj.read_text(encoding="utf-8")
                    text_content_parts.append(
                        f"--- {path_obj.name} ---\n{content}\n--- End of {path_obj.name} ---"
                    )
                except Exception as e:
                    logger.error(f"Failed to read file {file.path}: {e}")
                    continue

            # Prepend file contents to message
            if text_content_parts:
                final_message = "\n\n".join(text_content_parts) + "\n\n" + user_message

        # Create multimodal message if:
        # 1. Images found (attached or auto-detected)
        # 2. Model supports vision
        logger.info(
            f"[IMAGE_DETECTION] Condition check: "
            f"image_paths={bool(all_image_paths)}, model_supports_vision={model_supports_vision}, "
            f"combined={bool(all_image_paths) and model_supports_vision}"
        )
        if all_image_paths and model_supports_vision:
            logger.info("[IMAGE_DETECTION] ENTERING multimodal message creation block")
            try:
                logger.info(
                    f"[IMAGE_DETECTION] About to call _create_multimodal_message with {len(all_image_paths)} image(s)"
                )
                # Note: Multimodal message creation is now handled by ConversationService
                logger.info(
                    f"[IMAGE_DETECTION] Will pass {len(all_image_paths)} image(s) to ConversationService"
                )
            except Exception as e:
                # Fall back to text-only message and show error
                import traceback

                logger.error(
                    f"[IMAGE_DETECTION] Failed to create multimodal message: {e}"
                )
                logger.error(f"[IMAGE_DETECTION] Traceback: {traceback.format_exc()}")
                error_bubble = MessageBubble(
                    f"❌ Failed to process image(s): {e}\n\n"
                    "Continuing with text-only message.",
                    role="error",
                    show_metadata=False,
                )
                await self.chat_view.add_message(error_bubble)

        # Note: Message creation is now handled by ConversationService
        # The service will create the appropriate message (text or multimodal) from content and attachments

        # Clear attached files after processing
        input_area.attached_files.clear()
        input_area._update_file_chips()

        # Move EVERYTHING to a background worker to keep UI responsive
        async def _process_and_stream() -> None:
            # NOTE: Message adding is now handled by ConversationService.send_message()
            # The service adds the message when streaming starts

            # Convert TUI AttachedFile to SDK Attachment format
            from consoul.sdk.models import Attachment

            sdk_attachments = [
                Attachment(path=f.path, type=f.type) for f in attached_files
            ]

            # Add new conversation to list if first message
            # Do this before streaming so the conversation appears immediately
            if (
                is_first_message
                and hasattr(self, "conversation_list")
                and self.conversation_id
            ):
                await self.conversation_list.prepend_conversation(self.conversation_id)
                self._update_top_bar_state()

            # Start streaming AI response via ConversationService
            # This will add the message to conversation before yielding tokens
            await self._stream_via_conversation_service(
                content=final_message,
                attachments=sdk_attachments if sdk_attachments else None,
            )

            # Persist attachments after streaming completes (message is now in conversation)
            user_message_id = None
            if (
                self.conversation is not None
                and self.conversation.persist
                and self.conversation._db
                and self.conversation.session_id
                and attached_files
            ):
                # Get the persisted message ID
                try:
                    messages = self.conversation._db.load_conversation(
                        self.conversation.session_id
                    )
                    # Find the user message we just added (should be second-to-last, before AI response)
                    if len(messages) >= 2:
                        # Look for the last human message
                        for msg in reversed(messages):
                            if msg.get("role") == "user":
                                user_message_id = msg.get("id")
                                break

                    if user_message_id:
                        logger.debug(
                            f"Persisting {len(attached_files)} attachments to message {user_message_id}"
                        )
                        await self._persist_attachments(user_message_id, attached_files)
                        logger.debug("Attachments persisted successfully")
                    else:
                        logger.warning(
                            "Could not find user message ID for attachment persistence"
                        )
                except Exception as e:
                    logger.error(f"Failed to persist attachments: {e}", exc_info=True)

        # Fire off all processing in background worker
        # This keeps the UI responsive during the entire "Thinking..." phase
        self.run_worker(_process_and_stream(), exclusive=False)

    async def on_input_area_command_execute_requested(
        self, event: InputArea.CommandExecuteRequested
    ) -> None:
        """Handle inline shell command execution request.

        Args:
            event: CommandExecuteRequested event containing the command
        """
        import subprocess
        import time

        from consoul.tui.widgets.command_output_bubble import CommandOutputBubble

        command = event.command
        self.log.info(f"[COMMAND_EXEC] Executing inline command: {command}")

        # Execute command in background to avoid blocking UI
        start_time = time.time()

        try:
            # Run command with timeout
            result = await self._run_in_thread(
                subprocess.run,
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
                cwd=Path.cwd(),
            )

            execution_time = time.time() - start_time

            stdout = result.stdout
            stderr = result.stderr
            exit_code = result.returncode

            # Truncate output if too long (prevent UI freeze)
            max_lines = 1000
            if stdout:
                lines = stdout.split("\n")
                if len(lines) > max_lines:
                    first = lines[:50]
                    last = lines[-50:]
                    truncated = [
                        *first,
                        f"\n... truncated {len(lines) - 100} lines ...\n",
                        *last,
                    ]
                    stdout = "\n".join(truncated)

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

            self.log.info(
                f"[COMMAND_EXEC] Command completed with exit code {exit_code} in {execution_time:.2f}s"
            )

        except subprocess.TimeoutExpired:
            # Command timed out
            execution_time = time.time() - start_time

            error_bubble = CommandOutputBubble(
                command=command,
                stdout="",
                stderr="Command timed out after 30 seconds",
                exit_code=124,  # Standard timeout exit code
                execution_time=execution_time,
            )

            await self.chat_view.add_message(error_bubble)

            self.log.warning(f"[COMMAND_EXEC] Command timed out: {command}")
            self.notify("Command timed out after 30 seconds", severity="warning")

        except Exception as e:
            # Execution failed
            execution_time = time.time() - start_time

            error_bubble = CommandOutputBubble(
                command=command,
                stdout="",
                stderr=f"Execution failed: {e}",
                exit_code=1,
                execution_time=execution_time,
            )

            await self.chat_view.add_message(error_bubble)

            self.log.error(f"[COMMAND_EXEC] Execution failed: {e}", exc_info=True)
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
        import re
        import subprocess

        message = event.message
        self.log.info("[INLINE_COMMAND] Processing message with inline commands")

        # Find all !`command` patterns
        pattern = r"!\s*`([^`]+)`"
        matches = list(re.finditer(pattern, message))

        if not matches:
            # No commands found, send as regular message
            self.post_message(InputArea.MessageSubmit(message))
            return

        # Execute each command and build replacement map
        replacements = {}
        for match in matches:
            command = match.group(1)
            placeholder = match.group(0)  # Full pattern like !`command`

            self.log.info(f"[INLINE_COMMAND] Executing: {command}")

            try:
                # Execute command with timeout
                result = await self._run_in_thread(
                    subprocess.run,
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=Path.cwd(),
                )

                # Get output
                output = result.stdout.strip() if result.stdout else ""
                if result.stderr:
                    output += f"\n[stderr: {result.stderr.strip()}]"

                if result.returncode != 0:
                    output = (
                        f"[Command failed with exit code {result.returncode}]\n{output}"
                    )

                # Truncate if too long
                if len(output) > 10000:
                    output = output[:10000] + "\n... (output truncated)"

                replacements[placeholder] = output

            except subprocess.TimeoutExpired:
                replacements[placeholder] = "[Command timed out after 30 seconds]"
                self.log.warning(f"[INLINE_COMMAND] Timeout: {command}")

            except Exception as e:
                replacements[placeholder] = f"[Command failed: {e}]"
                self.log.error(f"[INLINE_COMMAND] Error: {e}", exc_info=True)

        # Replace all command patterns with their output
        processed_message = message
        for placeholder, output in replacements.items():
            processed_message = processed_message.replace(placeholder, output)

        self.log.info(f"[INLINE_COMMAND] Processed {len(replacements)} commands")

        # Send the processed message as a regular message
        self.post_message(InputArea.MessageSubmit(processed_message))

    async def on_tool_approval_requested(self, message: ToolApprovalRequested) -> None:
        """Handle tool approval request by showing modal.

        Uses callback pattern to handle approval result asynchronously.
        This is the correct pattern for showing modals from message handlers.

        Args:
            message: ToolApprovalRequested with tool_call and widget
        """
        logger.debug(
            f"[TOOL_FLOW] on_tool_approval_requested called for {message.tool_call.name}"
        )

        from consoul.ai.tools import ToolApprovalRequest
        from consoul.tui.widgets import ToolApprovalModal

        # Get dynamic risk assessment from registry
        if self.tool_registry is None:
            # Fallback to DANGEROUS if no registry (shouldn't happen)
            from consoul.ai.tools import RiskLevel
            from consoul.ai.tools.permissions.analyzer import CommandRisk

            risk_assessment = CommandRisk(
                level=RiskLevel.DANGEROUS,
                reason="No tool registry available",
            )
        else:
            try:
                risk_assessment = self.tool_registry.assess_risk(
                    message.tool_call.name,
                    message.tool_call.arguments,
                )
            except Exception as e:
                # Handle unregistered tools or assessment errors gracefully
                from consoul.ai.tools import RiskLevel
                from consoul.ai.tools.permissions.analyzer import CommandRisk

                self.log.warning(
                    f"Failed to assess risk for tool '{message.tool_call.name}': {e}"
                )
                risk_assessment = CommandRisk(
                    level=RiskLevel.DANGEROUS,
                    reason=f"Tool not found or assessment failed: {e}",
                )

        # Extract risk level and reason
        # assess_risk returns CommandRisk for all tools now
        from consoul.ai.tools import RiskLevel

        if hasattr(risk_assessment, "level"):
            # CommandRisk object
            risk_level: RiskLevel = risk_assessment.level
            risk_reason: str = risk_assessment.reason
        else:
            # Plain RiskLevel (backward compatibility - shouldn't happen)
            risk_level = risk_assessment  # type: ignore[assignment]
            risk_reason = f"Static risk level: {risk_level.value}"

        # If tool not found, immediately reject with helpful error
        if (
            risk_level == RiskLevel.DANGEROUS
            and "Tool not found" in risk_reason
            and self.tool_registry
        ):
            # Get available tools for error message
            tool_names = [t.name for t in self.tool_registry.list_tools()]
            available_tools = ", ".join(tool_names)
            error_msg = (
                f"Tool '{message.tool_call.name}' does not exist. "
                f"Available tools: {available_tools}"
            )
            self.log.warning(error_msg)

            # Send immediate rejection with helpful message
            self.post_message(
                ToolApprovalResult(
                    tool_call=message.tool_call,
                    approved=False,
                    reason=error_msg,
                )
            )
            return

        # Log approval request
        import time

        from consoul.ai.tools.audit import AuditEvent

        start_time = time.time()
        if self.tool_registry and self.tool_registry.audit_logger:
            await self.tool_registry.audit_logger.log_event(
                AuditEvent(
                    event_type="request",
                    tool_name=message.tool_call.name,
                    arguments=message.tool_call.arguments,
                )
            )

        # Check if approval is needed based on policy/whitelist
        # This enables:
        # - BALANCED policy to auto-approve SAFE commands
        # - Whitelisted commands to bypass approval
        # - TRUSTING policy to auto-approve SAFE+CAUTION commands
        logger.debug(
            f"[TOOL_FLOW] Checking if approval needed for {message.tool_call.name}"
        )
        try:
            needs_approval = (
                not self.tool_registry
                or self.tool_registry.needs_approval(
                    message.tool_call.name, message.tool_call.arguments
                )
            )
            logger.debug(
                f"[TOOL_FLOW] Approval check result: needs_approval={needs_approval}"
            )
        except Exception as e:
            # Tool not found or other error - require approval
            logger.error(
                f"[TOOL_FLOW] Error checking approval for '{message.tool_call.name}': {e}",
                exc_info=True,
            )
            needs_approval = True

        if not needs_approval:
            logger.debug(f"[TOOL_FLOW] Auto-approving {message.tool_call.name}")
            # Auto-approve based on policy or whitelist
            self.log.info(
                f"Auto-approving tool '{message.tool_call.name}' "
                f"(risk={risk_level.value}, reason={risk_reason})"
            )

            # Log auto-approval
            duration_ms = int((time.time() - start_time) * 1000)
            if self.tool_registry and self.tool_registry.audit_logger:
                await self.tool_registry.audit_logger.log_event(
                    AuditEvent(
                        event_type="approval",
                        tool_name=message.tool_call.name,
                        arguments=message.tool_call.arguments,
                        decision=True,
                        result=f"Auto-approved by policy ({risk_level.value})",
                        duration_ms=duration_ms,
                    )
                )

            self.post_message(
                ToolApprovalResult(
                    tool_call=message.tool_call,
                    approved=True,
                    reason=f"Auto-approved by policy ({risk_level.value})",
                )
            )
            return

        # Create approval request
        request = ToolApprovalRequest(
            tool_name=message.tool_call.name,
            arguments=message.tool_call.arguments,
            risk_level=risk_level,
            tool_call_id=message.tool_call.id,
            description=risk_reason,  # Add risk reason as description
        )

        # Define async callback to handle result and log audit event
        async def on_approval_result_async(approved: bool | None) -> None:
            """Handle approval modal dismissal with audit logging."""
            # Convert None to False (treat no response as denial)
            if approved is None:
                approved = False

            # Log approval/denial
            duration_ms = int((time.time() - start_time) * 1000)
            if self.tool_registry and self.tool_registry.audit_logger:
                await self.tool_registry.audit_logger.log_event(
                    AuditEvent(
                        event_type="approval" if approved else "denial",
                        tool_name=message.tool_call.name,
                        arguments=message.tool_call.arguments,
                        decision=approved,
                        result=None if approved else "User denied execution via modal",
                        duration_ms=duration_ms,
                    )
                )

            # Emit result message to trigger execution
            reason = None if approved else "User denied execution via modal"
            self.post_message(
                ToolApprovalResult(
                    tool_call=message.tool_call,
                    approved=bool(approved),
                    reason=reason,
                )
            )

        # Define sync wrapper for callback
        def on_approval_result(approved: bool | None) -> None:
            """Sync wrapper for async callback."""
            import asyncio

            # Create task to run async callback
            # Store reference to avoid task being garbage collected
            task = asyncio.create_task(on_approval_result_async(approved))
            # Add to set of background tasks to keep reference
            if not hasattr(self, "_audit_tasks"):
                self._audit_tasks: set[asyncio.Task[None]] = set()
            self._audit_tasks.add(task)
            task.add_done_callback(self._audit_tasks.discard)

        # Show modal with callback (non-blocking)
        # This is the correct pattern: push_screen with callback, not await
        modal = ToolApprovalModal(request)
        self.push_screen(modal, on_approval_result)

    async def on_tool_approval_result(self, message: ToolApprovalResult) -> None:
        """Handle tool approval result by executing tool.

        After execution, checks if all tools are done and continues AI response.

        Args:
            message: ToolApprovalResult with approval decision
        """
        import time

        from langchain_core.messages import ToolMessage

        from consoul.ai.tools.audit import AuditEvent

        logger.debug(
            f"[TOOL_FLOW] on_tool_approval_result: "
            f"tool={message.tool_call.name}, "
            f"approved={message.approved}, "
            f"call_id={message.tool_call.id}"
        )

        # Start timing for entire approval flow
        start_time = time.time()

        if message.approved:
            # Update tool call data to EXECUTING
            self._tool_call_data[message.tool_call.id]["status"] = "EXECUTING"
            logger.info(
                f"[TOOL_FLOW] Executing approved tool: {message.tool_call.name}"
            )

            # Log execution start
            if self.tool_registry and self.tool_registry.audit_logger:
                await self.tool_registry.audit_logger.log_event(
                    AuditEvent(
                        event_type="execution",
                        tool_name=message.tool_call.name,
                        arguments=message.tool_call.arguments,
                    )
                )

            # Yield control to allow UI to update and show "EXECUTING" status
            # This prevents the UI from appearing frozen during tool execution
            await asyncio.sleep(0.01)  # 10ms delay to let UI refresh

            # NOTE: This handler is obsolete (SOUL-265) - nothing posts ToolApprovalRequested
            # Tool execution now handled by ConversationService via TUIToolApprover
            # TODO: Remove entire on_tool_approval_result handler in follow-up ticket

            # Execute tool
            try:
                # FIXME: _execute_tool removed in SOUL-265, this code path unreachable
                result: str = ""  # Satisfy linter - this code is never reached
                raise NotImplementedError("Tool execution moved to ConversationService")
                # Update tool call data with SUCCESS  # type: ignore[unreachable]
                self._tool_call_data[message.tool_call.id]["status"] = "SUCCESS"
                self._tool_call_data[message.tool_call.id]["result"] = result

                duration_ms = int((time.time() - start_time) * 1000)
                self.log.info(
                    f"[TOOL_FLOW] Tool execution SUCCESS: "
                    f"{message.tool_call.name} in {duration_ms}ms, "
                    f"result_length={len(result)}"
                )

                # Update widget with result and SUCCESS status

                # Log successful result
                if self.tool_registry and self.tool_registry.audit_logger:
                    await self.tool_registry.audit_logger.log_event(
                        AuditEvent(
                            event_type="result",
                            tool_name=message.tool_call.name,
                            arguments=message.tool_call.arguments,
                            result=result[:500]
                            if len(result) > 500
                            else result,  # Truncate long results
                            duration_ms=duration_ms,
                        )
                    )
            except Exception as e:
                # Execution failed - update tool call data with ERROR
                result = f"Tool execution failed: {e}"
                self._tool_call_data[message.tool_call.id]["status"] = "ERROR"
                self._tool_call_data[message.tool_call.id]["result"] = result

                duration_ms = int((time.time() - start_time) * 1000)
                self.log.error(
                    f"[TOOL_FLOW] Tool execution ERROR: "
                    f"{message.tool_call.name} failed after {duration_ms}ms - {e}",
                    exc_info=True,
                )

                # Update widget with error result and ERROR status

                # Log error
                if self.tool_registry and self.tool_registry.audit_logger:
                    await self.tool_registry.audit_logger.log_event(
                        AuditEvent(
                            event_type="error",
                            tool_name=message.tool_call.name,
                            arguments=message.tool_call.arguments,
                            error=str(e),
                            duration_ms=duration_ms,
                        )
                    )
        else:
            # Tool denied - update tool call data with DENIED status
            result = f"Tool execution denied: {message.reason}"
            self._tool_call_data[message.tool_call.id]["status"] = "DENIED"

            self._tool_call_data[message.tool_call.id]["result"] = result
            self.log.info(
                f"[TOOL_FLOW] Tool DENIED: {message.tool_call.name} - {message.reason}"
            )

        # Store result
        tool_message = ToolMessage(content=result, tool_call_id=message.tool_call.id)
        self._tool_results[message.tool_call.id] = tool_message

        # Persist tool call to database for UI reconstruction
        await self._persist_tool_call(
            message.tool_call,
            status=self._tool_call_data[message.tool_call.id]["status"],
            result=result,
        )

        # Yield control to allow UI to process events after tool execution
        await asyncio.sleep(0)

        # Check if all tools are done
        completed = len(self._tool_results)
        total = len(self._pending_tool_calls)
        logger.debug(
            f"[TOOL_FLOW] Tool completion status: {completed}/{total} tools completed"
        )

        if completed == total:
            # All tools completed - post message to continue with results
            # Use message passing to break async call chain and keep UI responsive
            logger.debug(
                f"[TOOL_FLOW] All {total} tools completed, posting message to continue"
            )
            # Post message instead of awaiting directly - this breaks the call chain
            self.post_message(ContinueWithToolResults())
        else:
            self.log.info(
                f"[TOOL_FLOW] Waiting for remaining tools ({total - completed} pending)"
            )

    async def _persist_tool_call(
        self,
        tool_call: ParsedToolCall,
        status: str,
        result: str,
    ) -> None:
        """Persist a tool call to the database for UI reconstruction.

        Args:
            tool_call: The parsed tool call to persist
            status: Tool call status (SUCCESS, ERROR, DENIED)
            result: Tool call result or error message
        """
        # Check if we have the database and message ID
        if (
            not self.conversation
            or not self.conversation._db
            or not self._current_assistant_message_id
        ):
            self.log.debug(
                "[TOOL_FLOW] Cannot persist tool call - no database or message ID"
            )
            return

        try:
            import asyncio
            from functools import partial

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._executor,
                partial(
                    self.conversation._db.save_tool_call,
                    message_id=self._current_assistant_message_id,
                    tool_name=tool_call.name,
                    arguments=tool_call.arguments,
                    status=status.lower(),  # DB expects lowercase
                    result=result,
                ),
            )
            self.log.debug(
                f"[TOOL_FLOW] Persisted tool call: {tool_call.name} ({status})"
            )
        except Exception as e:
            self.log.warning(f"[TOOL_FLOW] Failed to persist tool call: {e}")

    async def _persist_attachments(
        self,
        message_id: int,
        attached_files: list[AttachedFile],
    ) -> None:
        """Persist attachments to the database for UI reconstruction.

        Args:
            message_id: The database message ID to link attachments to
            attached_files: List of AttachedFile objects to persist
        """
        if not self.conversation or not self.conversation._db:
            return

        try:
            import asyncio
            from functools import partial

            loop = asyncio.get_event_loop()
            for file in attached_files:
                await loop.run_in_executor(
                    self._executor,
                    partial(
                        self.conversation._db.save_attachment,
                        message_id=message_id,
                        file_path=file.path,
                        file_type=file.type,
                        mime_type=file.mime_type,
                        file_size=file.size,
                    ),
                )
            logger.debug(
                f"Persisted {len(attached_files)} attachment(s) for message {message_id}"
            )
        except Exception as e:
            logger.warning(f"Failed to persist attachments: {e}")

    def _extract_display_content(self, content: str) -> str:
        """Extract displayable text from message content.

        Handles multimodal content that was JSON-serialized, extracting text
        and replacing image data with placeholders.

        Args:
            content: Message content (string or JSON-serialized list)

        Returns:
            Clean display text without base64 image data
        """
        # Try to parse as JSON (multimodal content)
        if isinstance(content, str) and content.startswith("["):
            try:
                import json

                content_list = json.loads(content)
                if isinstance(content_list, list):
                    # Extract text parts and replace images with placeholders
                    text_parts = []
                    image_count = 0

                    for item in content_list:
                        if isinstance(item, dict):
                            if item.get("type") == "text":
                                text_parts.append(item.get("text", ""))
                            elif item.get("type") == "image_url":
                                image_count += 1
                                # Add image placeholder instead of base64 data
                                text_parts.append(f"[Image {image_count}]")
                        elif isinstance(item, str):
                            text_parts.append(item)

                    return "\n".join(text_parts) if text_parts else content
            except (json.JSONDecodeError, ValueError):
                # Not JSON or invalid - return as-is
                pass

        return content

    async def _display_reconstructed_attachments(
        self,
        attachments: list[dict[str, Any]],
    ) -> None:
        """Display attachments from a loaded conversation using FileChip widgets.

        Args:
            attachments: List of attachment dicts from database
        """
        if not attachments:
            return

        from textual.containers import Horizontal

        from consoul.tui.widgets.historical_file_chip import HistoricalFileChip

        # Create a container for the attachment chips
        container = Horizontal(classes="historical-attachments")

        for att in attachments:
            file_path = att.get("file_path", "")
            file_type = att.get("file_type", "unknown")
            file_size = att.get("file_size")

            chip = HistoricalFileChip(
                file_path=file_path,
                file_type=file_type,
                file_size=file_size,
            )
            container.compose_add_child(chip)

        await self.chat_view.add_message(container)

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
            PermissionManagerScreen(self.consoul_config)
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
        from consoul.tui.widgets.system_prompt_modal import SystemPromptModal

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

        await self.push_screen(
            SystemPromptModal(
                system_prompt=system_prompt,
                profile_name=profile_name,
                tool_count=tool_count,
                stored_at=stored_at,
            )
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
        try:
            from consoul.tui.widgets.ollama_library_modal import OllamaLibraryModal

            await self.push_screen(OllamaLibraryModal())
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
        import random

        from textual.screen import Screen

        from consoul.tui.animations import AnimationStyle
        from consoul.tui.loading import LoadingScreen

        # Check if a screensaver is currently showing
        # Screens are on top of the screen stack
        if len(self.screen_stack) > 1:
            # There's a screen showing - restore docked widgets and dismiss it
            for widget in self.query("Footer, ContextualTopBar"):
                widget.display = True
            self.pop_screen()
            return

        # Create a screen with the loading animation
        animation_styles = [
            AnimationStyle.SOUND_WAVE,
            AnimationStyle.MATRIX_RAIN,
            AnimationStyle.BINARY_WAVE,
            AnimationStyle.CODE_STREAM,
            AnimationStyle.PULSE,
        ]
        style = random.choice(animation_styles)

        class ScreensaverScreen(Screen[None]):
            """Screensaver screen that covers entire terminal."""

            DEFAULT_CSS = """
            ScreensaverScreen {
                layout: vertical;
                height: 100vh;
                padding: 0;
                margin: 0;
            }

            ScreensaverScreen > LoadingScreen {
                width: 100%;
                height: 100%;
                padding: 0;
                margin: 0;
            }

            ScreensaverScreen > LoadingScreen > Center {
                display: none;
            }
            """

            def __init__(
                self, animation_style: AnimationStyle, theme_name: str
            ) -> None:
                super().__init__()
                self.animation_style = animation_style
                self.theme_name = theme_name

            def on_mount(self) -> None:
                """Hide docked widgets when screen mounts."""
                # Hide docked widgets (Footer, ContextualTopBar) to ensure screensaver covers everything
                for widget in self.app.query("Footer, ContextualTopBar"):
                    widget.display = False

            def compose(self) -> ComposeResult:
                # Use theme name as color scheme if available, otherwise fallback to blue
                color_scheme = (
                    self.theme_name
                    if self.theme_name
                    in [
                        "consoul-dark",
                        "consoul-light",
                        "consoul-oled",
                        "consoul-midnight",
                        "consoul-matrix",
                        "consoul-sunset",
                        "consoul-ocean",
                        "consoul-volcano",
                        "consoul-neon",
                        "consoul-forest",
                    ]
                    else "consoul-dark"
                )
                yield LoadingScreen(
                    message="",
                    style=self.animation_style,
                    color_scheme=color_scheme,  # type: ignore
                    show_progress=False,
                )

            def on_key(self, event: events.Key) -> None:
                """Dismiss on any key press and restore docked widgets."""
                # Restore docked widgets visibility
                for widget in self.app.query("Footer, ContextualTopBar"):
                    widget.display = True
                self.app.pop_screen()

        # Get current theme name
        theme_name = self.theme if hasattr(self, "theme") and self.theme else "blue"
        await self.push_screen(ScreensaverScreen(style, theme_name))

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

        # Clear current chat view first
        await self.chat_view.clear_messages()

        # Show loading indicator
        await self.chat_view.show_loading_indicator()

        # Give the loading indicator time to render before we start loading messages
        await asyncio.sleep(0.1)

        # Load conversation from database with full metadata for UI reconstruction
        if self.consoul_config:
            try:
                # Use load_conversation_full to get tool_calls and attachments
                messages = self.conversation_list.db.load_conversation_full(
                    conversation_id
                )

                # Display messages in chat view with proper UI reconstruction
                from consoul.tui.widgets import MessageBubble

                # Pre-process messages to merge consecutive assistant messages
                # (one with tools, one with content) into a single bubble
                processed_messages = []
                i = 0
                while i < len(messages):
                    msg = messages[i]

                    # Check if this is an assistant message with tools but no content
                    # and the next message is also an assistant with content
                    if (
                        msg["role"] == "assistant"
                        and msg.get("tool_calls")
                        and not msg["content"].strip()
                        and i + 1 < len(messages)
                    ):
                        # Look ahead for tool message(s) and next assistant message
                        next_idx = i + 1
                        # Skip tool result messages
                        while (
                            next_idx < len(messages)
                            and messages[next_idx]["role"] == "tool"
                        ):
                            next_idx += 1

                        # If next non-tool message is assistant with content, merge them
                        if (
                            next_idx < len(messages)
                            and messages[next_idx]["role"] == "assistant"
                            and messages[next_idx]["content"].strip()
                        ):
                            # Merge: use tool_calls from first, content from second
                            merged = {
                                **messages[next_idx],
                                "tool_calls": msg["tool_calls"],
                            }
                            processed_messages.append(merged)
                            i = next_idx + 1  # Skip both messages
                            continue

                    processed_messages.append(msg)
                    i += 1

                for msg in processed_messages:
                    role = msg["role"]
                    content = msg["content"]
                    tool_calls_raw = msg.get("tool_calls", [])
                    attachments = msg.get("attachments", [])

                    # Map database tool_call structure to expected format
                    # DB uses 'tool_name' key, but ToolCallDetailsModal expects 'name' key
                    tool_calls = []
                    for tc in tool_calls_raw:
                        tool_calls.append(
                            {
                                "name": tc.get("tool_name", "unknown"),
                                "arguments": tc.get("arguments", {}),
                                "status": tc.get("status", "unknown"),
                                "result": tc.get("result"),
                                "id": tc.get("id"),
                                "type": "tool_call",
                            }
                        )

                    # Skip system and tool messages in display
                    # Tool results are shown via the 🛠 button modal
                    if role in ("system", "tool"):
                        continue

                    # Handle multimodal content (deserialize JSON if needed)
                    display_content = self._extract_display_content(content)

                    # Show tool execution indicator for assistant messages with tools
                    if tool_calls and role == "assistant":
                        from textual.widgets import Static

                        from consoul.tui.widgets.tool_formatter import (
                            format_tool_header,
                        )

                        # Show each tool call with formatted header and arguments
                        for tc in tool_calls:
                            tool_name = tc.get("name", "unknown")
                            tool_args = tc.get("arguments", {})
                            header_renderable = format_tool_header(
                                tool_name, tool_args, theme=self.theme
                            )
                            # Use Static widget to render Rich renderables
                            tool_indicator = Static(
                                header_renderable,
                                classes="system-message",
                            )
                            await self.chat_view.add_message(tool_indicator)

                    # Create message bubbles
                    # Show assistant messages (always, even if empty, for 🛠 button)
                    # Show user messages only if they have content
                    if role == "assistant" or (role == "user" and display_content):
                        # Extract thinking for assistant messages
                        thinking_to_display = None
                        message_content = display_content or ""

                        if role == "assistant" and message_content.strip():
                            thinking, response_text = extract_reasoning(
                                message_content, model_name=self.current_model
                            )
                            message_content = response_text
                            thinking_to_display = self._should_display_thinking(
                                thinking
                            )

                        # Get token count from database (stored when message was created)
                        token_count = msg.get("tokens")
                        # Get streaming metrics from database
                        tokens_per_second = msg.get("tokens_per_second")
                        time_to_first_token = msg.get("time_to_first_token")

                        bubble = MessageBubble(
                            message_content,
                            role=role,
                            show_metadata=True,
                            token_count=token_count,
                            tool_calls=tool_calls if tool_calls else None,
                            message_id=msg.get("id"),  # Pass message ID for branching
                            thinking_content=thinking_to_display
                            if role == "assistant"
                            else None,
                            tokens_per_second=tokens_per_second,
                            time_to_first_token=time_to_first_token,
                        )
                        await self.chat_view.add_message(bubble)

                    # Display attachments for user messages
                    if attachments and role == "user":
                        await self._display_reconstructed_attachments(attachments)

                # Update conversation ID to resume this conversation
                self.conversation_id = conversation_id

                # Ensure we scroll to the bottom after loading all messages
                # Clear the "user scrolled away" flag first
                self.chat_view._user_scrolled_away = False
                # Use call_after_refresh to ensure all messages are laid out first
                self.chat_view.call_after_refresh(
                    self.chat_view.scroll_end, animate=False
                )

                # Update the conversation object if we have one
                logger.info(
                    f"[CONV_LOAD] Checking conditions: "
                    f"has_conversation={self.conversation is not None}, "
                    f"has_config={self.consoul_config is not None}, "
                    f"bool(conversation)={bool(self.conversation)}, "
                    f"bool(config)={bool(self.consoul_config)}"
                )

                if not self.conversation:
                    logger.warning("[CONV_LOAD] self.conversation is falsy!")
                if not self.consoul_config:
                    logger.warning("[CONV_LOAD] self.consoul_config is falsy!")

                # Use explicit None check instead of truthiness check
                # because ConversationHistory.__len__ makes empty conversations falsy
                if self.conversation is not None and self.consoul_config is not None:
                    # Reload conversation history into current conversation object with profile settings
                    try:
                        from consoul.ai import ConversationHistory

                        conv_kwargs = self._get_conversation_config()
                        conv_kwargs["session_id"] = (
                            conversation_id  # Resume this specific session
                        )
                        logger.info(
                            f"[CONV_LOAD] Creating ConversationHistory with session_id={conversation_id}"
                        )
                        self.conversation = ConversationHistory(
                            model_name=self.consoul_config.current_model,
                            model=self.chat_model,
                            **conv_kwargs,
                        )
                        logger.info(
                            f"[CONV_LOAD] Created ConversationHistory: "
                            f"session_id={self.conversation.session_id}, "
                            f"_conversation_created={self.conversation._conversation_created}, "
                            f"message_count={len(self.conversation.messages)}"
                        )
                    except Exception as e:
                        logger.error(
                            f"[CONV_LOAD] Failed to create ConversationHistory: {e}",
                            exc_info=True,
                        )

                # Hide loading indicator and scroll to bottom
                try:
                    # Hide loading indicator
                    await self.chat_view.hide_loading_indicator()

                    # Trigger scroll after layout completes
                    self.chat_view.scroll_to_bottom_after_load()
                except Exception as scroll_err:
                    logger.error(
                        f"Error loading conversation scroll: {scroll_err}",
                        exc_info=True,
                    )
                    raise

            except Exception as e:
                self.log.error(f"Failed to load conversation: {e}")
                self.notify(f"Failed to load conversation: {e}", severity="error")
                # Hide loading indicator on error
                await self.chat_view.hide_loading_indicator()

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
            self.log.info(
                f"Branching conversation {current_session_id} at message {message_id}"
            )

            # Branch the conversation in the database
            new_session_id = self.conversation_list.db.branch_conversation(
                source_session_id=current_session_id,
                branch_at_message_id=message_id,
            )

            self.log.info(f"Created branched conversation: {new_session_id}")

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
                if (
                    provider != self.consoul_config.current_provider.value
                    or model_name != self.current_model
                ):
                    self._switch_provider_and_model(provider, model_name)

        from consoul.tui.widgets import ModelPickerModal

        modal = ModelPickerModal(
            current_model=self.current_model,
            current_provider=self.consoul_config.current_provider,
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

        from consoul.config.profiles import get_builtin_profiles
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
        if not self.consoul_config:
            self.notify("No configuration available", severity="error")
            return

        try:
            # Get old database path and persist setting before switching
            old_db_path = (
                self.active_profile.conversation.db_path
                if self.active_profile
                else None
            )
            old_persist = (
                self.active_profile.conversation.persist
                if self.active_profile
                else True
            )

            # Update active profile in config
            self.consoul_config.active_profile = profile_name
            self.active_profile = self.consoul_config.get_active_profile()
            self.current_profile = profile_name

            # Get new persist setting
            assert self.active_profile is not None, (
                "Active profile should be available after switching"
            )
            new_persist = self.active_profile.conversation.persist

            # Persist profile selection to config file
            from pathlib import Path

            from consoul.config.loader import find_config_files, save_config

            try:
                # Determine config file path (prefer project, fallback to global)
                global_config, project_config = find_config_files()
                config_path = project_config or global_config

                # If no config exists, create global config
                if not config_path:
                    config_path = Path.home() / ".consoul" / "config.yaml"

                # Save updated config
                save_config(self.consoul_config, config_path)
                self.log.info(
                    f"Profile selection saved to {config_path}: {profile_name}"
                )
            except Exception as save_error:
                # Log but don't fail the profile switch - it's already applied in memory
                self.log.warning(
                    f"Failed to persist profile selection: {save_error}", exc_info=True
                )

            # NOTE: Model/provider remain unchanged - profiles are separate from models

            # Handle sidebar visibility based on persist setting changes
            assert self.active_profile is not None, (
                "Active profile should be available for db path access"
            )
            new_db_path = self.active_profile.conversation.db_path

            # Case 1: Switching from non-persist to persist profile
            if not old_persist and new_persist:
                # Need to mount sidebar if show_sidebar is enabled
                if self.config.show_sidebar and not hasattr(self, "conversation_list"):
                    from consoul.ai.database import ConversationDatabase
                    from consoul.tui.widgets.conversation_list import ConversationList

                    db = ConversationDatabase(new_db_path)
                    self.conversation_list = ConversationList(db=db)

                    # Mount sidebar in main-container before content-area
                    main_container = self.query_one(".main-container")
                    main_container.mount(self.conversation_list, before=0)

                    self.log.info(
                        f"Mounted conversation sidebar for persist-enabled profile '{profile_name}'"
                    )

            # Case 2: Switching from persist to non-persist profile
            elif old_persist and not new_persist:
                # Need to unmount sidebar
                if hasattr(self, "conversation_list"):
                    self.conversation_list.remove()
                    delattr(self, "conversation_list")
                    self.log.info(
                        f"Unmounted conversation sidebar for non-persist profile '{profile_name}'"
                    )

            # Case 3: Both profiles have persist=True - check if database path changed
            elif (
                old_persist
                and new_persist
                and old_db_path != new_db_path
                and hasattr(self, "conversation_list")
            ):
                # Database path changed - update conversation list database
                from consoul.ai.database import ConversationDatabase

                self.conversation_list.db = ConversationDatabase(new_db_path)
                # Reload conversations from new database
                self.run_worker(
                    self.conversation_list.reload_conversations(), exclusive=True
                )
                self.log.info(
                    f"Switched to profile '{profile_name}' with database: {new_db_path}"
                )

            # Update conversation with new system prompt if needed (with dynamic tools)
            system_prompt = self._build_current_system_prompt()
            if self.conversation and system_prompt:
                # Clear and re-add system message with new prompt
                # (This preserves conversation history but updates instructions)
                self.conversation.clear(preserve_system=False)
                self.conversation.add_system_message(system_prompt)
                # Store updated prompt metadata
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

            # Update top bar display
            self._update_top_bar_state()

            self.notify(
                f"Switched to profile '{profile_name}' and saved to config (model unchanged: {self.current_model})",
                severity="information",
            )
            self.log.info(
                f"Profile switched and saved: {profile_name}, model preserved: {self.current_model}"
            )

        except Exception as e:
            # Disable markup to avoid markup errors from validation messages
            error_msg = str(e).replace("[", "\\[")
            self.notify(f"Failed to switch profile: {error_msg}", severity="error")
            self.log.error(f"Profile switch failed: {e}", exc_info=True)

    def _handle_create_profile(self) -> None:
        """Handle create new profile action from ProfileSelectorModal."""
        if not self.consoul_config:
            self.notify("No configuration available", severity="error")
            return

        def on_profile_created(new_profile: Any | None) -> None:
            """Handle ProfileEditorModal result for creation."""
            if not new_profile or not self.consoul_config:
                return

            try:
                from consoul.config.loader import find_config_files, save_config
                from consoul.config.profiles import get_builtin_profiles

                # Ensure we're not trying to create a built-in profile
                if new_profile.name in get_builtin_profiles():
                    self.notify(
                        f"Cannot create profile '{new_profile.name}': name is reserved for built-in profiles",
                        severity="error",
                    )
                    return

                # Add to config
                self.consoul_config.profiles[new_profile.name] = new_profile

                # Save to disk
                global_path, project_path = find_config_files()
                save_path = project_path if project_path else global_path
                if not save_path:
                    save_path = Path.home() / ".consoul" / "config.yaml"
                save_config(self.consoul_config, save_path)

                self.notify(
                    f"Profile '{new_profile.name}' created successfully",
                    severity="information",
                )
                self.log.info(f"Created new profile: {new_profile.name}")

            except Exception as e:
                error_msg = str(e).replace("[", "\\[")
                self.notify(f"Failed to create profile: {error_msg}", severity="error")
                self.log.error(f"Profile creation failed: {e}", exc_info=True)

        from consoul.config.profiles import get_builtin_profiles
        from consoul.tui.widgets import ProfileEditorModal

        builtin_names = set(get_builtin_profiles().keys())

        modal = ProfileEditorModal(
            existing_profile=None,  # Create mode
            existing_profiles=self.consoul_config.profiles,
            builtin_profile_names=builtin_names,
        )
        self.push_screen(modal, on_profile_created)

    def _handle_edit_profile(self, profile_name: str) -> None:
        """Handle edit profile action from ProfileSelectorModal.

        Args:
            profile_name: Name of profile to edit
        """
        if not self.consoul_config:
            self.notify("No configuration available", severity="error")
            return

        # Get the profile to edit
        if profile_name not in self.consoul_config.profiles:
            self.notify(f"Profile '{profile_name}' not found", severity="error")
            return

        # Check if it's a built-in profile
        from consoul.config.profiles import get_builtin_profiles

        if profile_name in get_builtin_profiles():
            self.notify(
                f"Cannot edit built-in profile '{profile_name}'. Create a copy instead.",
                severity="error",
            )
            return

        profile_to_edit = self.consoul_config.profiles[profile_name]

        def on_profile_edited(updated_profile: Any | None) -> None:
            """Handle ProfileEditorModal result for editing."""
            if not updated_profile or not self.consoul_config:
                return

            try:
                from consoul.config.loader import find_config_files, save_config

                # Remove old profile if name changed
                if updated_profile.name != profile_name:
                    del self.consoul_config.profiles[profile_name]

                    # If we were using the old profile, switch to the new name
                    if self.current_profile == profile_name:
                        self.current_profile = updated_profile.name
                        self.consoul_config.active_profile = updated_profile.name

                # Update/add profile
                self.consoul_config.profiles[updated_profile.name] = updated_profile

                # Save to disk
                global_path, project_path = find_config_files()
                save_path = project_path if project_path else global_path
                if not save_path:
                    save_path = Path.home() / ".consoul" / "config.yaml"
                save_config(self.consoul_config, save_path)

                self.notify(
                    f"Profile '{updated_profile.name}' updated successfully",
                    severity="information",
                )
                self.log.info(
                    f"Updated profile: {profile_name} -> {updated_profile.name}"
                )

                # If editing current profile, apply changes
                if self.current_profile == updated_profile.name:
                    self.active_profile = updated_profile
                    self._update_top_bar_state()

            except Exception as e:
                error_msg = str(e).replace("[", "\\[")
                self.notify(f"Failed to update profile: {error_msg}", severity="error")
                self.log.error(f"Profile update failed: {e}", exc_info=True)

        from consoul.config.profiles import get_builtin_profiles
        from consoul.tui.widgets import ProfileEditorModal

        builtin_names = set(get_builtin_profiles().keys())

        modal = ProfileEditorModal(
            existing_profile=profile_to_edit,
            existing_profiles=self.consoul_config.profiles,
            builtin_profile_names=builtin_names,
        )
        self.push_screen(modal, on_profile_edited)

    def _handle_delete_profile(self, profile_name: str) -> None:
        """Handle delete profile action from ProfileSelectorModal.

        Args:
            profile_name: Name of profile to delete
        """
        if not self.consoul_config:
            self.notify("No configuration available", severity="error")
            return

        # Check if profile exists
        if profile_name not in self.consoul_config.profiles:
            self.notify(f"Profile '{profile_name}' not found", severity="error")
            return

        # Check if it's a built-in profile
        from consoul.config.profiles import get_builtin_profiles

        if profile_name in get_builtin_profiles():
            self.notify(
                f"Cannot delete built-in profile '{profile_name}'",
                severity="error",
            )
            return

        # Check if it's the current profile
        if profile_name == self.current_profile:
            self.notify(
                f"Cannot delete current profile '{profile_name}'. Switch to another profile first.",
                severity="error",
            )
            return

        # Show confirmation dialog
        def on_confirmed(confirmed: bool | None) -> None:
            """Handle confirmation result."""
            if not confirmed or not self.consoul_config:
                return

            try:
                from consoul.config.loader import find_config_files, save_config

                # Delete from config
                del self.consoul_config.profiles[profile_name]

                # Save to disk
                global_path, project_path = find_config_files()
                save_path = project_path if project_path else global_path
                if not save_path:
                    save_path = Path.home() / ".consoul" / "config.yaml"
                save_config(self.consoul_config, save_path)

                self.notify(
                    f"Profile '{profile_name}' deleted successfully",
                    severity="information",
                )
                self.log.info(f"Deleted profile: {profile_name}")

            except Exception as e:
                error_msg = str(e).replace("[", "\\[")
                self.notify(f"Failed to delete profile: {error_msg}", severity="error")
                self.log.error(f"Profile deletion failed: {e}", exc_info=True)

        # Use Textual's built-in question dialog if available
        # For now, just confirm and delete (could enhance with custom confirmation modal)
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

        self.push_screen(ConfirmDeleteModal(), on_confirmed)

    def _switch_provider_and_model(self, provider: str, model_name: str) -> None:
        """Switch to a different provider and model WITHOUT changing profile.

        Models/providers define WHICH AI to use.
        This method changes the AI backend while preserving profile settings.

        Args:
            provider: Provider to switch to (e.g., "openai", "anthropic")
            model_name: Name of model to switch to
        """
        if not self.consoul_config:
            self.notify("No configuration available", severity="error")
            return

        try:
            from consoul.config.models import Provider

            # Update current provider and model in config
            self.consoul_config.current_provider = Provider(provider)
            self.consoul_config.current_model = model_name
            self.current_model = model_name

            # Persist model selection to config file
            try:
                from consoul.config.loader import find_config_files, save_config

                # Determine which config file to save to
                global_path, project_path = find_config_files()
                save_path = (
                    project_path
                    if project_path and project_path.exists()
                    else global_path
                )

                if not save_path:
                    # Default to global config
                    save_path = Path.home() / ".consoul" / "config.yaml"

                # Save updated config (preserves user's model choice)
                save_config(self.consoul_config, save_path, include_api_keys=False)
                self.log.info(f"Persisted model selection to {save_path}")
            except Exception as e:
                self.log.warning(f"Failed to persist model selection: {e}")
                # Continue even if save fails - model is still switched in memory

            # Reinitialize chat model with new provider/model
            from consoul.ai import get_chat_model

            old_conversation_id = self.conversation_id

            model_config = self.consoul_config.get_current_model_config()
            self.chat_model = get_chat_model(model_config, config=self.consoul_config)

            # NOTE: analyze_images tool registration disabled for SOUL-116
            # See line 433-437 for explanation
            # self._sync_vision_tool_registration()

            # Re-bind tools to the new model
            if self.tool_registry:
                tool_metadata_list = self.tool_registry.list_tools(enabled_only=True)
                if tool_metadata_list:
                    # Check if model supports tool calling
                    from consoul.ai.providers import supports_tool_calling

                    if supports_tool_calling(self.chat_model):
                        tools = [meta.tool for meta in tool_metadata_list]
                        self.chat_model = self.chat_model.bind_tools(tools)  # type: ignore[assignment]
                        self.log.info(
                            f"Re-bound {len(tools)} tools to new model {model_name}"
                        )
                    else:
                        self.log.warning(
                            f"Model {model_name} does not support tool calling. "
                            "Tools are disabled for this model."
                        )

            # Preserve conversation by updating model reference
            if self.conversation:
                self.conversation._model = self.chat_model
                self.conversation.model_name = self.current_model

            # Update top bar display
            self._update_top_bar_state()

            self.notify(
                f"Switched to {provider}/{model_name} (profile unchanged: {self.current_profile})",
                severity="information",
            )
            self.log.info(
                f"Model/provider switched: {provider}/{model_name}, "
                f"profile preserved: {self.current_profile}, "
                f"conversation preserved: {old_conversation_id}"
            )

        except Exception as e:
            # Disable markup to avoid markup errors from Pydantic validation messages
            error_msg = str(e).replace("[", "\\[")
            self.notify(
                f"Failed to switch model/provider: {error_msg}", severity="error"
            )
            self.log.error(f"Model/provider switch failed: {e}", exc_info=True)
