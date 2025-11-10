# Consoul TUI Research & Architecture Planning

**Date:** 2025-11-09
**Purpose:** Guide TUI development based on Gira, Postings, and Textual best practices

---

## Executive Summary

This research examines two exemplary Textual TUI applications (Gira and Postings) to inform Consoul's TUI architecture. Key findings:

1. **Library-First Design**: Since Consoul will be used as a library in Gira and other projects, the TUI should be cleanly separated from core functionality
2. **Proven Patterns**: Both apps demonstrate robust patterns for widgets, state management, and user interaction
3. **Streaming Focus**: Consoul's unique requirement is streaming AI responses, requiring specialized widgets

---

## Architecture Analysis

### 1. Gira TUI Architecture

**File Structure:**
```
gira/tui/
├── app.py              # Main TuiApp class (120KB, highly complex)
├── cli.py              # CLI entry point and logging setup
├── config.py           # TUI-specific configuration
├── css/                # Textual CSS stylesheets
│   ├── main.tcss
│   ├── kanban.tcss
│   └── themes/
├── services/           # Background services
│   └── blame_service.py
├── themes/             # Theme system
│   ├── models.py
│   └── loader.py
├── utils/              # Utilities
│   ├── error_handling.py
│   ├── terminal_detection.py
│   └── data_integration.py
└── widgets/            # 70+ widget files
    ├── base/           # Base widget classes
    ├── kanban_board.py
    ├── navigation_sidebar.py
    ├── contextual_top_bar.py
    ├── ticket_details_modal.py
    └── ... (many specialized widgets)
```

**Key Architectural Patterns:**

1. **Reactive State Management**
   ```python
   current_project: reactive[str] = reactive("")
   project_root: reactive[Optional[Path]] = reactive(None)
   current_section: reactive[str] = reactive("board")
   app_loading: reactive[bool] = reactive(True)
   ```

2. **View-Based Navigation**
   - Multiple views: KanbanBoard, BacklogView, EpicView, BlameView, etc.
   - Sidebar for navigation between views
   - Contextual top bar showing view-specific actions

3. **Modal System**
   - Heavy use of modals for create/edit operations
   - Modal-only mode support (GCM-1177: show ticket details without full UI)
   - Confirmation modals for destructive actions

4. **Signal Handlers & Lifecycle**
   - SIGUSR1 for external refresh
   - Comprehensive error handling with ErrorHandler class
   - Terminal cleanup on exit (mouse tracking, cursor, alt screen)
   - GC management (disabled automatic GC to prevent UI freezes)

5. **Service Layer**
   - BlameDataService for async git operations
   - Separation of data loading from UI rendering

6. **Configuration**
   ```python
   class TuiConfig:
       theme: str
       force_keyboard_mode: bool
       mouse_drag_enabled: bool
       # ... TUI-specific settings
   ```

**Key Bindings (Gira):**
```python
BINDINGS = [
    Binding("q", "quit", "Quit", priority=True),
    Binding("n", "create_item", "New"),
    Binding("enter", "view_item", "View"),
    Binding("r", "refresh", "Refresh"),
    Binding("b", "switch_to_board", "Board", show=False),
    Binding("m", "toggle_sidebar", "Sidebar", show=False),
    Binding("/", "search", "Search", show=False),
    Binding("ctrl+t", "cycle_theme", "Theme", show=False),
    # ... many more
]
```

---

### 2. Postings TUI Architecture

**File Structure:**
```
posting/
├── app.py              # Main Posting app
├── config.py           # Settings with pydantic
├── commands.py         # Command palette provider
├── help_screen.py      # Help modal
├── jump_overlay.py     # Jump mode for focus navigation
├── themes.py           # Theme management
├── widgets/
│   ├── collection/     # Collection browser
│   ├── request/        # Request editor components
│   │   ├── request_editor.py (tabbed)
│   │   ├── header_editor.py
│   │   ├── request_body.py
│   │   ├── url_bar.py
│   │   └── ...
│   ├── response/       # Response display
│   │   ├── response_area.py
│   │   ├── response_trace.py
│   │   └── script_output.py
│   ├── datatable.py
│   ├── input.py
│   └── text_area.py
└── posting.scss        # SCSS for styling
```

**Key Patterns:**

1. **Tabbed Content**
   ```python
   class RequestEditor(Vertical):
       def compose(self):
           with RequestEditorTabbedContent():
               with TabPane("Headers", id="headers-pane"):
                   yield HeaderEditor()
               with TabPane("Body", id="body-pane"):
                   yield Lazy(RequestBodyEditor())
               # ... more tabs
   ```

2. **Lazy Loading**
   - Uses `Lazy()` for tabs that aren't immediately visible
   - Performance optimization for complex widgets

3. **Command Palette**
   - Custom CommandProvider for app-specific commands
   - Fuzzy search for actions

