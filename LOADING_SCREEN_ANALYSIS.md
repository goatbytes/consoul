# Loading Screen Integration Analysis

## Current State

### ✅ What Exists
- `src/consoul/tui/loading.py` - Complete LoadingScreen implementation with:
  - `BinaryCanvas` - Animated binary/waveform background
  - `LoadingScreen` - Widget with logo, message, and progress bar
  - `ConsoulLoadingScreen` - Screen wrapper for the TUI
  - Consoul brand colors (blue/purple/cyan)
  - Progress tracking (0-100%)
  - Message updates
  - Fade-out animation

- `src/consoul/tui/animations.py` - Animation system (assumed to exist based on imports)

### ❌ What's Missing
- LoadingScreen is **NOT currently used** in the app
- No integration in `ConsoulApp.__init__` or `on_mount`
- Initialization happens synchronously in `__init__` (lines 133-358)

---

## Current Initialization Flow

### `__init__` (Lines 133-358) - Blocking, No Feedback

```python
def __init__(self, config, consoul_config, test_mode):
    super().__init__()

    # 1. Config setup (fast)
    self.config = config or TuiConfig()

    # 2. Load Consoul config from file (potentially slow)
    if consoul_config is None:
        consoul_config = load_config()  # ⚠️ File I/O

    # 3. Initialize AI model (SLOW - network request)
    model_config = consoul_config.get_current_model_config()
    self.chat_model = get_chat_model(model_config, config=consoul_config)  # ⚠️ API call

    # 4. Create conversation history (moderate)
    self.conversation = ConversationHistory(...)

    # 5. Auto-resume conversation if enabled (potentially slow)
    if auto_resume:
        db = ConversationDatabase(...)
        latest = db.get_latest_conversation(...)  # ⚠️ Database query
        self.conversation.load_from_messages(...)

    # 6. Initialize tool registry (moderate)
    from consoul.ai.tools import ToolRegistry
    self.tool_registry = ToolRegistry(...)
    self.tool_registry.register(...)  # Multiple tool registrations

    # 7. Bind tools to model (API-dependent)
    self.chat_model = self.tool_registry.bind_to_model(self.chat_model)  # ⚠️ Varies by provider
```

### `on_mount` (Lines 561-626) - Post-Mount Setup

```python
def on_mount(self):
    # Fallback conversation creation
    if not self.conversation:
        self.conversation = ConversationHistory(...)  # ⚠️ Only if __init__ failed

    # Add system prompt
    self._add_initial_system_prompt()

    # Theme registration
    self.register_theme(CONSOUL_DARK)
    self.register_theme(CONSOUL_LIGHT)
    self.theme = self.config.theme

    # GC setup
    # Search polling
    # Top bar update
```

---

## Performance Bottlenecks (What Should Show Progress)

### 🔴 Critical (Blocking, User-Facing Delays)

1. **AI Model Initialization** (`get_chat_model`) - Lines 196
   - **What**: API connection/validation to OpenAI/Anthropic/Google
   - **Time**: 0.5-3 seconds (network dependent)
   - **Progress**: "Connecting to AI provider..."
   - **Percentage**: 30-40%

2. **Tool Registry Setup** - Lines 268-356
   - **What**: Registering 10+ tools (bash, file editing, code search, etc.)
   - **Time**: 0.2-1 second (imports + registry setup)
   - **Progress**: "Loading tools..."
   - **Percentage**: 50-60%

3. **Model Tool Binding** - Line 358
   - **What**: Binding tools to LangChain model
   - **Time**: 0.1-0.5 seconds (varies by provider)
   - **Progress**: "Binding tools to model..."
   - **Percentage**: 70-80%

### 🟡 Moderate (Visible but Quick)

4. **Config Loading** - Lines 169-176
   - **What**: Read/parse YAML config file
   - **Time**: 0.05-0.2 seconds
   - **Progress**: "Loading configuration..."
   - **Percentage**: 10-20%

