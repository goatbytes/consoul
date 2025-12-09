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
            del self._last_tool_signature  # type: ignore[has-type]

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

        # Add user message to conversation history immediately (in-memory)
        from langchain_core.messages import HumanMessage

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
                message = self._create_multimodal_message(
                    final_message, all_image_paths
                )
                logger.info(
                    f"[IMAGE_DETECTION] Created multimodal message with {len(all_image_paths)} image(s)"
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
                message = HumanMessage(content=final_message)
        else:
            # Regular text message
            message = HumanMessage(content=final_message)

        # Clear attached files after processing
        input_area.attached_files.clear()
        input_area._update_file_chips()

        # Move EVERYTHING to a background worker to keep UI responsive
        async def _process_and_stream() -> None:
            # Add user message (this will create conversation on first message if needed)
            if self.conversation is not None:
                await self.conversation.add_user_message_async(message.content)

            # Get the message that was just added for persisting attachments
            user_message_id = None
            if (
                self.conversation is not None
                and self.conversation.persist
                and self.conversation._db
                and self.conversation.session_id
            ):
                # The message was already persisted in add_user_message_async, get its ID
                # by checking the last persisted message
                try:
                    messages = self.conversation._db.load_conversation(
                        self.conversation.session_id
                    )
                    if messages:
                        user_message_id = messages[-1].get("id")
                    logger.debug(f"Persisted user message with ID: {user_message_id}")
                    # Save attachments linked to this user message
                    if user_message_id and attached_files:
                        logger.debug(f"Persisting {len(attached_files)} attachments")
                        await self._persist_attachments(user_message_id, attached_files)
                        logger.debug("Attachments persisted successfully")
                except Exception as e:
                    logger.error(
                        f"Failed to persist message or attachments: {e}", exc_info=True
                    )

            # Add new conversation to list if first message
            # Use prepend instead of reload to avoid flickering
            if (
                is_first_message
                and hasattr(self, "conversation_list")
                and self.conversation_id
            ):
                await self.conversation_list.prepend_conversation(self.conversation_id)
                self._update_top_bar_state()

            # Start streaming AI response
            await self._stream_ai_response()

        # Fire off all processing in background worker
        # This keeps the UI responsive during the entire "Thinking..." phase
        self.run_worker(_process_and_stream(), exclusive=False)

    async def _stream_ai_response(self) -> None:
        """Stream AI response token-by-token to TUI.

        Uses StreamingResponse widget for real-time token display,
        then converts to MessageBubble when complete.

        Runs the blocking LangChain stream() call in a background worker
        to prevent freezing the UI event loop.
        """
        from consoul.ai.exceptions import StreamingError
        from consoul.ai.history import to_dict_message
        from consoul.tui.widgets import MessageBubble, StreamingResponse

        # DEBUG: Log entry to verify this method is called
        logger.debug(
            f"[TOOL_FLOW] _stream_ai_response ENTRY - iteration {self._tool_call_iterations}/{self._max_tool_iterations}"
        )

        # Update streaming state
        self._stream_cancelled = False
        self.streaming = True  # Update reactive state
        self._update_top_bar_state()  # Update top bar streaming indicator

        try:
            # Get trimmed messages for context window
            # This can be slow due to token counting, so run in executor
            model_config = self.consoul_config.get_current_model_config()  # type: ignore[union-attr]

            # Get the model's actual context window size from conversation history
            # (which uses get_model_token_limit() to query the model)
            context_size = self.conversation.max_tokens  # type: ignore[union-attr]

            # Reserve tokens for response - must be less than total context window
            # Use max_tokens from config if specified, otherwise use a reasonable default
            default_reserve = 4096

            # Reserve tokens should be a portion of context window for the response
            # Use model_config.max_tokens as desired response length if set,
            # but ensure it doesn't exceed half the context window
            if model_config.max_tokens:
                reserve_tokens = min(model_config.max_tokens, context_size // 2)
            else:
                reserve_tokens = min(default_reserve, context_size // 2)

            # Final safety check: ensure reserve_tokens leaves room for input
            # Reserve at most (context - 512) to guarantee at least 512 tokens for conversation
            reserve_tokens = min(reserve_tokens, context_size - 512)

            # Check if ANY message in conversation is multimodal BEFORE token counting
            # Token counting with large base64 images can hang
            has_multimodal_in_history = False
            if self.conversation and self.conversation.messages:
                # Check last 10 messages for multimodal content (checking all could be slow)
                for msg in list(self.conversation.messages[-10:]):
                    if (
                        hasattr(msg, "content")
                        and isinstance(msg.content, list)
                        and any(
                            isinstance(block, dict)
                            and block.get("type") in ["image", "image_url"]
                            for block in msg.content
                        )
                    ):
                        has_multimodal_in_history = True
                        break

            # Run token counting and message trimming in executor to avoid blocking
            import asyncio

            loop = asyncio.get_event_loop()

            # For conversations with multimodal content, skip expensive token counting
            if has_multimodal_in_history:
                logger.info(
                    "[IMAGE_DETECTION] Conversation contains multimodal content, skipping token counting"
                )
                # Just take the last few messages to keep context manageable
                messages = list(self.conversation.messages[-10:])  # type: ignore
            else:
                # Debug: log message count before trimming
                conv_msg_count = (
                    len(self.conversation.messages) if self.conversation else 0
                )
                logger.debug(
                    f"[MESSAGES] Before trimming: conversation has {conv_msg_count} messages"
                )
                if self.conversation and conv_msg_count > 0 and conv_msg_count <= 5:
                    for i, msg in enumerate(self.conversation.messages):
                        logger.debug(
                            f"[MESSAGES]   Message {i}: type={msg.type}, "
                            f"content_len={len(str(msg.content)) if msg.content else 0}"
                        )

                try:
                    # Add timeout to prevent hanging on token counting
                    messages = await asyncio.wait_for(
                        loop.run_in_executor(
                            self._executor,
                            self.conversation.get_trimmed_messages,  # type: ignore[union-attr]
                            reserve_tokens,
                        ),
                        timeout=10.0,  # 10 second timeout
                    )
                except asyncio.TimeoutError:
                    logger.warning(
                        "Token counting timed out after 10s, using last 20 messages as fallback"
                    )
                    # Fallback: use last 20 messages without token counting
                    messages = list(self.conversation.messages[-20:])  # type: ignore
                except Exception as e:
                    logger.error(f"Error trimming messages: {e}", exc_info=True)
                    # Fallback: use last 20 messages
                    messages = list(self.conversation.messages[-20:])  # type: ignore

            self.log.info(
                f"[TOOL_FLOW] _stream_ai_response starting - "
                f"iteration={self._tool_call_iterations}/{self._max_tool_iterations}, "
                f"conversation_messages={len(self.conversation.messages) if self.conversation else 0}, "
                f"trimmed_messages={len(messages)}"
            )

            # Debug: log message details if empty
            if not messages or len(messages) == 0:
                logger.error(
                    f"[MESSAGES] Empty message list! "
                    f"conversation.messages count: {len(self.conversation.messages) if self.conversation else 0}"
                )
                if self.conversation and self.conversation.messages:
                    logger.error(
                        f"[MESSAGES] First few messages: {self.conversation.messages[:3]}"
                    )
            else:
                logger.debug(f"[MESSAGES] Sending {len(messages)} messages to model")

            # Check if the last user message is multimodal (contains images)
            has_multimodal_content = False
            if messages and len(messages) > 0:
                last_msg = messages[-1]
                if hasattr(last_msg, "content") and isinstance(last_msg.content, list):
                    # Check if any content block is an image
                    has_multimodal_content = any(
                        isinstance(block, dict)
                        and block.get("type") in ["image", "image_url"]
                        for block in last_msg.content
                    )

            logger.info(
                f"[IMAGE_DETECTION] Last message has multimodal content: {has_multimodal_content}"
            )

            # Use model without tools for multimodal messages to force direct vision analysis
            # Tools cause the model to use bash/analyze_images instead of vision capabilities
            model_to_use = self.chat_model
            if has_multimodal_content:
                logger.info(
                    "[IMAGE_DETECTION] Using model WITHOUT tools for multimodal message"
                )
                # Check if model has tools bound via RunnableBinding
                # bind_tools() creates a RunnableBinding with 'bound' attribute pointing to base model
                if hasattr(self.chat_model, "bound"):
                    # This is a RunnableBinding from bind_tools() - get the wrapped model
                    model_to_use = self.chat_model.bound  # type: ignore
                    logger.info(
                        "[IMAGE_DETECTION] Unwrapped model from RunnableBinding"
                    )
                else:
                    # Model doesn't have tools bound, use as-is
                    logger.info(
                        "[IMAGE_DETECTION] Model has no tool bindings, using directly"
                    )

                # Add system message to guide the model to use vision directly
                from langchain_core.messages import SystemMessage

                vision_system_msg = SystemMessage(
                    content="You have vision capabilities. When provided with an image, analyze and describe what you see in the image directly. Do not suggest using external tools or bash commands."
                )
                # Insert system message at the beginning of the conversation
                messages.insert(0, vision_system_msg)
                logger.info(
                    "[IMAGE_DETECTION] Added system message at beginning to guide vision analysis"
                )

            # For multimodal messages, pass LangChain messages directly
            # For text-only messages, convert to dict format
            if has_multimodal_content:
                messages_to_send = messages
                logger.info(
                    f"[IMAGE_DETECTION] Sending {len(messages_to_send)} LangChain messages directly to model"
                )
                # Debug: Log message structure
                for i, msg in enumerate(messages_to_send):
                    msg_type = msg.type
                    content = msg.content
                    if isinstance(content, list):
                        logger.info(
                            f"[IMAGE_DETECTION] Message {i} ({msg_type}): {len(content)} content blocks"
                        )
                        for j, block in enumerate(content):
                            if isinstance(block, dict):
                                block_type = block.get("type", "unknown")
                                if block_type == "image":
                                    data_len = (
                                        len(block.get("data", ""))
                                        if "data" in block
                                        else 0
                                    )
                                    logger.info(
                                        f"[IMAGE_DETECTION]   Block {j}: type=image, data_length={data_len}, keys={list(block.keys())}"
                                    )
                                else:
                                    logger.info(
                                        f"[IMAGE_DETECTION]   Block {j}: type={block_type}"
                                    )
                    else:
                        content_preview = str(content)[:100] if content else "(empty)"
                        logger.info(
                            f"[IMAGE_DETECTION] Message {i} ({msg_type}): {content_preview}"
                        )
            else:
                # Convert to dict format for LangChain (also can be slow with many messages)
                messages_to_send = await loop.run_in_executor(
                    self._executor, lambda: [to_dict_message(msg) for msg in messages]
                )
                logger.debug(
                    f"[MESSAGES] Converted {len(messages)} messages to {len(messages_to_send)} dict messages"
                )
                if len(messages_to_send) == 0:
                    logger.error(
                        f"[MESSAGES] Conversion resulted in empty list! Original had {len(messages)} messages"
                    )

            # Final check before sending to model
            if not messages_to_send or len(messages_to_send) == 0:
                logger.error(
                    f"[MESSAGES] About to send EMPTY message list to model! "
                    f"This will cause an error. Original messages: {len(messages)}"
                )

            # Stream tokens in background worker to avoid blocking UI
            collected_tokens: list[str] = []

            # Use asyncio.Queue to stream tokens from background thread to UI
            import asyncio

            token_queue: asyncio.Queue[str | None] = asyncio.Queue()

            # Queue to send final AIMessage with tool_calls
            from langchain_core.messages import AIMessage

            message_queue: asyncio.Queue[AIMessage | None] = asyncio.Queue()

            # Queue to send exceptions from background thread
            exception_queue: asyncio.Queue[Exception | None] = asyncio.Queue()

            # Get the current event loop (Textual's loop)
            event_loop = asyncio.get_running_loop()

            def normalize_chunk_content(
                content: str | list[dict[str, str]] | None,
            ) -> str:
                """Normalize chunk content to string.

                LangChain chunks can have content as:
                - str: Direct text (OpenAI, most providers)
                - list: Blocks like [{"type":"text","text":"foo"}] (Anthropic, Gemini)
                - None: Empty chunk

                Args:
                    content: Chunk content from AIMessage

                Returns:
                    Normalized string content, empty string if None
                """
                if content is None:
                    return ""
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    # Extract text from block list (Anthropic/Gemini format)
                    text_parts = []
                    for block in content:
                        if isinstance(block, dict):
                            # Handle {"type": "text", "text": "content"}
                            if block.get("type") == "text" and "text" in block:
                                text_parts.append(block["text"])
                            # Handle other block types if needed
                        elif isinstance(block, str):
                            # Some providers may send list of strings
                            text_parts.append(block)
                    return "".join(text_parts)
                # Fallback: convert to string
                return str(content)

            def sync_stream_producer() -> None:
                """Background thread: stream tokens and push to queue.

                Sends None as sentinel when complete or cancelled.
                Collects chunks to reconstruct final AIMessage with tool_calls.
                Sends exceptions via exception_queue to trigger error handling.
                """
                collected_chunks: list[AIMessage] = []
                exception_caught: Exception | None = None
                try:
                    for chunk in model_to_use.stream(messages_to_send):  # type: ignore[union-attr]
                        # Check for cancellation
                        if self._stream_cancelled:
                            break

                        # Collect all chunks (even empty ones) for tool_calls
                        collected_chunks.append(chunk)

                        # Normalize content (handles str, list of blocks, None)
                        token = normalize_chunk_content(chunk.content)  # type: ignore[arg-type]

                        # Skip empty tokens
                        if not token:
                            continue

                        # Push token to queue (thread-safe)
                        asyncio.run_coroutine_threadsafe(
                            token_queue.put(token), event_loop
                        )

                except Exception as e:
                    # Store exception to send to main thread
                    exception_caught = e
                    logger.error(
                        f"[TOOL_FLOW] Exception in stream loop: {e}", exc_info=True
                    )
                finally:
                    logger.debug(
                        f"[TOOL_FLOW] Stream loop finished. Collected {len(collected_chunks)} chunks, exception={exception_caught}"
                    )
                    # Send sentinel to signal completion
                    asyncio.run_coroutine_threadsafe(token_queue.put(None), event_loop)

                    # Send exception if any (so main thread can handle it properly)
                    asyncio.run_coroutine_threadsafe(
                        exception_queue.put(exception_caught), event_loop
                    )

                    # Combine chunks into final AIMessage
                    # Tool calls are typically in the last chunk
                    final_message: AIMessage | None = None
                    if (
                        collected_chunks
                        and not self._stream_cancelled
                        and not exception_caught
                    ):
                        try:
                            # Accumulate tool_call_chunks from all chunks
                            # OpenAI streams tool calls incrementally across chunks as strings:
                            # - Early chunks have name, id, and args='' (empty string)
                            # - Later chunks have incremental args updates like '{"', 'command', '":"', 'ls', '"}'
                            # - We need to concatenate args strings by index, then parse final JSON
                            tool_calls_by_index: dict[int, dict[str, Any]] = {}

                            for chunk in collected_chunks:
                                # Use tool_call_chunks (raw streaming data), not tool_calls (pre-parsed)
                                if (
                                    not hasattr(chunk, "tool_call_chunks")
                                    or not chunk.tool_call_chunks
                                ):
                                    continue

                                for tc in chunk.tool_call_chunks:  # type: ignore[attr-defined]
                                    if not isinstance(tc, dict):
                                        continue

                                    # Use explicit index if provided, default to 0
                                    tc_index = tc.get("index", 0)

                                    if tc_index not in tool_calls_by_index:
                                        tool_calls_by_index[tc_index] = {
                                            "name": "",
                                            "args": "",  # Initialize as empty STRING, not dict
                                            "id": None,
                                            "type": "tool_call",
                                        }

                                    # Concatenate string fields from chunks
                                    if tc.get("name"):
                                        tool_calls_by_index[tc_index]["name"] = tc[
                                            "name"
                                        ]
                                    if tc.get("id"):
                                        tool_calls_by_index[tc_index]["id"] = tc["id"]
                                    if tc.get("args"):
                                        # Concatenate args as strings (e.g., '{"' + 'command' + '":"' ...)
                                        tool_calls_by_index[tc_index]["args"] += tc[
                                            "args"
                                        ]

                            # Parse the concatenated JSON args strings into dicts
                            tool_calls = []
                            for tc_data in tool_calls_by_index.values():
                                args_str = tc_data["args"]
                                try:
                                    # Parse accumulated JSON string into dict
                                    import json

                                    parsed_args = (
                                        json.loads(args_str) if args_str else {}
                                    )
                                    tool_calls.append(
                                        {
                                            "name": tc_data["name"],
                                            "args": parsed_args,
                                            "id": tc_data["id"],
                                            "type": "tool_call",
                                        }
                                    )
                                except json.JSONDecodeError as e:
                                    logger.warning(
                                        f"Failed to parse tool call args: {args_str!r}, error: {e}"
                                    )
                                    # Include anyway with empty args
                                    tool_calls.append(
                                        {
                                            "name": tc_data["name"],
                                            "args": {},
                                            "id": tc_data["id"],
                                            "type": "tool_call",
                                        }
                                    )

                            logger.debug(
                                f"Found {len(tool_calls)} tool_calls after merging chunks"
                            )
                            logger.debug(f"Final tool_calls: {tool_calls}")

                            # Reconstruct content from chunks
                            # Normalize all content (handles str, list blocks, None)
                            content_parts: list[str] = []
                            for c in collected_chunks:
                                normalized = normalize_chunk_content(c.content)  # type: ignore[arg-type]
                                if normalized:
                                    content_parts.append(normalized)

                            # Extract usage_metadata from chunks
                            # OpenAI may send usage in a separate chunk or in response_metadata
                            usage_metadata = None
                            if collected_chunks:
                                # Check all chunks from the end, looking for usage_metadata
                                logger.debug(
                                    f"[COST] Checking {len(collected_chunks)} chunks for usage data"
                                )

                                for i, chunk in enumerate(
                                    reversed(collected_chunks[-5:])
                                ):  # Check last 5 chunks
                                    chunk_idx = len(collected_chunks) - i - 1

                                    # Check usage_metadata attribute
                                    if (
                                        hasattr(chunk, "usage_metadata")
                                        and chunk.usage_metadata
                                    ):
                                        usage_metadata = chunk.usage_metadata
                                        logger.debug(
                                            f"[COST] Found usage_metadata in chunk {chunk_idx}: {usage_metadata}"
                                        )
                                        break

                                    # Check response_metadata for usage info
                                    if (
                                        hasattr(chunk, "response_metadata")
                                        and chunk.response_metadata
                                    ):
                                        resp_meta = chunk.response_metadata
                                        if (
                                            "usage" in resp_meta
                                            or "token_usage" in resp_meta
                                        ):
                                            logger.debug(
                                                f"[COST] Found usage in chunk {chunk_idx} response_metadata: {resp_meta}"
                                            )
                                            # Convert to usage_metadata format if needed
                                            if "usage" in resp_meta:
                                                usage_dict = resp_meta["usage"]
                                                usage_metadata = {
                                                    "input_tokens": usage_dict.get(
                                                        "prompt_tokens", 0
                                                    ),
                                                    "output_tokens": usage_dict.get(
                                                        "completion_tokens", 0
                                                    ),
                                                    "total_tokens": usage_dict.get(
                                                        "total_tokens", 0
                                                    ),
                                                }
                                                break

                                if not usage_metadata:
                                    logger.debug(
                                        "[COST] No usage_metadata found in any chunks"
                                    )

                            # Create final message with all content, tool_calls, and usage_metadata
                            final_message = AIMessage(
                                content="".join(content_parts),
                                tool_calls=tool_calls if tool_calls else [],
                                usage_metadata=usage_metadata,
                            )
                            logger.debug(
                                f"Final message has {len(final_message.tool_calls) if final_message.tool_calls else 0} tool_calls"
                            )
                            logger.debug(
                                "[TOOL_FLOW] About to send final_message to main thread"
                            )
                        except Exception as e:
                            # If message reconstruction fails, don't block completion
                            logger.error(
                                f"[TOOL_FLOW] Exception during message reconstruction: {e}",
                                exc_info=True,
                            )
                            final_message = None

                    # Send final message to main thread
                    logger.debug(
                        f"[TOOL_FLOW] Sending final_message to queue: has_message={final_message is not None}"
                    )
                    asyncio.run_coroutine_threadsafe(
                        message_queue.put(final_message), event_loop
                    )

            # Start background thread
            import threading

            stream_thread = threading.Thread(target=sync_stream_producer, daemon=True)
            stream_thread.start()

            # Wait for first token, then replace typing indicator with streaming widget
            # Use a loop with short timeouts to keep UI responsive during API wait
            import time

            stream_start_time = time.time()
            first_token = None
            got_token = False  # Track if we actually received something from queue
            while not got_token:
                try:
                    # Wait for token with 50ms timeout, then yield to event loop
                    first_token = await asyncio.wait_for(
                        token_queue.get(), timeout=0.05
                    )
                    got_token = True  # Got something from queue (even if it's None)
                except asyncio.TimeoutError:
                    # Timeout - yield control to allow keyboard/click events to process
                    # Force Textual to process pending events and render
                    await asyncio.sleep(0)
                    # CRITICAL: Trigger a refresh to process pending input widget updates
                    try:
                        input_area = self.query_one("#input-area")
                        input_area.refresh()
                    except Exception:
                        pass  # Input area might not exist yet
                    await asyncio.sleep(0)
                    # Check if stream was cancelled
                    if self._stream_cancelled:
                        break
                    # Continue waiting for token
                    continue

            time_to_first_token = time.time() - stream_start_time
            logger.debug(
                f"[TOOL_FLOW] Got first_token: is_none={first_token is None}, value={first_token[:50] if first_token else 'None'}, ttft={time_to_first_token:.3f}s"
            )

            # Hide typing indicator
            await self.chat_view.hide_typing_indicator()

            # Check if first token indicates thinking mode
            thinking_mode = False
            thinking_indicator = None
            if first_token and StreamingResponse().detect_thinking_start(first_token):
                thinking_mode = True
                logger.debug("[THINKING] Detected thinking tags at start of stream")
                # Create and show thinking indicator
                from consoul.tui.widgets.thinking_indicator import ThinkingIndicator

                thinking_indicator = ThinkingIndicator()
                await self.chat_view.add_message(thinking_indicator)

            # Create streaming response widget
            stream_widget = StreamingResponse(renderer="hybrid")
            if not thinking_mode:
                # Show stream widget immediately if not in thinking mode
                await self.chat_view.add_message(stream_widget)

            # Track for cancellation
            self._current_stream = stream_widget

            # Check if stream ended immediately or was cancelled
            if first_token is None or self._stream_cancelled:
                # Stream ended before any tokens - could be tool call response with no content
                if self._stream_cancelled:
                    await stream_widget.remove()
                    cancelled_bubble = MessageBubble(
                        "_Stream cancelled by user_",
                        role="system",
                        show_metadata=False,
                    )
                    await self.chat_view.add_message(cancelled_bubble)
                    return

                # If no tokens but not cancelled, might be tool calls with empty content
                # Don't return yet - let it continue to check for tool calls below
                # The stream widget will be removed if we have tool calls
                # Skip token consumption loop since there are no tokens
                pass
            else:
                # Add first token (only if we have one)
                collected_tokens.append(first_token)

                if thinking_mode:
                    # In thinking mode - show token in thinking indicator AND buffer
                    stream_widget.thinking_buffer += first_token
                    await thinking_indicator.add_token(first_token)  # type: ignore[union-attr]
                else:
                    # Not in thinking mode - add token to stream widget
                    await stream_widget.add_token(first_token)

                # Consume remaining tokens from queue and update UI in real-time
                while True:
                    token = await token_queue.get()

                    # Yield control to allow UI event processing (scrolling, clicking, etc)
                    # Without this, user input events queue up and aren't processed until streaming ends
                    await asyncio.sleep(0)

                    # None = sentinel, stream is done
                    if token is None:
                        break

                    # Check for cancellation
                    if self._stream_cancelled:
                        break

                    # Add token to collected tokens
                    collected_tokens.append(token)

                    # Handle thinking mode transitions
                    if thinking_mode:
                        # Buffer token for end detection
                        stream_widget.thinking_buffer += token

                        # Show token in thinking indicator (visible streaming)
                        await thinking_indicator.add_token(token)  # type: ignore[union-attr]

                        if stream_widget.detect_thinking_end():
                            # Thinking has ended - transition to normal streaming
                            logger.debug(
                                "[THINKING] Detected end of thinking tags, switching to normal streaming"
                            )
                            thinking_mode = False

                            # Remove thinking indicator
                            if thinking_indicator:
                                await thinking_indicator.remove()

                            # Show stream widget for the answer portion
                            await self.chat_view.add_message(stream_widget)

                            # Don't add the buffered thinking content to stream widget
                            # It will be extracted later and shown in collapsible section
                    else:
                        # Normal streaming mode - add token to UI immediately
                        await stream_widget.add_token(token)

                    # Yield to event loop to allow screen refresh
                    import asyncio

                    await asyncio.sleep(0)

            # If still in thinking mode when stream ends, remove indicator and show stream widget
            if thinking_mode and thinking_indicator:
                logger.debug(
                    "[THINKING] Stream ended while in thinking mode, removing indicator"
                )
                await thinking_indicator.remove()
                # Show the stream widget with all content (thinking will be extracted later)
                await self.chat_view.add_message(stream_widget)

            # Finalize streaming widget (this handles scrolling internally)
            await stream_widget.finalize_stream()

            # Get complete response
            full_response = "".join(collected_tokens)

            # Check if background thread encountered an exception
            stream_exception = await exception_queue.get()
            logger.debug(f"[TOOL_FLOW] Stream exception: {stream_exception}")
            if stream_exception:
                # Check if this is a "model does not support tools" error from Ollama
                error_msg = str(stream_exception).lower()
                if "does not support tools" in error_msg and "400" in error_msg:
                    self.log.warning(
                        f"Model {self.current_model} rejected tool calls. "
                        "Retrying without tools..."
                    )

                    # Remove the failed stream widget
                    await stream_widget.remove()

                    # Remove tool binding from model
                    from consoul.ai import get_chat_model

                    model_config = self.consoul_config.get_current_model_config()  # type: ignore[union-attr]
                    self.chat_model = get_chat_model(
                        model_config, config=self.consoul_config
                    )

                    # Update conversation's model reference
                    if self.conversation:
                        self.conversation._model = self.chat_model

                    # Show notification to user
                    self.notify(
                        f"Model {self.current_model} doesn't support tools. Retrying...",
                        severity="warning",
                        timeout=3,
                    )

                    # Show typing indicator before retry
                    await self.chat_view.show_typing_indicator()

                    # Reset streaming state for retry
                    self._stream_cancelled = False
                    self.streaming = True
                    self._update_top_bar_state()

                    # Retry the request without tools (conversation already has user message)
                    await self._stream_ai_response()
                    return

                # Re-raise other exceptions to trigger error handling
                raise stream_exception

            # Get final AIMessage with potential tool_calls
            final_message = await message_queue.get()
            logger.debug(
                f"[TOOL_FLOW] Got final_message from queue: type={type(final_message).__name__}, is_none={final_message is None}"
            )

            # Check if we have content OR tool calls (tool calls can come with empty content)
            has_content = not self._stream_cancelled and full_response.strip()
            has_tool_calls_in_message = (
                final_message
                and hasattr(final_message, "tool_calls")
                and final_message.tool_calls
            )

            logger.debug(
                f"[TOOL_FLOW] Response check: has_content={has_content}, "
                f"has_tool_calls_in_message={has_tool_calls_in_message}, "
                f"full_response_len={len(full_response)}, "
                f"cancelled={self._stream_cancelled}"
            )

            if has_content or has_tool_calls_in_message:
                # Calculate streaming metrics before persisting
                # (need token count for tokens_per_second calculation)
                stream_end_time = time.time()
                stream_duration = stream_end_time - stream_start_time

                # Try to get token count - will recalculate more accurately later if needed
                try:
                    from langchain_core.messages import AIMessage

                    # Quick token count for metrics
                    token_count_for_metrics = await asyncio.wait_for(
                        loop.run_in_executor(
                            self._executor,
                            self.conversation._token_counter,  # type: ignore[union-attr,arg-type]
                            [AIMessage(content=full_response)],
                        ),
                        timeout=2.0,  # Short timeout for quick estimate
                    )
                except Exception:
                    # Fallback to quick approximation
                    token_count_for_metrics = len(full_response) // 4

                tokens_per_second = (
                    token_count_for_metrics / stream_duration
                    if stream_duration > 0
                    else None
                )

                # Add to conversation history
                # Important: Use final_message directly to preserve tool_calls attribute
                if final_message:
                    self.conversation.messages.append(final_message)  # type: ignore[union-attr]
                    # Persist to DB and capture message ID for linking tool calls
                    try:
                        # Build metadata for streaming metrics
                        metadata: dict[str, float] = {}
                        if tokens_per_second is not None:
                            metadata["tokens_per_second"] = tokens_per_second
                        if time_to_first_token is not None:
                            metadata["time_to_first_token"] = time_to_first_token

                        self._current_assistant_message_id = await asyncio.wait_for(
                            self.conversation._persist_message(  # type: ignore[union-attr]
                                final_message, metadata=metadata if metadata else None
                            ),
                            timeout=10.0,  # 10 second timeout
                        )
                    except asyncio.TimeoutError:
                        logger.error(
                            "Message persistence timed out after 10s - continuing without DB save"
                        )
                        self._current_assistant_message_id = None
                    except Exception as e:
                        logger.error(f"Message persistence failed: {e}")
                        self._current_assistant_message_id = None
                elif has_content:
                    # Fallback if final_message reconstruction failed but we have content
                    self.conversation.add_assistant_message(full_response)  # type: ignore[union-attr]

                # Check for tool calls in the final message
                logger.debug(
                    f"[TOOL_FLOW] Checking final_message for tool calls: has_final_message={final_message is not None}"
                )
                if final_message:
                    from consoul.ai.tools.parser import has_tool_calls, parse_tool_calls

                    logger.debug("[TOOL_FLOW] Calling has_tool_calls()")
                    if has_tool_calls(final_message):
                        parsed_calls = parse_tool_calls(final_message)
                        logger.debug(
                            f"[TOOL_FLOW] Tool calls detected in model response: "
                            f"{len(parsed_calls)} call(s), "
                            f"content_length={len(full_response)}"
                        )
                        for i, call in enumerate(parsed_calls):
                            self.log.info(
                                f"[TOOL_FLOW]   Tool {i + 1}: {call.name}({list(call.arguments.keys()) if isinstance(call.arguments, dict) else '...'})"
                            )

                        # If stream widget is empty (no content), replace with tool indicator
                        if not full_response.strip():
                            logger.debug(
                                "[TOOL_FLOW] Replacing empty stream widget with tool execution message"
                            )
                            await stream_widget.remove()

                            # Show tool execution messages with formatted headers
                            from textual.widgets import Static

                            from consoul.tui.widgets.tool_formatter import (
                                format_tool_header,
                            )

                            for call in parsed_calls:
                                # Format tool header with arguments (returns RenderableType)
                                header_renderable = format_tool_header(
                                    call.name, call.arguments, theme=self.theme
                                )
                                # Use Static widget to render Rich renderables
                                tool_message = Static(
                                    header_renderable,
                                    classes="system-message",
                                )
                                await self.chat_view.add_message(tool_message)

                        # Handle tool calls
                        logger.debug(
                            f"[TOOL_FLOW] Calling _handle_tool_calls with {len(parsed_calls)} calls"
                        )
                        await self._handle_tool_calls(parsed_calls)
                        logger.debug("[TOOL_FLOW] _handle_tool_calls completed")
                    else:
                        self.log.info(
                            f"[TOOL_FLOW] No tool calls in model response, "
                            f"content_length={len(full_response)}"
                        )

                # Generate title if this is the first exchange
                if self.title_generator and self._should_generate_title():
                    self.log.debug("Triggering title generation for first exchange")
                    # Get first user message (skip system messages)
                    user_msg = None
                    for msg in self.conversation.messages:  # type: ignore[union-attr]
                        if msg.type == "human":
                            user_msg = msg.content
                            break

                    if user_msg and self.conversation.session_id:  # type: ignore[union-attr]
                        # Run title generation in background (non-blocking)
                        self.run_worker(
                            self._generate_and_save_title(
                                self.conversation.session_id,  # type: ignore[union-attr]
                                user_msg,  # type: ignore[arg-type]
                                full_response,
                            ),
                            exclusive=False,
                            name=f"title_gen_{self.conversation.session_id}",  # type: ignore[union-attr]
                        )
                    else:
                        self.log.warning(
                            f"Cannot generate title: user_msg={bool(user_msg)}, "
                            f"session_id={self.conversation.session_id if self.conversation else None}"
                        )

                # Replace StreamingResponse with MessageBubble for permanent display
                # Save scroll position before removing widget to prevent jump to top
                chat_view_scroll_y = self.chat_view.scroll_y
                # Consider "at bottom" if within 5 units of the bottom
                # This handles cases where scroll is in progress but not yet complete
                chat_view_at_bottom = (
                    self.chat_view.scroll_y >= self.chat_view.max_scroll_y - 5
                )
                logger.debug(
                    f"[SCROLL] Before removing StreamingResponse - "
                    f"scroll_y: {chat_view_scroll_y}, "
                    f"max_scroll_y: {self.chat_view.max_scroll_y}, "
                    f"at_bottom: {chat_view_at_bottom}"
                )

                await stream_widget.remove()

                # Collect tool call data if any tools were executed
                tool_calls_list = (
                    list(self._tool_call_data.values())
                    if self._tool_call_data
                    else None
                )

                # Only create assistant bubble if there's actual content
                # Don't create bubble for initial tool call responses (empty content)
                # The final response after tool execution will have content and tool data
                if full_response.strip():
                    # Calculate actual token count from the response content
                    # (collected_tokens is chunks, not tokens - could be just 1 chunk)
                    try:
                        from langchain_core.messages import AIMessage

                        # Use a timeout to prevent hanging on token counting
                        token_count = await asyncio.wait_for(
                            loop.run_in_executor(
                                self._executor,
                                self.conversation._token_counter,  # type: ignore[union-attr,arg-type]
                                [AIMessage(content=full_response)],
                            ),
                            timeout=5.0,  # 5 second timeout
                        )
                    except asyncio.TimeoutError:
                        logger.warning("Token counting timed out, using approximation")
                        token_count = len(full_response) // 4
                    except Exception as e:
                        logger.warning(f"Token counting failed: {e}")
                        # Fallback to character approximation if token counting fails
                        token_count = len(full_response) // 4

                    # Calculate streaming metrics
                    stream_end_time = time.time()
                    stream_duration = stream_end_time - stream_start_time
                    tokens_per_second = (
                        token_count / stream_duration if stream_duration > 0 else None
                    )

                    # Extract thinking/reasoning from response
                    thinking = None
                    response_text = full_response

                    if full_response.strip():
                        thinking, response_text = extract_reasoning(
                            full_response, model_name=self.current_model
                        )

                    # Determine if thinking should be displayed based on config
                    thinking_content = self._should_display_thinking(thinking)

                    # Calculate estimated cost for non-local providers
                    estimated_cost = None

                    # Debug: Log usage_metadata availability
                    logger.debug(
                        f"[COST] Checking cost calculation: "
                        f"has_final_message={final_message is not None}, "
                        f"has_usage_metadata={hasattr(final_message, 'usage_metadata') if final_message else False}, "
                        f"usage_metadata_value={getattr(final_message, 'usage_metadata', None) if final_message else None}"
                    )

                    if (
                        final_message
                        and hasattr(final_message, "usage_metadata")
                        and final_message.usage_metadata
                        and self.consoul_config
                    ):
                        # Check if this is a local provider (Ollama, LlamaCpp, MLX)
                        model_config = self.consoul_config.get_current_model_config()
                        from consoul.config.models import (
                            LlamaCppModelConfig,
                            MLXModelConfig,
                            OllamaModelConfig,
                        )

                        is_local = isinstance(
                            model_config,
                            (OllamaModelConfig, LlamaCppModelConfig, MLXModelConfig),
                        )

                        logger.debug(
                            f"[COST] Provider check: is_local={is_local}, "
                            f"model_config_type={type(model_config).__name__}"
                        )

                        if not is_local:
                            try:
                                from consoul.pricing import calculate_cost

                                usage = final_message.usage_metadata
                                # IMPORTANT: For Anthropic, input_tokens = tokens after last cache breakpoint only
                                # Total input = input_tokens + cache_read + cache_creation
                                input_tokens = usage.get("input_tokens", 0)
                                output_tokens = usage.get("output_tokens", 0)

                                logger.debug(
                                    f"[COST] Token usage: input={input_tokens}, output={output_tokens}"
                                )

                                # Extract cache tokens if available
                                cache_read_tokens = 0
                                cache_write_5m_tokens = 0
                                cache_write_1h_tokens = 0
                                cache_creation_total = 0

                                if "input_token_details" in usage:
                                    input_details = usage["input_token_details"]
                                    if isinstance(input_details, dict):
                                        cache_read_tokens = input_details.get(
                                            "cache_read", 0
                                        )
                                        cache_creation_total = input_details.get(
                                            "cache_creation", 0
                                        )
                                        cache_write_5m_val = input_details.get(
                                            "ephemeral_5m_input_tokens", 0
                                        )
                                        cache_write_5m_tokens = (
                                            int(cache_write_5m_val)
                                            if isinstance(
                                                cache_write_5m_val, (int, float)
                                            )
                                            else 0
                                        )
                                        cache_write_1h_val = input_details.get(
                                            "ephemeral_1h_input_tokens", 0
                                        )
                                        cache_write_1h_tokens = (
                                            int(cache_write_1h_val)
                                            if isinstance(
                                                cache_write_1h_val, (int, float)
                                            )
                                            else 0
                                        )

                                # Fallback: if TTL breakdown not available but total exists
                                if (
                                    cache_creation_total > 0
                                    and cache_write_5m_tokens == 0
                                    and cache_write_1h_tokens == 0
                                ):
                                    # Use worst-case (1-hour) pricing
                                    cache_write_1h_tokens = cache_creation_total

                                # Get service_tier for OpenAI models
                                service_tier = None
                                from consoul.config.models import OpenAIModelConfig

                                if isinstance(model_config, OpenAIModelConfig):
                                    service_tier = model_config.service_tier

                                # Calculate cost
                                cost_info = calculate_cost(
                                    self.current_model,
                                    input_tokens,
                                    output_tokens,
                                    cache_read_tokens=cache_read_tokens,
                                    cache_write_5m_tokens=cache_write_5m_tokens,
                                    cache_write_1h_tokens=cache_write_1h_tokens,
                                    service_tier=service_tier,
                                )

                                logger.debug(
                                    f"[COST] Calculation result: "
                                    f"pricing_available={cost_info['pricing_available']}, "
                                    f"total_cost={cost_info['total_cost']}"
                                )

                                if cost_info["pricing_available"]:
                                    estimated_cost = cost_info["total_cost"]
                                    logger.info(
                                        f"[COST] Estimated cost for message: ${estimated_cost:.6f}"
                                    )
                            except Exception as e:
                                logger.warning(
                                    f"[COST] Failed to calculate cost: {e}",
                                    exc_info=True,
                                )

                    assistant_bubble = MessageBubble(
                        response_text,
                        role="assistant",
                        show_metadata=True,
                        token_count=token_count,
                        tool_calls=tool_calls_list,
                        message_id=self._current_assistant_message_id,
                        thinking_content=thinking_content,
                        tokens_per_second=tokens_per_second,
                        time_to_first_token=time_to_first_token,
                        estimated_cost=estimated_cost,
                    )

                    # Temporarily disable auto_scroll to prevent premature scroll during MessageBubble mount
                    # We'll manually scroll after layout is complete
                    saved_auto_scroll = self.chat_view.auto_scroll
                    self.chat_view.auto_scroll = False

                    await self.chat_view.add_message(assistant_bubble)

                    # Restore auto_scroll
                    self.chat_view.auto_scroll = saved_auto_scroll

                    # Ensure we're scrolled to bottom if we were at bottom before removal
                    # This prevents the scroll position from jumping when widget is replaced
                    if chat_view_at_bottom:
                        # Store the expected minimum scroll height
                        # The MessageBubble should render at least as tall as the StreamingResponse was
                        expected_min_scroll = chat_view_scroll_y

                        logger.debug(
                            f"[SCROLL] Scheduling scroll after MessageBubble added - "
                            f"current_scroll_y: {self.chat_view.scroll_y}, "
                            f"max_scroll_y: {self.chat_view.max_scroll_y}, "
                            f"expected_min_scroll: {expected_min_scroll}"
                        )

                        # Use a polling approach to wait for layout completion
                        # The MessageBubble's Markdown widget needs time to render
                        scroll_attempts = 0
                        max_attempts = 50  # 500ms max (10ms * 50)
                        last_max_scroll = 0

                        def _check_and_scroll() -> None:
                            nonlocal scroll_attempts, last_max_scroll
                            scroll_attempts += 1
                            current_max_scroll = self.chat_view.max_scroll_y

                            logger.debug(
                                f"[SCROLL] Attempt {scroll_attempts} - "
                                f"scroll_y: {self.chat_view.scroll_y}, "
                                f"max_scroll_y: {current_max_scroll}, "
                                f"last_max_scroll: {last_max_scroll}, "
                                f"expected_min: {expected_min_scroll}"
                            )

                            # Layout is ready when:
                            # 1. We've reached the expected minimum height AND layout is stable
                            # 2. OR we've timed out
                            reached_expected_height = (
                                current_max_scroll >= expected_min_scroll
                            )
                            layout_stable = (
                                scroll_attempts
                                >= 3  # Wait at least 3 attempts before trusting stability
                                and current_max_scroll > 0
                                and current_max_scroll == last_max_scroll
                            )
                            timed_out = scroll_attempts >= max_attempts

                            # Only scroll if we've reached expected height or timed out
                            # Don't scroll early just because layout looks "stable" at a smaller size
                            if (reached_expected_height and layout_stable) or timed_out:
                                logger.debug(
                                    f"[SCROLL] Scrolling to bottom - "
                                    f"layout_stable: {layout_stable}, "
                                    f"reached_expected: {reached_expected_height}, "
                                    f"timed_out: {timed_out}, "
                                    f"scroll_y: {self.chat_view.scroll_y}, "
                                    f"max_scroll_y: {current_max_scroll}"
                                )
                                self.chat_view.scroll_end(animate=False)
                            else:
                                # Layout not ready yet, try again in 10ms
                                last_max_scroll = current_max_scroll
                                self.set_timer(0.01, _check_and_scroll)

                        # Start checking after initial refresh
                        self.chat_view.call_after_refresh(_check_and_scroll)
            elif self._stream_cancelled:
                # Show cancellation indicator
                await stream_widget.remove()
                cancelled_bubble = MessageBubble(
                    "_Stream cancelled by user_",
                    role="system",
                    show_metadata=False,
                )
                await self.chat_view.add_message(cancelled_bubble)

        except StreamingError as e:
            # Handle streaming errors with partial response
            self.log.error(f"Streaming error: {e}")

            # Hide typing indicator on error
            await self.chat_view.hide_typing_indicator()

            await stream_widget.remove()

            error_message = f"**Error:** {e}"
            if e.partial_response:
                error_message += (
                    f"\n\n**Partial response:**\n{e.partial_response[:500]}"
                )
                if len(e.partial_response) > 500:
                    error_message += "..."

            error_bubble = MessageBubble(
                error_message, role="error", show_metadata=False
            )
            await self.chat_view.add_message(error_bubble)

        except Exception as e:
            # Handle unexpected errors
            self.log.error(f"Unexpected error during streaming: {e}", exc_info=True)

            # Hide typing indicator on error
            await self.chat_view.hide_typing_indicator()

            # Only remove stream_widget if it was created
            if "stream_widget" in locals():
                await stream_widget.remove()

            error_bubble = MessageBubble(
                f"**Unexpected error:** {e}\n\nPlease check the logs for more details.",
                role="error",
                show_metadata=False,
            )
            await self.chat_view.add_message(error_bubble)

        finally:
            # Reset streaming state
            self._current_stream = None
            self.streaming = False
            self._update_top_bar_state()  # Update top bar streaming indicator

            # Restore focus to input area
            self.input_area.text_area.focus()

    async def _execute_tool(self, tool_call: ParsedToolCall) -> str:
        """Execute a tool and return its result.

        Handles execution errors gracefully, returning error message
        as tool result (so AI can see what went wrong).

        IMPORTANT: Tool execution runs in a thread pool executor to prevent
        blocking the Textual event loop. This keeps the UI responsive during
        long-running tool operations (e.g., bash commands, file I/O).

        Args:
            tool_call: Parsed tool call with name, arguments

        Returns:
            Tool execution result as string (stdout or error message)

        Example:
            >>> result = await self._execute_tool(tool_call)
            >>> print(result)  # "file1.txt\nfile2.py" or "Tool execution failed: ..."
        """
        try:
            # Use tool registry to execute any registered tool
            if self.tool_registry is None:
                return "Tool registry not initialized"

            # Get the tool from registry
            tool_metadata = None
            for meta in self.tool_registry.list_tools(enabled_only=True):
                if meta.tool.name == tool_call.name:
                    tool_metadata = meta
                    break

            if tool_metadata is None:
                return f"Unknown tool: {tool_call.name}"

            # Execute the tool using its invoke method
            # Run in executor to avoid blocking the event loop and freezing the UI
            import asyncio

            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                self._executor,
                tool_metadata.tool.invoke,
                tool_call.arguments,
            )
            return str(result)

        except Exception as e:
            # Return error as tool result (AI can see it and respond appropriately)
            self.log.error(f"Tool execution error: {e}", exc_info=True)
            return f"Tool execution failed: {e}"

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

    async def on_continue_with_tool_results(
        self, message: ContinueWithToolResults
    ) -> None:
        """Handle message to continue AI response with tool results.

        CRITICAL: Run in background task to prevent Textual from queuing events.
        Message handlers that do long async operations cause Textual to batch
        ALL widget events (keyboard, mouse, etc.) until the handler completes.

        Args:
            message: Message containing tool results
        """
        # Get tool results from stored state
        tool_results = [self._tool_results[tc.id] for tc in self._pending_tool_calls]

        # Run in background task, NOT in message handler context
        # This allows Textual to continue processing events normally
        import asyncio

        self._continue_task = asyncio.create_task(
            self._continue_with_tool_results(tool_results)
        )

    async def _continue_with_tool_results(
        self, tool_results: list[ToolMessage]
    ) -> None:
        """Continue AI response with tool results.

        Appends tool results to conversation and invokes model again
        to get final response incorporating the results.

        Args:
            tool_results: List of ToolMessage objects with execution results

        Example:
            >>> tool_results = [ToolMessage(content="...", tool_call_id="call_123")]
            >>> await self._continue_with_tool_results(tool_results)
        """

        self.log.info(
            f"[TOOL_FLOW] _continue_with_tool_results called with {len(tool_results)} results"
        )

        if not tool_results or not self.conversation or not self.chat_model:
            self.log.warning(
                f"[TOOL_FLOW] Skipping continuation - "
                f"tool_results={bool(tool_results)}, "
                f"conversation={bool(self.conversation)}, "
                f"chat_model={bool(self.chat_model)}"
            )
            return

        try:
            # Validate: Check that we have tool results for all pending tool calls
            expected_ids = {tc.id for tc in self._pending_tool_calls}
            actual_ids = {tr.tool_call_id for tr in tool_results}

            self.log.info(
                f"[TOOL_FLOW] Validating tool results - "
                f"Expected IDs: {expected_ids}, Actual IDs: {actual_ids}"
            )

            if expected_ids != actual_ids:
                missing = expected_ids - actual_ids
                extra = actual_ids - expected_ids
                self.log.warning(
                    f"[TOOL_FLOW] Tool call ID mismatch - Missing: {missing}, Extra: {extra}"
                )

            # Add tool results to conversation history and persist them
            self.log.info(
                f"[TOOL_FLOW] Adding {len(tool_results)} tool messages to conversation"
            )
            for tool_msg in tool_results:
                self.conversation.messages.append(tool_msg)
                # Persist to database for audit trail (critical for security)
                await self.conversation._persist_message(tool_msg)
                self.log.debug(
                    f"[TOOL_FLOW] Added tool message: id={tool_msg.tool_call_id}, "
                    f"content_length={len(tool_msg.content)}"
                )
                # Yield control after each persistence to keep UI responsive
                await asyncio.sleep(0)

            # Stream AI's final response with tool results
            # Reuse existing streaming infrastructure
            self.log.info(
                "[TOOL_FLOW] Calling _stream_ai_response to get model continuation"
            )
            await self._stream_ai_response()
            self.log.info("[TOOL_FLOW] _stream_ai_response completed")

        except Exception as e:
            self.log.error(
                f"[TOOL_FLOW] Error continuing with tool results: {e}", exc_info=True
            )

            # Hide typing indicator if shown
            await self.chat_view.hide_typing_indicator()

            # Show error to user
            error_bubble = MessageBubble(
                f"**Failed to get AI response after tool execution:**\n\n{e}\n\n"
                f"The tool results have been saved to conversation history.",
                role="error",
                show_metadata=False,
            )
            await self.chat_view.add_message(error_bubble)

    async def _handle_tool_calls(self, parsed_calls: list[ParsedToolCall]) -> None:
        """Handle tool calls by creating widgets and requesting approval.

        NEW EVENT-DRIVEN FLOW (SOUL-62, SOUL-63):
        1. Create widget with PENDING status for each tool call
        2. Emit ToolApprovalRequested message (non-blocking)
        3. Return immediately (approval happens in message handler)

        The approval flow continues via message handlers:
        - on_tool_approval_requested: Shows modal and waits for user
        - on_tool_approval_result: Executes tool and updates widget
        - After all tools complete, continues AI response

        Args:
            parsed_calls: List of ParsedToolCall objects from parser

        Note:
            This method is non-blocking. Tool execution happens asynchronously
            via the message passing system.
        """

        # Increment iteration counter
        self._tool_call_iterations += 1
        logger.debug(
            f"[TOOL_FLOW] Tool call iteration {self._tool_call_iterations} "
            f"with {len(parsed_calls)} tool(s)"
        )

        # Detect infinite loops by checking for repeated identical tool calls
        # Create signature of current tool call batch
        def _make_hashable(obj: Any) -> Any:
            """Convert an object to a hashable representation for signature tracking."""
            if isinstance(obj, dict):
                return frozenset((k, _make_hashable(v)) for k, v in obj.items())
            elif isinstance(obj, list):
                return tuple(_make_hashable(item) for item in obj)
            elif isinstance(obj, set):
                return frozenset(_make_hashable(item) for item in obj)
            else:
                # Primitive types (str, int, bool, None) are already hashable
                return obj

        call_signature = tuple(
            (
                call.name,
                _make_hashable(call.arguments)
                if isinstance(call.arguments, dict)
                else str(call.arguments),
            )
            for call in parsed_calls
        )

        # Check if this exact call was made in the last iteration
        if (
            hasattr(self, "_last_tool_signature")
            and call_signature == self._last_tool_signature  # type: ignore[has-type]
        ):
            logger.warning(
                "[TOOL_FLOW] Detected repeated identical tool call - stopping to prevent loop"
            )
            error_bubble = MessageBubble(
                "**Tool calling loop detected**\n\n"
                "The model made the same tool call twice in a row, indicating it's stuck.\n\n"
                "Try:\n"
                "- Using a more capable model (GPT-4, Claude, etc.)\n"
                "- Simplifying your request\n"
                "- Being more specific about what you want",
                role="error",
                show_metadata=False,
            )
            await self.chat_view.add_message(error_bubble)
            return

        # Store signature for next iteration
        self._last_tool_signature = call_signature

        # Store pending tool calls for tracking
        self._pending_tool_calls = list(parsed_calls)

        # Reset tool results for this new batch
        # Each call to _handle_tool_calls represents a new batch of tools
        # We must reset to avoid counting tools from previous iterations
        self._tool_results = {}
        logger.debug(
            f"[TOOL_FLOW] Reset tool results for new batch of {len(parsed_calls)} tools"
        )

        for tool_call in parsed_calls:
            logger.debug(
                f"[TOOL_FLOW] Tool call detected: {tool_call.name} with args: {tool_call.arguments}"
            )

            # Initialize tool call data with PENDING status
            self._tool_call_data[tool_call.id] = {
                "name": tool_call.name,
                "arguments": tool_call.arguments,
                "status": "PENDING",
                "result": None,
            }

            # Emit approval request message (non-blocking)
            # This will be handled by on_tool_approval_requested outside streaming context
            logger.debug(
                f"[TOOL_FLOW] Posting ToolApprovalRequested for {tool_call.name}"
            )
            self.post_message(ToolApprovalRequested(tool_call))
            logger.debug(
                f"[TOOL_FLOW] Posted ToolApprovalRequested for {tool_call.name}"
            )

    # Message handlers for tool approval workflow

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

            # Execute tool
            try:
                result = await self._execute_tool(message.tool_call)
                # Update tool call data with SUCCESS
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