4. **Jump Mode**
   - `ctrl+o` activates jump overlay
   - Quick keyboard navigation between widgets
   - Similar to vim-style "hints"

5. **Settings Management**
   ```python
   # Pydantic-based settings
   class Settings(BaseSettings):
       heading: HeadingSettings
       theme: str
       layout: PostingLayout
       # ...
   ```

6. **Screen-Based Architecture**
   - `MainScreen` for primary interface
   - `HelpScreen` for documentation
   - Screen switching for major mode changes

---

## Key Takeaways for Consoul TUI

### 1. **Library-First Separation**

**Recommendation:** Keep TUI completely separate from core AI/conversation logic

```
consoul/
├── ai/              # Core library (already exists)
├── config/          # Core library (already exists)
├── formatters/      # Core library (already exists)
├── tui/             # NEW: TUI implementation
│   ├── __init__.py
│   ├── app.py       # Main ConsoulApp
│   ├── cli.py       # TUI CLI entry
│   ├── config.py    # TUI-specific config
│   ├── css/
│   ├── widgets/
│   └── utils/
└── __main__.py      # CLI commands (already exists)
```

**Why:** Gira can import `consoul.ai` and `consoul.config` without pulling in TUI dependencies.

---

### 2. **Streaming-Centric Widget Design**

Unlike Gira (project management) or Postings (HTTP requests), Consoul's primary UX is **streaming AI responses**.

**Unique Requirements:**
- Real-time token streaming display
- Conversation history with user/assistant roles
- Markdown rendering with syntax highlighting
- Streaming progress indicators
- Ability to interrupt/cancel streaming

**Proposed Core Widgets:**

```python
# consoul/tui/widgets/
chat_view.py              # Main conversation view
message_bubble.py         # Individual message display
streaming_response.py     # Streaming assistant response
input_area.py             # User input with autocomplete
conversation_list.py      # Sidebar with history
model_selector.py         # Provider/model picker
profile_selector.py       # Profile switcher
settings_screen.py        # Settings modal
```

---

### 3. **Recommended Architecture**

```python
# consoul/tui/app.py
class ConsoulApp(App[None]):
    """Main Consoul TUI application."""

    CSS_PATH = "css/main.tcss"
    TITLE = "Consoul - AI Terminal Assistant"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+n", "new_conversation", "New Chat"),
        Binding("ctrl+p", "switch_profile", "Profile"),
        Binding("ctrl+m", "switch_model", "Model"),
        Binding("ctrl+l", "clear_conversation", "Clear"),
        Binding("ctrl+e", "export_conversation", "Export"),
        Binding("ctrl+s", "search_history", "Search"),
        Binding("/", "focus_input", "Input", show=False),
        Binding("escape", "cancel_stream", "Cancel", show=False),
        Binding("ctrl+comma", "settings", "Settings", show=False),
    ]

    # Reactive state
    current_profile: reactive[str] = reactive("default")
    current_model: reactive[str] = reactive("")
    conversation_id: reactive[Optional[str]] = reactive(None)
    streaming: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield ConversationList()  # Sidebar
            with Vertical(id="main-content"):
                yield ChatView()      # Message history + streaming
                yield InputArea()     # User input
        yield Footer()
```

---

### 4. **Message/Event System**

Learn from Gira's message-based architecture:

```python
# consoul/tui/messages.py
from textual.message import Message

class StreamStart(Message):
    """Emitted when AI response streaming starts."""
    def __init__(self, model: str, session_id: str):
        super().__init__()
        self.model = model
        self.session_id = session_id

class StreamToken(Message):
    """Emitted for each streamed token."""
    def __init__(self, token: str, session_id: str):
        super().__init__()
        self.token = token
        self.session_id = session_id

class StreamComplete(Message):
    """Emitted when streaming completes."""
    def __init__(self, full_response: str, session_id: str):
        super().__init__()
        self.full_response = full_response
        self.session_id = session_id

class StreamError(Message):
    """Emitted on streaming error."""
    def __init__(self, error: Exception):
        super().__init__()
        self.error = error
```

Usage in ChatView:
```python
class ChatView(Widget):
    @on(StreamToken)
    def handle_token(self, message: StreamToken):
        """Append token to current streaming message bubble."""
        self.streaming_bubble.append_token(message.token)

    @on(StreamComplete)
    def handle_complete(self, message: StreamComplete):
        """Finalize the message and save to history."""
        self.finalize_message(message.full_response)
        self.post_message(RefreshHistory())
```

---

### 5. **Streaming Widget Implementation**

**Key Pattern:** Use TextArea or RichLog for streaming content

