"""Main Consoul TUI application.

This module provides the primary ConsoulApp class that implements the Textual
terminal user interface for interactive AI conversations.
"""

from __future__ import annotations

import gc
from typing import TYPE_CHECKING, ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.reactive import reactive
from textual.widgets import Footer, Header

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel
    from textual.binding import BindingType

    from consoul.ai.history import ConversationHistory
    from consoul.config import ConsoulConfig
    from consoul.tui.widgets import InputArea, StreamingResponse

from consoul.tui.config import TuiConfig
from consoul.tui.css.themes import load_theme

__all__ = ["ConsoulApp"]


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
        Binding("ctrl+n", "new_conversation", "New Chat"),
        Binding("ctrl+l", "clear_conversation", "Clear"),
        Binding("escape", "cancel_stream", "Cancel", show=False),
        # Navigation
        Binding("ctrl+p", "switch_profile", "Profile", show=False),
        Binding("ctrl+m", "switch_model", "Model", show=False),
        Binding("ctrl+e", "export_conversation", "Export", show=False),
        Binding("ctrl+s", "search_history", "Search", show=False),
        Binding("/", "focus_input", "Input", show=False),
        # UI
        Binding("ctrl+comma", "settings", "Settings", show=False),
        Binding("ctrl+t", "cycle_theme", "Theme", show=False),
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

        if consoul_config is not None:
            try:
                self.active_profile = consoul_config.get_active_profile()
                self.current_profile = self.active_profile.name
                self.current_model = self.active_profile.model.model

                # Initialize chat model
                from consoul.ai import get_chat_model

                self.chat_model = get_chat_model(
                    self.active_profile.model, config=consoul_config
                )

                # Initialize conversation history
                from consoul.ai import ConversationHistory

                self.conversation = ConversationHistory(
                    model_name=self.active_profile.model.model,
                    model=self.chat_model,
                    persist=True,  # Enable SQLite persistence
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
                    f"Initialized AI model: {self.active_profile.model.model}, "
                    f"session: {self.conversation_id}"
                )

            except Exception as e:
                # Log error but allow app to start (graceful degradation)
                import traceback

                self.log.error(
                    f"Failed to initialize AI model: {e}\n{traceback.format_exc()}"
                )
                self.chat_model = None
                self.conversation = None

        # Streaming state
        self._current_stream: StreamingResponse | None = None
        self._stream_cancelled = False

    def on_mount(self) -> None:
        """Initialize app after mounting (message pump is running).

        Sets up GC management and validates theme.
        """
        # Validate theme (can safely notify now that message pump is running)
        try:
            _ = load_theme(self.config.theme)  # type: ignore[arg-type]
        except FileNotFoundError:
            self.notify(
                f"Theme '{self.config.theme}' not found, using default",
                severity="warning",
            )

        # Set up GC management (streaming-aware mode from research)
        if self.config.gc_mode == "streaming-aware":
            gc.disable()
            self._gc_interval_timer = self.set_interval(
                self.config.gc_interval_seconds, self._idle_gc
            )

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

        from consoul.tui.widgets import ChatView, ConversationList, InputArea

        yield Header()

        # Main content area with optional sidebar
        with Horizontal(classes="main-container"):
            # Conversation list sidebar (conditional)
            if self.config.show_sidebar and self.consoul_config:
                from consoul.ai.database import ConversationDatabase

                db = ConversationDatabase()
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

        # Add user message to chat view
        user_bubble = MessageBubble(user_message, role="user", show_metadata=True)
        await self.chat_view.add_message(user_bubble)

        # Add to conversation history
        self.conversation.add_user_message(user_message)

        # Start streaming AI response
        await self._stream_ai_response()

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

        # Create streaming response widget
        stream_widget = StreamingResponse(renderer="hybrid")
        await self.chat_view.add_message(stream_widget)

        # Track for cancellation
        self._current_stream = stream_widget
        self._stream_cancelled = False
        self.streaming = True  # Update reactive state

        try:
            # Get trimmed messages for context window
            messages = self.conversation.get_trimmed_messages(  # type: ignore[union-attr]
                reserve_tokens=self.active_profile.model.max_tokens or 4096  # type: ignore[union-attr]
            )

            # Convert to dict format for LangChain
            messages_dict = [to_dict_message(msg) for msg in messages]

            # Stream tokens in background worker to avoid blocking UI
            collected_tokens: list[str] = []

            # Use asyncio.Queue to stream tokens from background thread to UI
            import asyncio

            token_queue: asyncio.Queue[str | None] = asyncio.Queue()

            # Get the current event loop (Textual's loop)
            event_loop = asyncio.get_running_loop()

            def sync_stream_producer() -> None:
                """Background thread: stream tokens and push to queue.

                Sends None as sentinel when complete or cancelled.
                """
                try:
                    for chunk in self.chat_model.stream(messages_dict):  # type: ignore[union-attr]
                        # Check for cancellation
                        if self._stream_cancelled:
                            break

                        # Skip empty chunks
                        if not chunk.content:
                            continue

                        token = chunk.content
                        # Push token to queue (thread-safe)
                        asyncio.run_coroutine_threadsafe(
                            token_queue.put(token), event_loop
                        )

                except Exception as e:
                    # Push exception as string
                    asyncio.run_coroutine_threadsafe(
                        token_queue.put(f"ERROR: {e}"), event_loop
                    )
                finally:
                    # Send sentinel to signal completion
                    asyncio.run_coroutine_threadsafe(token_queue.put(None), event_loop)

            # Start background thread
            import threading

            stream_thread = threading.Thread(target=sync_stream_producer, daemon=True)
            stream_thread.start()

            # Consume tokens from queue and update UI in real-time
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

            # Finalize streaming widget
            await stream_widget.finalize_stream()

            # Get complete response
            full_response = "".join(collected_tokens)

            if not self._stream_cancelled and full_response.strip():
                # Add to conversation history
                self.conversation.add_assistant_message(full_response)  # type: ignore[union-attr]

                # Replace StreamingResponse with MessageBubble for permanent display
                await stream_widget.remove()

                assistant_bubble = MessageBubble(
                    full_response,
                    role="assistant",
                    show_metadata=True,
                    token_count=len(collected_tokens),
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

            # Restore focus to input area
            self.input_area.text_area.focus()

    # Action handlers (placeholders for Phase 2+)

    async def action_new_conversation(self) -> None:
        """Start a new conversation."""
        if self.conversation is not None:
            # Clear chat view
            await self.chat_view.clear_messages()

            # Create new conversation with same model
            from consoul.ai import ConversationHistory

            self.conversation = ConversationHistory(
                model_name=self.active_profile.model.model,  # type: ignore[union-attr]
                model=self.chat_model,
                persist=True,  # New session ID will be created
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
        self.notify("Export (Phase 4)")

    def action_search_history(self) -> None:
        """Show search interface."""
        self.notify("Search (Phase 4)")

    def action_focus_input(self) -> None:
        """Focus the input area."""
        self.notify("Focus input (Phase 2)")

    def action_settings(self) -> None:
        """Show settings screen."""
        self.notify("Settings (Phase 4)")

    def action_cycle_theme(self) -> None:
        """Cycle to next theme."""
        self.notify("Theme cycling (Phase 4)")

    def action_help(self) -> None:
        """Show help modal."""
        self.notify("Help (Phase 4)")

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

        # Load conversation from database
        if self.consoul_config:
            try:
                from consoul.ai.database import ConversationDatabase

                db = ConversationDatabase()
                messages = db.load_conversation(conversation_id)

                # Display messages in chat view
                from consoul.tui.widgets import MessageBubble

                for msg in messages:
                    role = msg["role"]
                    content = msg["content"]

                    # Skip system messages in display
                    if role == "system":
                        continue

                    bubble = MessageBubble(
                        content,
                        role=role,
                        show_metadata=True,
                    )
                    await self.chat_view.add_message(bubble)

                # Update conversation ID to resume this conversation
                self.conversation_id = conversation_id

                # Update the conversation object if we have one
                if self.conversation:
                    # Reload conversation history into current conversation object
                    from consoul.ai import ConversationHistory

                    self.conversation = ConversationHistory(
                        model_name=self.active_profile.model.model,  # type: ignore[union-attr]
                        model=self.chat_model,
                        persist=True,
                        session_id=conversation_id,
                    )

                self.notify(
                    f"Loaded conversation {conversation_id[:8]}...",
                    severity="information",
                )

            except Exception as e:
                self.log.error(f"Failed to load conversation: {e}")
                self.notify(f"Failed to load conversation: {e}", severity="error")