5. **Conversation Auto-Resume** - Lines 222-257
   - **What**: Database query + message loading (optional, only if enabled)
   - **Time**: 0.1-0.5 seconds (depends on conversation size)
   - **Progress**: "Restoring conversation..."
   - **Percentage**: 85-90%

### 🟢 Fast (No Progress Needed)

- Theme registration (on_mount)
- GC setup
- UI composition
- State initialization

---

## Recommended Refactoring

### Option A: Async Initialization (Preferred)

**Show loading screen immediately, initialize in background**

```python
class ConsoulApp(App):
    def on_mount(self) -> None:
        """Show loading screen and initialize asynchronously."""
        # Push loading screen immediately
        self.push_screen(ConsoulLoadingScreen(show_progress=True))

        # Run initialization in background
        self.call_later(self._async_initialize)

    async def _async_initialize(self) -> None:
        """Initialize app components with progress updates."""
        loading_screen = self.screen

        # Step 1: Load config (10%)
        loading_screen.update_progress("Loading configuration...", 10)
        config = await self.run_in_thread(load_config)

        # Step 2: Initialize AI model (40%)
        loading_screen.update_progress("Connecting to AI provider...", 40)
        chat_model = await self.run_in_thread(get_chat_model, ...)

        # Step 3: Load tools (60%)
        loading_screen.update_progress("Loading tools...", 60)
        tool_registry = await self.run_in_thread(self._init_tool_registry)

        # Step 4: Bind tools (80%)
        loading_screen.update_progress("Binding tools to model...", 80)
        chat_model = await self.run_in_thread(tool_registry.bind_to_model, chat_model)

        # Step 5: Auto-resume (90%)
        if auto_resume:
            loading_screen.update_progress("Restoring conversation...", 90)
            await self.run_in_thread(self._auto_resume)

        # Step 6: Complete (100%)
        loading_screen.update_progress("Ready!", 100)
        await asyncio.sleep(0.5)

        # Fade out and show main screen
        await loading_screen.fade_out(duration=0.5)
        self.pop_screen()
```

**Pros:**
- ✅ Non-blocking UI
- ✅ Real progress feedback
- ✅ Professional UX
- ✅ Smooth transitions

**Cons:**
- ❌ Requires refactoring `__init__` to move logic out
- ❌ Thread safety considerations for model/registry
- ❌ More complex error handling

### Option B: Pre-Mount Initialization (Simpler)

**Initialize before first screen is shown**

```python
class ConsoulApp(App):
    SCREENS = {
        "loading": ConsoulLoadingScreen(show_progress=True)
    }

    def on_mount(self) -> None:
        """Show loading and initialize."""
        # Switch to loading screen
        self.push_screen("loading")
        self.set_timer(0.1, self._initialize_sync)

    def _initialize_sync(self) -> None:
        """Synchronous initialization with progress updates."""
        loading = self.screen

        # Manually update progress at each step
        loading.update_progress("Loading configuration...", 10)
        config = load_config()  # Still blocking

        loading.update_progress("Connecting to AI...", 40)
        chat_model = get_chat_model(...)  # Still blocking

        # ... etc

        loading.update_progress("Ready!", 100)
        self.set_timer(0.5, lambda: self.pop_screen())
```

**Pros:**
- ✅ Simpler implementation
- ✅ Minimal refactoring
- ✅ Shows progress feedback

**Cons:**
- ❌ Still blocks event loop (UI frozen during init)
- ❌ Can't cancel/interact during loading
- ❌ Progress updates may be janky

---

## Required Refactoring Tasks

### 1. Extract Initialization Logic from `__init__`

**Current:** All in `__init__` (lines 133-358)

**Target:** Move to separate methods

```python
def _load_config(self) -> ConsoulConfig:
    """Load Consoul configuration."""
    ...

def _initialize_ai_model(self, config: ConsoulConfig) -> BaseChatModel:
    """Initialize AI chat model."""
    ...

def _initialize_conversation(self, config: ConsoulConfig, model: BaseChatModel) -> ConversationHistory:
    """Create conversation history."""
    ...

def _initialize_tool_registry(self, config: ConsoulConfig) -> ToolRegistry:
    """Set up tool registry."""
    ...

def _auto_resume_conversation(self, conversation: ConversationHistory) -> None:
    """Resume previous conversation if configured."""
    ...
```