```python
# consoul/tui/widgets/streaming_response.py
from textual.widgets import Static
from rich.markdown import Markdown
from rich.console import Group

class StreamingResponse(Static):
    """Widget that displays a streaming AI response."""

    def __init__(self, model: str):
        super().__init__()
        self.model = model
        self.buffer = ""
        self.complete = False

    def append_token(self, token: str) -> None:
        """Append a new token to the response."""
        self.buffer += token
        self.update_display()

    def update_display(self) -> None:
        """Re-render the markdown content."""
        if self.complete:
            # Final render with full markdown
            self.update(Markdown(self.buffer))
        else:
            # Streaming render with cursor indicator
            self.update(Markdown(self.buffer + " ▊"))

    def finalize(self) -> None:
        """Mark streaming as complete."""
        self.complete = True
        self.update_display()
```

**Alternative:** Use RichLog (from Postings) for better performance with long outputs

```python
from posting.widgets.rich_log import RichLogIO  # Inspiration

class ChatLog(RichLog):
    """Scrollable log of conversation messages."""

    def add_user_message(self, content: str):
        self.write(f"[bold cyan]You:[/] {content}\n")

    def start_assistant_message(self, model: str):
        self.write(f"[bold green]{model}:[/] ")

    def append_token(self, token: str):
        self.write(token)
```

---

### 6. **Configuration for TUI**

Extend existing config system:

```python
# consoul/config/models.py (already exists)
class TuiConfig(BaseModel):
    """TUI-specific configuration."""

    theme: str = "monokai"
    show_sidebar: bool = True
    sidebar_width: str = "30%"
    enable_mouse: bool = True
    vim_mode: bool = False
    markdown_theme: str = "monokai"

    # Message display
    show_timestamps: bool = True
    show_token_count: bool = True
    max_message_length: Optional[int] = None

    # Performance
    max_visible_messages: int = 100
    lazy_load_history: bool = True

class ConsoulConfig(BaseModel):
    # ... existing fields ...
    tui: TuiConfig = TuiConfig()  # ADD
```

---

### 7. **Theme System**

Learn from both apps:

```python
# consoul/tui/themes/
__init__.py
models.py      # Theme data models
loader.py      # Load from .tcss or JSON
builtin.py     # Built-in themes (monokai, dracula, nord, gruvbox)
```

Textual supports CSS themes natively:
```tcss
/* consoul/tui/css/themes/monokai.tcss */
Screen {
    background: $surface;
}

ChatView {
    background: $panel;
    color: $text;
}

.user-message {
    background: $primary;
    color: $text;
}

.assistant-message {
    background: $secondary;
    color: $text;
}
```

---

### 8. **Error Handling**

Adopt Gira's ErrorHandler pattern:

```python
# consoul/tui/utils/error_handling.py
class ErrorHandler:
    """Centralized error handling for TUI."""

    def __init__(self, app: "ConsoulApp"):
        self.app = app
        self.logger = logging.getLogger("consoul.tui")

    async def handle_api_error(self, error: Exception):
        """Handle API errors gracefully."""
        self.logger.error(f"API error: {error}")
        self.app.push_screen(ErrorModal(
            title="API Error",
            message=str(error),
            suggestions=["Check API key", "Verify network connection"]
        ))

    async def handle_stream_error(self, error: Exception):
        """Handle streaming errors."""
        self.logger.error(f"Stream error: {error}")
        # Show error inline in chat
        self.app.notify("Streaming failed. See logs for details.", severity="error")
```

---

### 9. **Performance Considerations**

**From Gira:**
- Disable automatic GC to prevent UI freezes with many widgets
- Use lazy loading for heavy widgets (modals, complex views)
- Debounce reactive updates

**From Postings:**
- Use `Lazy()` wrapper for tab content
- Minimize DOM updates during streaming

**For Consoul:**
```python
# consoul/tui/app.py
class ConsoulApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Disable GC for smooth streaming
        gc.disable()

        # Schedule periodic manual GC
        self.set_interval(30.0, self._periodic_gc)

    def _periodic_gc(self):
        """Manual GC to prevent pauses during streaming."""
        if not self.streaming:  # Only GC when not actively streaming
            gc.collect(generation=0)  # Quick collection only
```

---

### 10. **Widget Hierarchy**

```
ConsoulApp
├── Header (Textual built-in)
├── Horizontal (Main container)
│   ├── ConversationList (Sidebar)
│   │   ├── ConversationItem (x N)
│   │   └── NewConversationButton
│   └── Vertical (Main content)
│       ├── ChatView
│       │   ├── MessageBubble (user)
│       │   ├── MessageBubble (assistant)
│       │   ├── StreamingResponse (if active)
│       │   └── ... (history)
│       └── InputArea
│           ├── TextArea (for user input)
│           └── SendButton
└── Footer (Textual built-in)

# Modals (overlays)
├── ProfileSelectorModal
├── ModelSelectorModal
├── SettingsScreen
├── SearchModal
├── ExportModal
└── ErrorModal
```

