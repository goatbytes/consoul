"""Main Consoul TUI application.

This module provides the primary ConsoulApp class that implements the Textual
terminal user interface for interactive AI conversations.
"""

from __future__ import annotations

import gc
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.coordinate import Coordinate
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Footer, Input

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel
    from langchain_core.messages import ToolMessage
    from textual.binding import BindingType

    from consoul.ai.history import ConversationHistory
    from consoul.ai.tools.parser import ParsedToolCall
    from consoul.config import ConsoulConfig
    from consoul.tui.widgets import (
        ContextualTopBar,
        InputArea,
        StreamingResponse,
    )
    from consoul.tui.widgets.input_area import AttachedFile

from consoul.tui.config import TuiConfig
from consoul.tui.css.themes import load_theme
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
        Binding("ctrl+e", "export_conversation", "Export", show=True),
        Binding("ctrl+i", "import_conversation", "Import", show=False),
        Binding("ctrl+s", "search_history", "Search", show=False),
        Binding("/", "focus_input", "Input", show=False),
        # UI
        Binding("ctrl+b", "toggle_sidebar", "Sidebar", show=True),
        Binding("ctrl+comma", "settings", "Settings", show=False),
        Binding("ctrl+shift+p", "permissions", "Permissions", show=True),
        Binding("f1", "help", "Help", show=False),
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

        # Load Consoul configuration for AI providers
        if consoul_config is None:
            from consoul.config import load_config

            try:
                consoul_config = load_config()
            except Exception as e:
                self.log.error(f"Failed to load configuration: {e}")
                consoul_config = None

        self.consoul_config = consoul_config

        # Initialize AI components
        self.chat_model: BaseChatModel | None = None
        self.conversation: ConversationHistory | None = None
        self.active_profile = None
        self.tool_registry = None

        if consoul_config is not None:
            try:
                self.active_profile = consoul_config.get_active_profile()
                self.current_profile = self.active_profile.name
                self.current_model = consoul_config.current_model

                # Initialize chat model using current provider/model from config
                from consoul.ai import get_chat_model

                model_config = consoul_config.get_current_model_config()
                self.chat_model = get_chat_model(model_config, config=consoul_config)

                # Note: Tools will be bound after registry is initialized (below)

                # Initialize conversation history with profile settings
                from consoul.ai import ConversationHistory

                conv_kwargs = self._get_conversation_config()
                self.conversation = ConversationHistory(
                    model_name=consoul_config.current_model,
                    model=self.chat_model,
                    **conv_kwargs,
                )

                # Add system prompt if configured
                if (
                    hasattr(self.active_profile, "system_prompt")
                    and self.active_profile.system_prompt
                ):
                    self.conversation.add_system_message(
                        self.active_profile.system_prompt
                    )

                # Set conversation ID for tracking
                self.conversation_id = self.conversation.session_id

                self.log.info(
                    f"Initialized AI model: {consoul_config.current_model}, "
                    f"session: {self.conversation_id}"
                )

                # Handle auto_resume if enabled in profile
                if (
                    self.active_profile
                    and hasattr(self.active_profile, "conversation")
                    and self.active_profile.conversation.auto_resume
                    and self.active_profile.conversation.persist
                ):
                    try:
                        from consoul.ai.database import ConversationDatabase

                        db = ConversationDatabase(
                            self.active_profile.conversation.db_path
                        )
                        recent_conversations = db.list_conversations(limit=1)

                        if recent_conversations:
                            latest_session_id = recent_conversations[0]["session_id"]
                            # Only resume if it's not the session we just created
                            if latest_session_id != self.conversation_id:
                                self.log.info(
                                    f"Auto-resuming last conversation: {latest_session_id}"
                                )
                                # Reload conversation with the latest session
                                conv_kwargs = self._get_conversation_config()
                                conv_kwargs["session_id"] = latest_session_id
                                self.conversation = ConversationHistory(
                                    model_name=consoul_config.current_model,
                                    model=self.chat_model,
                                    **conv_kwargs,
                                )
                                self.conversation_id = latest_session_id
                    except Exception as e:
                        self.log.warning(f"Failed to auto-resume conversation: {e}")

                # Handle retention_days cleanup if configured
                if (
                    self.active_profile
                    and hasattr(self.active_profile, "conversation")
                    and self.active_profile.conversation.retention_days > 0
                    and self.active_profile.conversation.persist
                ):
                    try:
                        from consoul.ai.database import ConversationDatabase

                        db = ConversationDatabase(
                            self.active_profile.conversation.db_path
                        )
                        deleted_count = db.delete_conversations_older_than(
                            self.active_profile.conversation.retention_days
                        )
                        if deleted_count > 0:
                            self.log.info(
                                f"Retention cleanup: deleted {deleted_count} conversations "
                                f"older than {self.active_profile.conversation.retention_days} days"
                            )
                    except Exception as e:
                        self.log.warning(f"Failed to cleanup old conversations: {e}")

                # Initialize tool registry (approval handled via _request_tool_approval)
                if consoul_config.tools and consoul_config.tools.enabled:
                    from consoul.ai.tools import RiskLevel, ToolRegistry
                    from consoul.ai.tools.implementations import (
                        append_to_file,
                        bash_execute,
                        code_search,
                        create_file,
                        delete_file,
                        edit_file_lines,
                        edit_file_search_replace,
                        find_references,
                        grep_search,
                        read_file,
                        read_url,
                        set_analyze_images_config,
                        set_bash_config,
                        set_code_search_config,
                        set_file_edit_config,
                        set_find_references_config,
                        set_grep_search_config,
                        set_read_config,
                        set_read_url_config,
                        set_web_search_config,
                        web_search,
                    )
                    from consoul.ai.tools.providers import CliApprovalProvider

                    # Configure bash tool with profile settings
                    if consoul_config.tools.bash:
                        set_bash_config(consoul_config.tools.bash)

                    # Configure read tool with profile settings
                    if consoul_config.tools.read:
                        set_read_config(consoul_config.tools.read)

                    # Configure grep_search tool with profile settings
                    if consoul_config.tools.grep_search:
                        set_grep_search_config(consoul_config.tools.grep_search)

                    # Configure code_search tool with profile settings
                    if consoul_config.tools.code_search:
                        set_code_search_config(consoul_config.tools.code_search)

                    # Configure find_references tool with profile settings
                    if consoul_config.tools.find_references:
                        set_find_references_config(consoul_config.tools.find_references)

                    # Configure web_search tool with profile settings
                    if consoul_config.tools.web_search:
                        set_web_search_config(consoul_config.tools.web_search)

                    # Configure read_url tool with profile settings
                    if consoul_config.tools.read_url:
                        set_read_url_config(consoul_config.tools.read_url)

                    # Configure file_edit tool with profile settings
                    if consoul_config.tools.file_edit:
                        set_file_edit_config(consoul_config.tools.file_edit)

                    # Configure image_analysis tool with profile settings
                    if consoul_config.tools.image_analysis:
                        set_analyze_images_config(consoul_config.tools.image_analysis)

                    # Create registry with CLI provider (we override approval in _request_tool_approval)
                    # The provider is required by registry but we don't use it - we show our own modal
                    self.tool_registry = ToolRegistry(
                        config=consoul_config.tools,
                        approval_provider=CliApprovalProvider(),  # Required but unused
                    )

                    # Register bash tool (risk level determined dynamically by CommandAnalyzer)
                    self.tool_registry.register(bash_execute, enabled=True)

                    # Register read tool (read-only, no side effects)
                    self.tool_registry.register(
                        read_file,
                        risk_level=RiskLevel.SAFE,
                        tags=["filesystem", "readonly"],
                        enabled=True,
                    )

                    # Register grep_search tool (read-only text search)
                    self.tool_registry.register(
                        grep_search,
                        risk_level=RiskLevel.SAFE,
                        tags=["search", "readonly"],
                        enabled=True,
                    )

                    # Register code_search tool (read-only AST search)
                    self.tool_registry.register(
                        code_search,
                        risk_level=RiskLevel.SAFE,
                        tags=["search", "readonly", "ast"],
                        enabled=True,
                    )

                    # Register find_references tool (read-only reference finder)
                    self.tool_registry.register(
                        find_references,
                        risk_level=RiskLevel.SAFE,
                        tags=["search", "readonly", "ast"],
                        enabled=True,
                    )

                    # Register web_search tool (read-only web search)
                    self.tool_registry.register(
                        web_search,
                        risk_level=RiskLevel.SAFE,
                        tags=["search", "readonly", "web"],
                        enabled=True,
                    )

                    # Register read_url tool (read-only URL fetching)
                    self.tool_registry.register(
                        read_url,
                        risk_level=RiskLevel.SAFE,
                        tags=["web", "readonly", "content"],
                        enabled=True,
                    )

                    # Register file edit tools
                    self.tool_registry.register(
                        create_file,
                        risk_level=RiskLevel.CAUTION,
                        tags=["filesystem", "write"],
                        enabled=True,
                    )

                    self.tool_registry.register(
                        edit_file_lines,
                        risk_level=RiskLevel.CAUTION,
                        tags=["filesystem", "write", "edit"],
                        enabled=True,
                    )

                    self.tool_registry.register(
                        edit_file_search_replace,
                        risk_level=RiskLevel.CAUTION,
                        tags=["filesystem", "write", "edit"],
                        enabled=True,
                    )

                    self.tool_registry.register(
                        append_to_file,
                        risk_level=RiskLevel.CAUTION,
                        tags=["filesystem", "write"],
                        enabled=True,
                    )

                    self.tool_registry.register(
                        delete_file,
                        risk_level=RiskLevel.DANGEROUS,
                        tags=["filesystem", "delete"],
                        enabled=True,
                    )

                    # NOTE: analyze_images tool registration disabled for SOUL-116
                    # The tool is meant for LLM-initiated image analysis, but for SOUL-116
                    # we handle image references directly by creating multimodal messages.
                    # Re-enable this when implementing SOUL-115 use case.
                    # self._sync_vision_tool_registration()

                    # Get tool metadata list
                    tool_metadata_list = self.tool_registry.list_tools(
                        enabled_only=True
                    )

                    self.log.info(
                        f"Initialized tool registry with {len(tool_metadata_list)} tools"
                    )

                    # Bind tools to model (extract BaseTool from metadata)
                    if tool_metadata_list:
                        # Check if model supports tool calling
                        from consoul.ai.providers import supports_tool_calling

                        if supports_tool_calling(self.chat_model):
                            tools = [meta.tool for meta in tool_metadata_list]
                            self.chat_model = self.chat_model.bind_tools(tools)  # type: ignore[assignment]
                            self.log.info(f"Bound {len(tools)} tools to chat model")
                        else:
                            self.log.warning(
                                f"Model {self.current_model} does not support tool calling. "
                                "Tools are disabled for this model."
                            )

            except Exception as e:
                # Log error but allow app to start (graceful degradation)
                import traceback

                self.log.error(
                    f"Failed to initialize AI model: {e}\n{traceback.format_exc()}"
                )
                self.chat_model = None
                self.conversation = None

        # Initialize title generator if enabled
        self.title_generator = None
        if self.config.auto_generate_titles:
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
                    detected = auto_detect_title_config(consoul_config)
                    if detected:
                        provider = provider or detected["provider"]
                        model = model or detected["model"]
                    else:
                        # No suitable model available, disable feature
                        self.log.info(
                            "Auto-title generation disabled: no suitable model found"
                        )
                        provider = None

                if provider and model:
                    self.title_generator = TitleGenerator(
                        provider=provider,
                        model_name=model,
                        prompt_template=self.config.auto_title_prompt,
                        max_tokens=self.config.auto_title_max_tokens,
                        temperature=self.config.auto_title_temperature,
                        api_key=self.config.auto_title_api_key,
                        config=consoul_config,
                    )
                    self.log.info(f"Title generator initialized: {provider}/{model}")

            except Exception as e:
                self.log.warning(f"Failed to initialize title generator: {e}")
                self.title_generator = None

        # Streaming state
        self._current_stream: StreamingResponse | None = None
        self._stream_cancelled = False

        # Tool execution state (for tracking pending tool approvals)
        self._pending_tool_calls: list[ParsedToolCall] = []
        self._tool_results: dict[str, ToolMessage] = {}  # Map tool_call_id -> result
        self._tool_call_data: dict[
            str, dict[str, Any]
        ] = {}  # Map tool_call_id -> display data
        self._tool_call_iterations = (
            0  # Track tool calling rounds to prevent infinite loops
        )
        self._max_tool_iterations = (
            5  # Maximum rounds of tool calls before forcing stop
        )
        # Track current assistant message ID for linking tool calls in database
        self._current_assistant_message_id: int | None = None

    def on_mount(self) -> None:
        """Initialize app after mounting (message pump is running).

        Sets up GC management and validates theme.
        """
        # Apply theme from config
        # Custom themes (TCSS files): monokai, dracula, nord, gruvbox
        # Built-in themes: textual-dark, textual-light, textual-ansi, tokyo-night, etc.
        custom_themes = ["monokai", "dracula", "nord", "gruvbox"]

        if self.config.theme in custom_themes:
            # Load custom TCSS theme
            try:
                _ = load_theme(self.config.theme)  # type: ignore[arg-type]
                self.theme = self.config.theme
            except FileNotFoundError:
                self.notify(
                    f"Theme '{self.config.theme}' not found, using default",
                    severity="warning",
                )
        else:
            # Use Textual built-in theme
            self.theme = self.config.theme

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

    def on_unmount(self) -> None:
        """Cleanup when app unmounts (library-first design).

        Restores original GC state to avoid affecting embedding applications.
        """
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
        except Exception as e:
            logger.error(f"Error updating top bar state: {e}", exc_info=True)

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
        import time

        from consoul.tui.widgets import MessageBubble

        t0 = time.time()
        logger.info("[TIMING] Message submit handler started")

        user_message = event.content

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

        t1 = time.time()
        logger.info(f"[TIMING] Model check complete: {(t1 - t0) * 1000:.1f}ms")

        # Reset tool call tracking for new user message
        self._tool_call_data = {}
        self._tool_results = {}
        self._tool_call_iterations = 0
        if hasattr(self, "_last_tool_signature"):
            del self._last_tool_signature  # type: ignore[has-type]

        t2 = time.time()
        logger.info(f"[TIMING] Reset tracking: {(t2 - t1) * 1000:.1f}ms")

        # Add user message to chat view FIRST for immediate visual feedback
        user_bubble = MessageBubble(user_message, role="user", show_metadata=True)
        await self.chat_view.add_message(user_bubble)

        t3 = time.time()
        logger.info(f"[TIMING] Added message bubble: {(t3 - t2) * 1000:.1f}ms")

        # Show typing indicator immediately
        await self.chat_view.show_typing_indicator()

        t4 = time.time()
        logger.info(f"[TIMING] Added typing indicator: {(t4 - t3) * 1000:.1f}ms")

        # The real issue: everything after this point blocks the event loop
        # We need to move ALL remaining work to a background worker
        # so the UI stays responsive during "Thinking..." phase

        t5 = time.time()
        logger.info(
            f"[TIMING] Starting background processing: {(t5 - t4) * 1000:.1f}ms"
        )

        # Track if this is the first message (conversation not yet in DB)
        is_first_message = (
            self.conversation.persist and not self.conversation._conversation_created
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

        self.conversation.messages.append(message)

        # Move EVERYTHING to a background worker to keep UI responsive
        async def _process_and_stream() -> None:
            t6 = time.time()
            logger.info(
                f"[TIMING] Worker started: {(t6 - t0) * 1000:.1f}ms from submit"
            )

            # Persist to DB in background
            if (
                self.conversation is not None
                and is_first_message
                and self.conversation._db
            ):
                try:
                    import asyncio

                    loop = asyncio.get_event_loop()
                    self.conversation.session_id = await loop.run_in_executor(
                        None,
                        self.conversation._db.create_conversation,
                        self.conversation.model_name,
                    )
                    self.conversation._conversation_created = True
                    logger.info(
                        f"Created conversation session: {self.conversation.session_id}"
                    )
                except Exception as e:
                    logger.warning(f"Failed to create conversation in DB: {e}")
                    self.conversation.persist = False

            # Persist message to DB and save attachments
            if self.conversation is not None and self.conversation.persist:
                try:
                    user_message_id = await self.conversation._persist_message(message)
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

            # Reload conversation list if first message
            if is_first_message and hasattr(self, "conversation_list"):
                await self.conversation_list.reload_conversations()
                self._update_top_bar_state()

            t7 = time.time()
            logger.info(f"[TIMING] DB persist complete: {(t7 - t6) * 1000:.1f}ms")

            # Start streaming AI response
            logger.info("[TIMING] About to call _stream_ai_response")
            await self._stream_ai_response()

            t8 = time.time()
            logger.info(
                f"[TIMING] Worker complete: {(t8 - t6) * 1000:.1f}ms, total: {(t8 - t0) * 1000:.1f}ms"
            )

        # Fire off all processing in background worker
        # This keeps the UI responsive during the entire "Thinking..." phase
        self.run_worker(_process_and_stream(), exclusive=False)

        logger.info(
            f"[TIMING] Message handler exiting, worker launched: {(time.time() - t0) * 1000:.1f}ms"
        )

    async def _stream_ai_response(self) -> None:
        """Stream AI response token-by-token to TUI.

        Uses StreamingResponse widget for real-time token display,
        then converts to MessageBubble when complete.

        Runs the blocking LangChain stream() call in a background worker
        to prevent freezing the UI event loop.
        """
        import time

        from consoul.ai.exceptions import StreamingError
        from consoul.ai.history import to_dict_message
        from consoul.tui.widgets import MessageBubble, StreamingResponse

        s0 = time.time()
        logger.info("[TIMING] _stream_ai_response ENTRY")

        # DEBUG: Log entry to verify this method is called
        logger.debug(
            f"[TOOL_FLOW] _stream_ai_response ENTRY - iteration {self._tool_call_iterations}/{self._max_tool_iterations}"
        )

        # Update streaming state
        self._stream_cancelled = False
        self.streaming = True  # Update reactive state
        self._update_top_bar_state()  # Update top bar streaming indicator

        s1 = time.time()
        logger.info(f"[TIMING] Updated streaming state: {(s1 - s0) * 1000:.1f}ms")

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

            s2 = time.time()
            logger.info(f"[TIMING] Got model config: {(s2 - s1) * 1000:.1f}ms")

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
                messages = await loop.run_in_executor(
                    None,
                    self.conversation.get_trimmed_messages,  # type: ignore[union-attr]
                    reserve_tokens,
                )

            s3 = time.time()
            logger.info(f"[TIMING] Got trimmed messages: {(s3 - s2) * 1000:.1f}ms")

            self.log.info(
                f"[TOOL_FLOW] _stream_ai_response starting - "
                f"iteration={self._tool_call_iterations}/{self._max_tool_iterations}, "
                f"conversation_messages={len(self.conversation.messages) if self.conversation else 0}, "
                f"trimmed_messages={len(messages)}"
            )

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
                    None, lambda: [to_dict_message(msg) for msg in messages]
                )

            s4 = time.time()
            logger.info(
                f"[TIMING] Converted to dict: {(s4 - s3) * 1000:.1f}ms, total prep: {(s4 - s0) * 1000:.1f}ms"
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

                            # Create final message with all content and tool_calls
                            final_message = AIMessage(
                                content="".join(content_parts),
                                tool_calls=tool_calls if tool_calls else [],
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
            first_token = await token_queue.get()
            logger.debug(
                f"[TOOL_FLOW] Got first_token: is_none={first_token is None}, value={first_token[:50] if first_token else 'None'}"
            )

            # Hide typing indicator and create streaming response widget
            await self.chat_view.hide_typing_indicator()
            stream_widget = StreamingResponse(renderer="hybrid")
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
                await stream_widget.add_token(first_token)

                # Consume remaining tokens from queue and update UI in real-time
                while True:
                    token = await token_queue.get()

                    # None = sentinel, stream is done
                    if token is None:
                        break

                    # Check for cancellation
                    if self._stream_cancelled:
                        break

                    # Add token to UI immediately
                    collected_tokens.append(token)
                    await stream_widget.add_token(token)

                    # Yield to event loop to allow screen refresh
                    import asyncio

                    await asyncio.sleep(0)

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
                # Add to conversation history
                # Important: Use final_message directly to preserve tool_calls attribute
                if final_message:
                    self.conversation.messages.append(final_message)  # type: ignore[union-attr]
                    # Persist to DB and capture message ID for linking tool calls
                    self._current_assistant_message_id = (
                        await self.conversation._persist_message(  # type: ignore[union-attr]
                            final_message
                        )
                    )
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

                            # Show minimal tool execution indicator
                            tool_names = ", ".join([call.name for call in parsed_calls])
                            tool_indicator = MessageBubble(
                                f"🔧 Executing: {tool_names}",
                                role="system",
                                show_metadata=False,
                            )
                            await self.chat_view.add_message(tool_indicator)

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

                        token_count = self.conversation._token_counter(  # type: ignore[union-attr]
                            [AIMessage(content=full_response)]
                        )
                    except Exception:
                        # Fallback to character approximation if token counting fails
                        token_count = len(full_response) // 4

                    assistant_bubble = MessageBubble(
                        full_response,
                        role="assistant",
                        show_metadata=True,
                        token_count=token_count,
                        tool_calls=tool_calls_list,
                    )
                    await self.chat_view.add_message(assistant_bubble)
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
                None,  # Use default executor
                tool_metadata.tool.invoke,
                tool_call.arguments,
            )
            return str(result)

        except Exception as e:
            # Return error as tool result (AI can see it and respond appropriately)
            self.log.error(f"Tool execution error: {e}", exc_info=True)
            return f"Tool execution failed: {e}"

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

        if message.approved:
            # Update tool call data to EXECUTING
            self._tool_call_data[message.tool_call.id]["status"] = "EXECUTING"
            self.log.info(
                f"[TOOL_FLOW] Executing approved tool: {message.tool_call.name}"
            )

            # Log execution start
            start_time = time.time()
            if self.tool_registry and self.tool_registry.audit_logger:
                await self.tool_registry.audit_logger.log_event(
                    AuditEvent(
                        event_type="execution",
                        tool_name=message.tool_call.name,
                        arguments=message.tool_call.arguments,
                    )
                )

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

        # Check if all tools are done
        completed = len(self._tool_results)
        total = len(self._pending_tool_calls)
        logger.debug(
            f"[TOOL_FLOW] Tool completion status: {completed}/{total} tools completed"
        )

        if completed == total:
            # All tools completed - feed results back to AI
            logger.debug(
                f"[TOOL_FLOW] All {total} tools completed, continuing with tool results"
            )
            tool_results = [
                self._tool_results[tc.id] for tc in self._pending_tool_calls
            ]
            await self._continue_with_tool_results(tool_results)
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
                None,
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
                    None,
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

            # Create new conversation with same model and profile settings
            from consoul.ai import ConversationHistory

            conv_kwargs = self._get_conversation_config()
            self.conversation = ConversationHistory(
                model_name=self.consoul_config.current_model,
                model=self.chat_model,
                **conv_kwargs,
            )

            # Re-add system prompt if configured
            if self.active_profile and hasattr(self.active_profile, "system_prompt"):
                system_prompt = self.active_profile.system_prompt
                if system_prompt:
                    self.conversation.add_system_message(system_prompt)

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
            return

        result = await self.push_screen(  # type: ignore[func-returns-value]
            SettingsScreen(config=self.config, consoul_config=self.consoul_config)
        )
        if result:
            self.notify("Settings saved successfully", severity="information")

    async def action_permissions(self) -> None:
        """Show permission manager screen."""
        from consoul.tui.widgets.permission_manager_screen import (
            PermissionManagerScreen,
        )

        if self.consoul_config is None:
            self.notify("Configuration not loaded", severity="error")
            return

        result = await self.push_screen(PermissionManagerScreen(self.consoul_config))  # type: ignore[func-returns-value]
        if result:
            self.notify(
                "Permission settings saved successfully", severity="information"
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

    def action_toggle_sidebar(self) -> None:
        """Toggle conversation list sidebar visibility."""
        if not hasattr(self, "conversation_list"):
            return

        # Toggle display
        self.conversation_list.display = not self.conversation_list.display

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
                # Find and update the row in conversation list
                for row_index, row_key in enumerate(
                    self.conversation_list.table.rows.keys()
                ):
                    if str(row_key.value) == session_id:
                        self.conversation_list.table.update_cell_at(
                            Coordinate(row_index, 0), title
                        )
                        self.log.debug("Updated conversation list UI with title")
                        break

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

        # Clear current chat view
        await self.chat_view.clear_messages()

        # Load conversation from database with full metadata for UI reconstruction
        if self.consoul_config:
            try:
                # Use load_conversation_full to get tool_calls and attachments
                messages = self.conversation_list.db.load_conversation_full(
                    conversation_id
                )

                # Display messages in chat view with proper UI reconstruction
                from consoul.tui.widgets import MessageBubble

                for msg in messages:
                    role = msg["role"]
                    content = msg["content"]
                    tool_calls = msg.get("tool_calls", [])
                    attachments = msg.get("attachments", [])

                    # Skip system and tool messages in display
                    # Tool results are shown via the 🛠 button modal
                    if role in ("system", "tool"):
                        continue

                    # Handle multimodal content (deserialize JSON if needed)
                    display_content = self._extract_display_content(content)

                    # Show tool execution indicator for assistant messages with tools
                    if tool_calls and role == "assistant":
                        tool_names = ", ".join(
                            [tc.get("tool_name", "unknown") for tc in tool_calls]
                        )
                        tool_indicator = MessageBubble(
                            f"🔧 Executing: {tool_names}",
                            role="system",
                            show_metadata=False,
                        )
                        await self.chat_view.add_message(tool_indicator)

                    # Create assistant message bubble (with tool button if tools exist)
                    if display_content or (role == "assistant" and not tool_calls):
                        bubble = MessageBubble(
                            display_content or "",
                            role=role,
                            show_metadata=True,
                            tool_calls=tool_calls if tool_calls else None,
                        )
                        await self.chat_view.add_message(bubble)

                    # Display attachments for user messages
                    if attachments and role == "user":
                        await self._display_reconstructed_attachments(attachments)

                # Update conversation ID to resume this conversation
                self.conversation_id = conversation_id

                # Update the conversation object if we have one
                if self.conversation and self.consoul_config:
                    # Reload conversation history into current conversation object with profile settings
                    from consoul.ai import ConversationHistory

                    conv_kwargs = self._get_conversation_config()
                    conv_kwargs["session_id"] = (
                        conversation_id  # Resume this specific session
                    )
                    self.conversation = ConversationHistory(
                        model_name=self.consoul_config.current_model,
                        model=self.chat_model,
                        **conv_kwargs,
                    )

                self.notify(
                    f"Loaded conversation {conversation_id[:8]}...",
                    severity="information",
                )

            except Exception as e:
                self.log.error(f"Failed to load conversation: {e}")
                self.notify(f"Failed to load conversation: {e}", severity="error")

    # ContextualTopBar message handlers

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

    async def on_contextual_top_bar_theme_switch_requested(
        self, event: ContextualTopBar.ThemeSwitchRequested
    ) -> None:
        """Handle theme switch request from top bar."""
        self.notify("Theme switching - Coming in SOUL-49", severity="information")

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
                    await self.conversation_list.search(current_query)
                    # Update match count in search bar (only when searching)
                    result_count = len(self.conversation_list.table.rows)
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
            # Get old database path before switching
            old_db_path = (
                self.active_profile.conversation.db_path
                if self.active_profile
                else None
            )

            # Update active profile in config
            self.consoul_config.active_profile = profile_name
            self.active_profile = self.consoul_config.get_active_profile()
            self.current_profile = profile_name

            # NOTE: Model/provider remain unchanged - profiles are separate from models

            # Check if database path changed
            new_db_path = self.active_profile.conversation.db_path
            if old_db_path != new_db_path:
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

            # Update conversation with new system prompt if needed
            if self.conversation and self.active_profile.system_prompt:
                # Clear and re-add system message with new prompt
                # (This preserves conversation history but updates instructions)
                self.conversation.clear(preserve_system=False)
                self.conversation.add_system_message(self.active_profile.system_prompt)

            # Update top bar display
            self._update_top_bar_state()

            self.notify(
                f"Switched to profile '{profile_name}' (model unchanged: {self.current_model})",
                severity="information",
            )
            self.log.info(
                f"Profile switched: {profile_name}, model preserved: {self.current_model}"
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