### 2. Add Progress Tracking

**Create initialization steps enum:**

```python
from enum import Enum

class InitStep(Enum):
    CONFIG = ("Loading configuration...", 10)
    AI_MODEL = ("Connecting to AI provider...", 40)
    TOOLS = ("Loading tools...", 60)
    BINDING = ("Binding tools to model...", 80)
    RESUME = ("Restoring conversation...", 90)
    COMPLETE = ("Ready!", 100)

    def __init__(self, message: str, progress: int):
        self.message = message
        self.progress = progress
```

### 3. Handle Initialization Errors

**Add error screen for failed initialization:**

```python
class InitializationError(Screen):
    """Screen shown when initialization fails."""

    def __init__(self, error: Exception):
        super().__init__()
        self.error = error

    def compose(self) -> ComposeResult:
        yield Static(f"Failed to initialize Consoul:\n\n{self.error}")
        yield Button("Retry", id="retry")
        yield Button("Exit", id="exit")
```

### 4. Update `compose()` to Not Require Initialized State

**Current issue:** `compose()` (line 646) assumes everything is initialized

**Solution:** Defer widget creation until after init completes

```python
def compose(self) -> ComposeResult:
    """Compose UI - only show after initialization."""
    # This will be called AFTER loading screen is popped
    # So we can safely assume model/conversation exist
    ...
```

---

## Integration Steps (Recommended Order)

### Phase 1: Foundation (No Visual Changes Yet)
1. ✅ LoadingScreen already exists
2. Extract `__init__` logic to methods
3. Add `InitStep` enum
4. Create `_async_initialize()` method

### Phase 2: Basic Integration
1. Modify `on_mount()` to push LoadingScreen
2. Move initialization to `_async_initialize()`
3. Add progress updates
4. Pop loading screen when complete

### Phase 3: Error Handling
1. Add try/catch in each init step
2. Create `InitializationError` screen
3. Add retry mechanism

### Phase 4: Polish
1. Tune progress percentages
2. Add fade-out animation
3. Test with slow connections
4. Add cancellation support (Ctrl+C during load)

---

## Testing Checklist

- [ ] Fast init (<1s total) - progress should still be visible
- [ ] Slow init (>5s) - progress updates smoothly
- [ ] Network failure - shows error screen
- [ ] Invalid config - shows error screen
- [ ] Ctrl+C during load - cancels gracefully
- [ ] Auto-resume with large conversation - doesn't freeze
- [ ] Theme switching after load - works correctly
- [ ] Multiple rapid starts/stops - no resource leaks

---

## Files to Modify

1. `src/consoul/tui/app.py`
   - Refactor `__init__` method
   - Add `_async_initialize()`
   - Modify `on_mount()`
   - Add error handling

2. `src/consoul/tui/loading.py`
   - Already complete, no changes needed
   - Maybe add error state support

3. `src/consoul/tui/cli.py`
   - Update CLI entry point if needed
   - Ensure signals (Ctrl+C) work during load

4. New: `src/consoul/tui/init.py` (optional)
   - Extract initialization logic
   - Keep app.py focused on UI

---

## Estimated Complexity

- **Effort**: 4-6 hours
- **Risk**: Medium (thread safety, error handling)
- **Testing**: 2-3 hours
- **Total**: ~8 hours

---

## Alternative: Quick Win (30 min)

Just show loading screen briefly without real progress:

```python
def on_mount(self) -> None:
    # Show loading screen
    self.push_screen(ConsoulLoadingScreen(show_progress=False))

    # Hide after 1 second (fake loading)
    self.set_timer(1.0, lambda: self.pop_screen())

    # Existing initialization continues in background
    # (still blocks, but user sees something)
```

**Pros:** Very quick to implement, looks professional
**Cons:** Doesn't solve actual blocking issue
