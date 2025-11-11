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
from textual.widgets import Footer

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel
    from textual.binding import BindingType

    from consoul.ai.history import ConversationHistory
    from consoul.config import ConsoulConfig
    from consoul.tui.widgets import ContextualTopBar, InputArea, StreamingResponse

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

        if consoul_config is not None:
            try:
                self.active_profile = consoul_config.get_active_profile()
                self.current_profile = self.active_profile.name
                self.current_model = consoul_config.current_model

                # Initialize chat model using current provider/model from config
                from consoul.ai import get_chat_model

                model_config = consoul_config.get_current_model_config()
                self.chat_model = get_chat_model(model_config, config=consoul_config)

                # Initialize conversation history
                from consoul.ai import ConversationHistory

                self.conversation = ConversationHistory(
                    model_name=consoul_config.current_model,
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
                    f"Initialized AI model: {consoul_config.current_model}, "
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

    def _update_top_bar_state(self) -> None:
        """Update ContextualTopBar reactive properties from app state."""
        if not hasattr(self, "top_bar"):
            return

        # Update provider and model (from config, not profile)
        if self.consoul_config:
            self.top_bar.current_provider = self.consoul_config.current_provider.value
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
            self.top_bar.conversation_count = self.conversation_list.conversation_count
        else:
            self.top_bar.conversation_count = 0

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

        # Track if this is the first message (conversation not yet in DB)
        is_first_message = (
            self.conversation.persist and not self.conversation._conversation_created
        )

        # Add to conversation history (creates DB conversation on first message)
        self.conversation.add_user_message(user_message)

        # Reload conversation list if this was the first message
        if is_first_message and hasattr(self, "conversation_list"):
            self.conversation_list.reload_conversations()
            self._update_top_bar_state()  # Update conversation count

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
        self._update_top_bar_state()  # Update top bar streaming indicator

        try:
            # Get trimmed messages for context window
            model_config = self.consoul_config.get_current_model_config()  # type: ignore[union-attr]
            reserve_tokens = model_config.max_tokens or 4096
            messages = self.conversation.get_trimmed_messages(  # type: ignore[union-attr]
                reserve_tokens=reserve_tokens
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

                # Yield to event loop to allow screen refresh
                import asyncio

                await asyncio.sleep(0)

            # Finalize streaming widget
            await stream_widget.finalize_stream()

            # Get complete response
            full_response = "".join(collected_tokens)

            if not self._stream_cancelled and full_response.strip():
                # Add to conversation history
                self.conversation.add_assistant_message(full_response)  # type: ignore[union-attr]

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
                                user_msg,
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
            self._update_top_bar_state()  # Update top bar streaming indicator

            # Restore focus to input area
            self.input_area.text_area.focus()

    # Action handlers (placeholders for Phase 2+)

    async def action_new_conversation(self) -> None:
        """Start a new conversation."""
        if self.conversation is not None and self.consoul_config:
            # Clear chat view
            await self.chat_view.clear_messages()

            # Create new conversation with same model
            from consoul.ai import ConversationHistory

            self.conversation = ConversationHistory(
                model_name=self.consoul_config.current_model,
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
                            (row_index, 0), title
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
                if self.conversation and self.consoul_config:
                    # Reload conversation history into current conversation object
                    from consoul.ai import ConversationHistory

                    self.conversation = ConversationHistory(
                        model_name=self.consoul_config.current_model,
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

    # ContextualTopBar message handlers

    async def on_contextual_top_bar_settings_requested(
        self, event: ContextualTopBar.SettingsRequested
    ) -> None:
        """Handle settings button click from top bar."""
        self.notify("Settings - Coming in SOUL-47", severity="information")

    async def on_contextual_top_bar_help_requested(
        self, event: ContextualTopBar.HelpRequested
    ) -> None:
        """Handle help button click from top bar."""
        self.notify("Help - Coming in SOUL-48", severity="information")

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

        def on_profile_selected(selected_profile: str | None) -> None:
            if selected_profile and selected_profile != self.current_profile:
                self._switch_profile(selected_profile)

        from consoul.tui.widgets import ProfileSelectorModal

        modal = ProfileSelectorModal(
            current_profile=self.current_profile,
            profiles=self.consoul_config.profiles,
        )
        self.push_screen(modal, on_profile_selected)

    async def on_contextual_top_bar_search_requested(
        self, event: ContextualTopBar.SearchRequested
    ) -> None:
        """Handle search request from top bar."""
        self.notify("Search - Coming in SOUL-45", severity="information")

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
            # Update active profile in config
            self.consoul_config.active_profile = profile_name
            self.active_profile = self.consoul_config.get_active_profile()
            self.current_profile = profile_name

            # NOTE: Model/provider remain unchanged - profiles are separate from models

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
            self.notify(f"Failed to switch profile: {e}", severity="error")
            self.log.error(f"Profile switch failed: {e}", exc_info=True)

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

            # Reinitialize chat model with new provider/model
            from consoul.ai import get_chat_model

            old_conversation_id = self.conversation_id

            model_config = self.consoul_config.get_current_model_config()
            self.chat_model = get_chat_model(model_config, config=self.consoul_config)

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
            self.notify(f"Failed to switch model/provider: {e}", severity="error")
            self.log.error(f"Model/provider switch failed: {e}", exc_info=True)
