# Tool Control UI/UX Proposal for Consoul TUI

## Executive Summary

Currently, the Consoul TUI registers all 13 tools automatically when `tools.enabled=True` in the config. Users have no runtime control over which tools are available. This proposal adds multiple layers of tool control to give TUI users fine-grained power over their AI assistant's capabilities.

## Important Distinction: Registration vs. Execution

### Current Behavior
**Registration (app.py:283-479):**
- All 13 tools are **hardcoded** and registered
- Registered tools are bound to the model (visible in AI context)

**Execution (registry.py:223-256, policy.py:323-345):**
- `allowed_tools` whitelist **controls execution** (blocking non-whitelisted tools)
- `PolicyResolver` uses whitelist for approval flow decisions

**The Gap:**
- Non-whitelisted tools are still **registered** (visible to AI)
- They're only **blocked at execution time** (after AI tries to use them)
- Wastes context (AI sees tools it can't use)
- Inconsistent with SDK (which only registers specified tools)

---

## Current State Analysis

### Tool Registration (app.py:283-479)
**Current Behavior:**
- All tools are **hardcoded** and registered on startup
- User has **no control** over which tools are available
- Only global on/off via `config.tools.enabled`

**Tools Currently Registered:**
1. **bash_execute** (variable risk*) - Execute shell commands
2. **read_file** (SAFE) - Read file contents
3. **grep_search** (SAFE) - Search file contents
4. **code_search** (SAFE) - AST-based code search
5. **find_references** (SAFE) - Find symbol references
6. **web_search** (SAFE) - Search the web
7. **wikipedia_search** (SAFE) - Wikipedia lookup
8. **read_url** (SAFE) - Fetch URL content
9. **create_file** (CAUTION) - Create new files
10. **edit_file_lines** (CAUTION) - Edit file line ranges
11. **edit_file_search_replace** (CAUTION) - Search/replace in files
12. **append_to_file** (CAUTION) - Append to files
13. **delete_file** (DANGEROUS) - Delete files

\* bash_execute risk is determined dynamically by CommandAnalyzer at execution time (SAFE/CAUTION/DANGEROUS/BLOCKED), not at registration. The four defined RiskLevel enum values are: SAFE, CAUTION, DANGEROUS, BLOCKED (src/consoul/ai/tools/base.py:30-33).

### Configuration (ToolConfig)
**Existing Config Options:**
- `enabled: bool` - Master switch (all or nothing)
- `allowed_tools: list[str]` - Whitelist for execution control
- `permission_policy` - PARANOID/BALANCED/TRUSTING/UNRESTRICTED
- Individual tool configs (bash.timeout, grep_search.max_results, etc.)

**Current Whitelist Behavior:**
- `allowed_tools` **IS used** at execution time via `ToolRegistry.is_allowed()` (src/consoul/ai/tools/registry.py:223-256) and `PolicyResolver._is_whitelisted()` (src/consoul/ai/tools/permissions/policy.py:323-345)
- Prevents execution of non-whitelisted tools
- Controls approval flow (whitelisted tools may skip approval based on policy)

**Gap:** While `allowed_tools` controls execution, the TUI still **registers all 13 tools** regardless of the whitelist. This means:
- Non-whitelisted tools are still bound to the model
- AI can attempt to call them (they'll be blocked at execution)
- Unnecessarily increases context size
- No way to prevent registration of unwanted tools

## Problems to Solve

### 1. All-or-Nothing Control
**Problem:** Users must enable all 13 tools or none.
**Impact:**
- Can't use safe read-only tools without also enabling file deletion
- No way to restrict AI to specific capabilities
- Security concern: unnecessary attack surface

### 2. No Runtime Modification
**Problem:** Tool list is fixed at startup.
**Impact:**
- Must restart TUI to change tools
- No session-based experimentation
- Can't adapt to changing trust levels mid-session

### 3. No Visibility
**Problem:** Users don't know which tools are available.
**Impact:**
- Hidden capabilities
- No way to verify security posture
- Difficult to debug tool-related issues

### 4. Registration vs. Execution Gap
**Problem:** `allowed_tools` controls execution but not registration.
**Impact:**
- All 13 tools are always registered and bound to model
- Non-whitelisted tools visible to AI (blocked at execution, not registration)
- Unnecessary context usage (tools listed that can't be used)
- Inconsistent with SDK (which only registers specified tools)

## Proposed Solution: Multi-Layer Tool Control

### Layer 1: CLI Flags (Immediate Control)
Add tool specification directly to the `consoul tui` command:

```bash
# Enable all tools (current default)
consoul tui

# Only safe read-only tools
consoul tui --tools safe

# Specific tools by name
consoul tui --tools bash,grep,code_search

# Category-based (like SDK)
consoul tui --tools search,web

# No tools (chat-only mode)
consoul tui --tools none

# Mix categories and specific tools
consoul tui --tools "search,bash,create_file"
```

**Implementation:**
```python
@click.option(
    "--tools",
    type=str,
    help="Tool specification: 'all', 'safe', 'caution', 'none', "
         "category names (search/file-edit/web/execute), "
         "or comma-separated tool names (bash,grep,code_search)",
)
def tui(ctx, theme, debug, log_file, test_mode, tools):
    # Parse tools specification and pass to ConsoulApp
    ...
```

**Benefits:**
- Immediate control without config changes
- Experiment with different tool sets per session
- CLI overrides config (standard behavior)
- Aligns with SDK patterns

---

### Layer 2: Config File (Persistent Preferences)

**Respect `allowed_tools` in config:**

```toml
[tools]
enabled = true

# Specify which tools to register
# Empty list = all tools (backward compatible)
# Non-empty list = only these tools
allowed_tools = [
    "bash",
    "grep_search",
    "code_search",
    "read_file",
    "create_file",
    "edit_file_lines",
]
```

**Or use risk-level filtering (NEW FIELD):**
```toml
[tools]
enabled = true
# NEW field to be added: risk_filter
risk_filter = "safe"  # Only SAFE tools
# OR
risk_filter = "caution"  # SAFE + CAUTION (excludes DANGEROUS)
```

**Implementation in app.py (PROPOSED):**
```python
# Replace hardcoded registration with dynamic lookup
if consoul_config.tools and consoul_config.tools.enabled:
    from consoul.ai.tools.catalog import (
        get_tools_by_risk_level,
        get_tool_by_name,
        TOOL_CATALOG,  # Import the catalog dict
    )

    # Determine which tools to register
    if consoul_config.tools.allowed_tools:
        # User specified explicit whitelist - look up each tool
        tools_to_register = []
        for name in consoul_config.tools.allowed_tools:
            tool_tuple = get_tool_by_name(name)
            if tool_tuple:
                tools_to_register.append(tool_tuple)
    elif hasattr(consoul_config.tools, 'risk_filter') and consoul_config.tools.risk_filter:
        # User specified risk level filter (NEW FEATURE)
        tools_to_register = list(get_tools_by_risk_level(consoul_config.tools.risk_filter))
    else:
        # Default: all tools (backward compatible)
        # NOTE: get_all_tools() does not exist - iterate catalog
        tools_to_register = list(TOOL_CATALOG.values())

    # Register filtered tools
    for tool, risk_level, categories in tools_to_register:
        self.tool_registry.register(tool, risk_level=risk_level, enabled=True)
```

**NEW APIs Required:**
- Add `risk_filter: str | None` field to `ToolConfig` (src/consoul/config/models.py)
- No new catalog functions needed - `get_tools_by_risk_level()` and `get_tool_by_name()` already exist
- Can iterate `TOOL_CATALOG.values()` for "all tools" case

**Benefits:**
- Persistent user preferences
- Fixes registration vs. execution gap
- Reduces context usage (only register needed tools)
- Backward compatible (empty list = all tools)
- Aligns with SDK behavior

---

### Layer 3: Interactive Tool Manager (TUI Screen)

Add a **Tools** screen accessible via keybinding (e.g., `Ctrl+T`):

```
┌─ Tool Manager ────────────────────────────────────────────────────────┐
│                                                                        │
│  [●] bash_execute        (CAUTION)  Execute shell commands            │
│  [●] grep_search         (SAFE)     Search file contents              │
│  [●] code_search         (SAFE)     AST-based code search             │
│  [●] find_references     (SAFE)     Find symbol references            │
│  [●] web_search          (SAFE)     Search the web                    │
│  [○] wikipedia_search    (SAFE)     Wikipedia lookup                  │
│  [●] read_url            (SAFE)     Fetch URL content                 │
│  [●] read_file           (SAFE)     Read file contents                │
│  [●] create_file         (CAUTION)  Create new files                  │
│  [●] edit_file_lines     (CAUTION)  Edit file line ranges             │
│  [●] edit_file_search_replace (CAUTION) Search/replace in files       │
│  [○] append_to_file      (CAUTION)  Append to files                   │
│  [○] delete_file         (DANGEROUS) Delete files                     │
│                                                                        │
│  10/13 tools enabled                                                  │
│                                                                        │
│  [Space] Toggle  [A]ll  [N]one  [S]afe Only  [Q]uit  [Enter] Apply   │
└────────────────────────────────────────────────────────────────────────┘
```

**Features:**
- ✅ Visual list of all available tools
- ✅ Toggle individual tools on/off (Space)
- ✅ Risk level color coding (SAFE=green, CAUTION=yellow, DANGEROUS=red)
- ✅ Quick filters: All, None, Safe Only
- ✅ Category-based filtering (Search, File Edit, Web, Execute)
- ✅ Real-time updates (rebind to model on apply)
- ✅ Session-only changes (or option to persist to config)

**Alternative: Compact Top Bar Indicator**

Add tool status to the top bar:

```
┌─ Consoul ──────────────────────────────────────────────────────────────┐
│ claude-3-5-sonnet-20241022  │  Tools: 10/13 ▼  │  Ctrl+T: Manage      │
└────────────────────────────────────────────────────────────────────────┘
```

Clicking "Tools: 10/13 ▼" opens the Tool Manager screen.

**Implementation:**
```python
class ToolManagerScreen(Screen):
    """Tool management screen for enabling/disabling tools."""

    def __init__(self, tool_registry: ToolRegistry):
        super().__init__()
        self.tool_registry = tool_registry
        self.tool_states = {
            meta.name: meta.enabled
            for meta in tool_registry.list_tools()
        }

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="tool-list")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Enabled", "Tool Name", "Risk", "Description")

        for meta in self.tool_registry.list_tools():
            enabled = "●" if meta.enabled else "○"
            risk_color = self._get_risk_color(meta.risk_level)
            table.add_row(
                enabled,
                meta.name,
                Text(meta.risk_level.value.upper(), style=risk_color),
                meta.tool.description[:50],
            )

    def action_toggle_tool(self) -> None:
        # Toggle selected tool
        ...

    def action_apply_changes(self) -> None:
        # Update registry and rebind to model
        ...
```

**Benefits:**
- Full visibility into tool availability
- Runtime enable/disable without restart
- Visual security posture awareness
- No config file editing required

---

### Layer 4: Session Presets (Power User Feature)

Add predefined tool sets for common scenarios:

```bash
# Built-in presets
consoul tui --preset readonly
consoul tui --preset development
consoul tui --preset safe-research
consoul tui --preset power-user

# Custom user presets (defined in config)
consoul tui --preset my-workflow
```

**Config definition:**
```toml
[tool_presets.readonly]
description = "Safe read-only tools for exploration"
tools = ["grep_search", "code_search", "find_references", "read_file", "read_url", "web_search"]

[tool_presets.development]
description = "Full development toolset (excludes delete)"
tools = ["bash", "grep_search", "code_search", "read_file", "create_file", "edit_file_lines", "edit_file_search_replace"]

[tool_presets.safe_research]
description = "Web research + code reading"
tools = ["web_search", "wikipedia_search", "read_url", "grep_search", "code_search", "read_file"]

[tool_presets.power_user]
description = "All tools enabled"
tools = []  # Empty = all tools
```

**Implementation:**
```python
@click.option(
    "--preset",
    type=str,
    help="Use a predefined tool preset (readonly/development/safe-research/power-user or custom)",
)
def tui(ctx, preset, ...):
    if preset:
        # Load preset from config or built-in
        tools_spec = load_tool_preset(preset)
    ...
```

**Benefits:**
- Quick workflow switching
- Shareable configurations
- Onboarding for new users ("start with readonly preset")
- Reduces cognitive load

---

## Recommended Implementation Priority

### Phase 1: Foundation (Critical)
**Goal:** Fix registration gap and add basic control

1. ✅ **Use `allowed_tools` for registration (not just execution)**
   - Modify `app.py` tool registration to respect `allowed_tools` whitelist
   - Currently: all tools registered, whitelist only blocks execution
   - After: only whitelisted tools are registered and bound to model
   - Backward compatible (empty list = all tools)
   - **Effort:** 2-3 hours
   - **Impact:** High (aligns registration with execution control)

2. ✅ **Add CLI `--tools` flag**
   - Support: `all`, `safe`, `caution`, `none`, tool names, categories
   - Override config when specified
   - **Effort:** 3-4 hours
   - **Impact:** High (immediate user control)

3. ✅ **Add risk level filtering to config (NEW)**
   - New field: `risk_filter: str | None` in ToolConfig
   - Values: `"safe"` | `"caution"` | `"dangerous"` | None
   - Uses existing `get_tools_by_risk_level()` function
   - **Effort:** 1-2 hours
   - **Impact:** Medium (common use case)

### Phase 2: Visibility (Important)
**Goal:** Show users what tools are available

4. ✅ **Add tool status to top bar**
   - Show "Tools: 10/13" indicator
   - Click to view detailed list
   - **Effort:** 2-3 hours
   - **Impact:** Medium (awareness)

5. ✅ **Create Tool Manager screen**
   - List all tools with enable/disable toggles
   - Risk level color coding
   - Quick filters (All/None/Safe)
   - **Effort:** 6-8 hours
   - **Impact:** High (full visibility + control)

### Phase 3: Power Features (Nice-to-Have)
**Goal:** Advanced workflows for power users

6. ✅ **Session presets**
   - Built-in presets (readonly/development/etc.)
   - Custom user presets in config
   - **Effort:** 4-6 hours
   - **Impact:** Medium (convenience)

7. ✅ **Persist changes from Tool Manager**
   - Option to save current tool state to config
   - "Save as preset" functionality
   - **Effort:** 3-4 hours
   - **Impact:** Low (nice QoL improvement)

---

## Design Decisions & Rationale

### 1. Why Not Auto-Detect Based on Context?
**Considered:** Automatically enable/disable tools based on conversation context.

**Rejected:**
- Too much magic (unexpected behavior)
- Security implications (tools enabling without user awareness)
- Complexity in context detection
- User preference for explicit control

### 2. Why CLI Flag + Config + UI?
**Rationale:**
- **CLI:** Quick one-off sessions, experimentation
- **Config:** Persistent preferences, team sharing
- **UI:** Discovery, runtime adjustments, visual feedback

Each layer serves different use cases. Users can choose their preferred method.

### 3. Why Not Tool Categories in UI?
**Included in Phase 2:**
- Quick filters will include "Search", "File Edit", "Web", "Execute"
- Aligns with SDK categories
- Reduces visual clutter for common selections

### 4. Should Changes Be Persistent by Default?
**Decision:** Session-only by default, with "Save" option.

**Rationale:**
- Safer (no accidental permanent changes)
- Allows experimentation
- Power users can explicitly save
- Aligns with "least surprise" principle

---

## UX Guidelines

### Color Coding (Risk Levels)
The four RiskLevel enum values (src/consoul/ai/tools/base.py:30-33):
- **SAFE** (Green): Read-only, no system changes
- **CAUTION** (Yellow): File operations, needs oversight
- **DANGEROUS** (Red): Destructive operations (delete)
- **BLOCKED** (Gray/Strikethrough): Explicitly prohibited (not used in TUI currently)

### Keyboard Shortcuts
- `Ctrl+T`: Open Tool Manager
- `Space`: Toggle selected tool
- `A`: Enable All
- `N`: Disable All
- `S`: Safe Only
- `Enter`: Apply changes
- `Esc`/`Q`: Cancel/Close

### Visual Feedback
- Tool count badge: "Tools: 10/13"
- Enabled tools: ● (filled circle)
- Disabled tools: ○ (empty circle)
- Active filter: highlighted border

### Error Handling
- **No tools enabled:** Show warning "No tools enabled. AI cannot perform actions."
- **Invalid tool name in CLI:** List available tools and suggest correction
- **Invalid preset:** Show available presets

---

## Migration Strategy

### Backward Compatibility
**Current behavior:** All tools enabled when `tools.enabled=True`

**After changes:**
- Empty `allowed_tools` list → All tools (backward compatible)
- CLI `--tools` not specified → Use config
- Config `risk_filter` not set → Use `allowed_tools` or default to all

**No breaking changes for existing users.**

### Documentation Updates
1. Update CLI help text
2. Add "Tool Control" section to user guide
3. Document tool categories
4. Add examples for common workflows
5. Security best practices guide

### Testing Strategy
1. Unit tests for tool filtering logic
2. Integration tests for CLI flag parsing
3. TUI tests for Tool Manager interactions
4. Regression tests (backward compatibility)
5. Security tests (whitelist enforcement)

---

## Success Metrics

### User Control
- ✅ Users can specify tools via CLI in <10 keystrokes
- ✅ Tool Manager accessible in <2 key presses
- ✅ Tool changes apply in <5 seconds

### Visibility
- ✅ Users can view all available tools
- ✅ Risk levels clearly indicated
- ✅ Tool count always visible

### Flexibility
- ✅ Support 4+ common workflows via presets
- ✅ Per-session tool changes without config edit
- ✅ Both coarse (risk level) and fine (individual) control

---

## Future Enhancements (Post-MVP)

### Tool Discovery Support
When SOUL-150 custom tool discovery is implemented:
- Show both built-in and discovered tools
- Visual distinction (icon/color)
- Filter by source (built-in vs. custom)

### Usage Analytics
- Track which tools are used most
- Suggest tool presets based on usage
- "You mostly use search tools - try the 'readonly' preset?"

### Per-Conversation Tool Sets
- Different tool availability per conversation
- "Research" conversation vs. "Development" conversation
- Saved in conversation metadata

### Tool Dependency Management
- Auto-enable dependencies ("bash requires read_file")
- Warn about missing complementary tools
- Suggest tool combinations for workflows

---

## Conclusion

This proposal provides **three layers of tool control** (CLI, Config, UI) to give Consoul TUI users the power to:

1. ✅ **Choose** which tools are available (whitelist, risk level, categories)
2. ✅ **See** what tools are currently active (visibility)
3. ✅ **Change** tool availability at runtime (flexibility)
4. ✅ **Save** preferences for future sessions (persistence)

The implementation is **incremental** (Phase 1→2→3) and **backward compatible** (no breaking changes).

**Recommended Next Step:** Implement Phase 1 (Foundation) to fix the config mismatch and add basic CLI control. This provides immediate value with minimal effort (6-9 hours total).