---

## Implementation Roadmap

### Phase 1: Foundation (EPIC-003 tickets)
1. **SOUL-32:** Setup TUI directory structure and base app
2. **SOUL-33:** Create TUI-specific configuration model
3. **SOUL-34:** Implement basic App class with keyboard bindings
4. **SOUL-35:** Create CSS theme system

### Phase 2: Core Widgets (EPIC-003 continued)
5. **SOUL-36:** Build ChatView widget with message display
6. **SOUL-37:** Implement StreamingResponse widget
7. **SOUL-38:** Create InputArea with send functionality
8. **SOUL-39:** Build ConversationList sidebar
9. **SOUL-40:** Implement message bubbles with markdown rendering

### Phase 3: Integration (EPIC-003 continued)
10. **SOUL-41:** Integrate with existing AI providers (stream_response)
11. **SOUL-42:** Connect to ConversationDatabase for history
12. **SOUL-43:** Implement conversation switching
13. **SOUL-44:** Add profile/model selection modals

### Phase 4: Advanced Features (EPIC-004)
14. **SOUL-45:** Add search functionality (integrate FTS5)
15. **SOUL-46:** Implement export/import UI
16. **SOUL-47:** Create settings screen
17. **SOUL-48:** Add keyboard shortcuts help modal
18. **SOUL-49:** Theme switching and customization

### Phase 5: Polish (EPIC-004 continued)
19. **SOUL-50:** Error handling and recovery
20. **SOUL-51:** Performance optimization (GC, lazy loading)
21. **SOUL-52:** Tests for TUI components
22. **SOUL-53:** Documentation and examples

---

## Design Principles for Consoul TUI

1. **Streaming First:** Optimize UX for real-time AI response display
2. **Keyboard-Driven:** Vim-like bindings, minimal mouse dependency
3. **Library-Compatible:** Zero coupling to TUI from core modules
4. **Lightweight:** Fast startup, low memory footprint
5. **Markdown Native:** Rich text rendering for code, lists, tables
6. **Profile-Aware:** Easy switching between AI providers and models
7. **History-Centric:** Quick access to past conversations via search
8. **Interruptible:** Cancel streaming responses gracefully
9. **Themeable:** Support dark/light themes like Gira and Postings
10. **Tested:** TUI smoke tests like Gira (test_tui_smoke.py)

---

## Technical Debt to Avoid

**From Gira Lessons:**
1. **Don't:** Make app.py a 3000-line monolith (Gira's is 120KB)
   - **Do:** Extract views into separate screen classes

2. **Don't:** Tightly couple data loading to UI
   - **Do:** Use service layer (like BlameDataService)

3. **Don't:** Ignore GC impact on UI responsiveness
   - **Do:** Disable auto GC and manually schedule collections

4. **Don't:** Hardcode terminal sequences
   - **Do:** Use Textual's built-in terminal management

**From Postings Lessons:**
1. **Don't:** Load all tabs eagerly
   - **Do:** Use `Lazy()` for expensive tab content

2. **Don't:** Reinvent command palette
   - **Do:** Extend Textual's CommandProvider

---

## Questions to Resolve

1. **Markdown Rendering:** Use Textual's built-in `Markdown` widget or Rich's `Markdown`?
   - **Recommendation:** Textual's widget (better integration, scrolling)

2. **Code Highlighting:** How to highlight code blocks in streamed markdown?
   - **Recommendation:** Use Pygments with TextArea or Rich syntax highlighting

3. **Conversation Storage:** Keep SQLite ConversationDatabase or add in-memory cache?
   - **Recommendation:** Keep SQLite, add LRU cache for active conversations

4. **Model Selection:** Modal or sidebar panel?
   - **Recommendation:** Modal (like Postings' collection selector), less screen clutter

5. **Input Multi-Line:** Support multi-line input (shift+enter) like Slack?
   - **Recommendation:** Yes, use TextArea instead of Input

6. **Vim Mode:** Implement vim-like navigation?
   - **Recommendation:** Phase 4 enhancement, not MVP

---

## Conclusion

Consoul's TUI should learn from Gira's robust architecture and Postings' elegant simplicity while focusing on its unique streaming chat UX. The key differentiator is real-time AI response rendering with markdown support.

**Next Steps:**
1. Create EPIC-003: Consoul TUI Foundation
2. Break down into ~20 tickets across 5 phases
3. Start with Phase 1 (foundation and base app)
4. Iterate based on user feedback

**Success Metrics:**
- ✅ Can be used as standalone chat interface
- ✅ Can be imported as library in Gira (zero coupling)
- ✅ Streams responses smoothly (no UI freezes)
- ✅ Markdown renders correctly (code, tables, lists)
- ✅ Keyboard navigation feels natural
- ✅ Startup time < 500ms
- ✅ Test coverage > 70%
