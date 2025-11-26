# TUI Documentation Corrections Needed

This document outlines all inaccuracies found in the TUI documentation and the correct information.

## Critical Issues

### 1. Keyboard Shortcuts - MANY INCORRECT

#### Global Shortcuts - CORRECTIONS NEEDED:

| Documented | Actual | Status |
|------------|--------|--------|
| `^s` → Settings | `^comma` (Ctrl+,) → Settings | ❌ WRONG |
| `^p` → Palette/Themes | `^p` → Profile Selector | ❌ WRONG |
| `^f` → Attach Files | NOT FOUND | ❌ WRONG |
| `^n` → New Chat | `^n` → New Chat | ✅ CORRECT |
| `^l` → Clear | `^l` → Clear | ✅ CORRECT |
| `^e` → Export | `^e` → Export | ✅ CORRECT |
| `^b` → Sidebar | `^b` → Sidebar | ✅ CORRECT |
| `^t` → Tools | `^t` → Tools | ✅ CORRECT |
| `shift+^p` → Permissions | `shift+^p` → Permissions | ✅ CORRECT |
| `q` → Quit | `q` → Quit | ✅ CORRECT |

#### MISSING from documentation:

| Shortcut | Action | Description |
|----------|--------|-------------|
| `^comma` | Settings | Open settings modal |
| `^m` | Switch Model | Open model picker |
| `^o` | Ollama Library | Browse Ollama library |
| `^i` | Import | Import conversation |
| `^s` | Search History | Search conversation history |
| `/` | Focus Input | Focus input area |
| `^shift+s` | System Prompt | View system prompt |
| `f1` | Help | Show help modal |
| `escape` | Cancel Stream | Cancel streaming response |
| `^c` | Quit | Alternative quit |

### 2. Themes - MAJOR INACCURACY

#### Documented (WRONG):
- Consoul Dark ✅
- Consoul Light ✅
- Nord ❌ (Textual built-in, not Consoul custom)
- Gruvbox ❌ (Textual built-in, not Consoul custom)
- Tokyo Night ❌ (Textual built-in, not Consoul custom)
- Flexoki ❌ (Textual built-in, not Consoul custom)

#### Actual Reality:
- **Only 2 Consoul custom themes registered**: `CONSOUL_DARK` and `CONSOUL_LIGHT`
- **Settings dropdown shows Textual built-in themes**:
  - consoul-dark
  - consoul-light
  - monokai
  - dracula
  - nord
  - gruvbox
  - tokyo-night
  - catppuccin-mocha
  - catppuccin-latte
  - solarized-light
  - flexoki
  - textual-dark
  - textual-light
  - textual-ansi

**Documentation Strategy**:
- Focus on the 2 Consoul-branded themes (dark/light)
- Mention that Textual's built-in themes are also available
- Remove all the detailed theme descriptions for non-Consoul themes
- Remove theme screenshots for non-Consoul themes

### 3. Settings Modal - PARTIALLY WRONG

#### Tabs (CORRECT):
- ✅ Appearance
- ✅ Performance (exists in code, needs verification of what's shown)
- ✅ Behavior (exists in code, needs verification of what's shown)
- ✅ Advanced (exists in code, needs verification of what's shown)

#### Appearance Tab - VERIFIED Options:
- ✅ Theme (dropdown with 14 themes)
- ✅ Show Sidebar (switch)
- ✅ Show Timestamps (switch)
- ✅ Show Token Count (switch)

**NEED TO VERIFY**: What options are in Performance, Behavior, and Advanced tabs

### 4. Configuration Options - SOME INACCURATE

#### Verified Real Config Options (from TuiConfig):

**Appearance**:
- `theme` ✅
- `show_sidebar` ✅
- `sidebar_width` ✅ (NOT in docs)
- `show_timestamps` ✅
- `show_token_count` ✅
- ~~`input_syntax_highlighting`~~ ❌ Listed as `input_syntax_highlighting` (CORRECT)

**Performance**:
- `gc_mode` ✅ (NOT in docs - should add)
- `gc_interval_seconds` ✅ (NOT in docs)
- `gc_generation` ✅ (NOT in docs)
- `stream_buffer_size` ✅ (NOT in docs)
- `stream_debounce_ms` ✅ (NOT in docs)
- `stream_renderer` ✅ (NOT in docs)
- `initial_conversation_load` ✅ (NOT in docs)
- `enable_virtualization` ✅ (NOT in docs)
- ~~`stream_tokens`~~ ❌ (NOT REAL - should remove)
- ~~`async_rendering`~~ ❌ (NOT REAL - should remove)
- ~~`virtual_scrolling`~~ ❌ (NOT REAL - should remove)
- ~~`cache_conversations`~~ ❌ (NOT REAL - should remove)
- ~~`max_cached_conversations`~~ ❌ (NOT REAL - should remove)

**Behavior**:
- `enable_multiline_input` ✅ (NOT in docs)
- `input_syntax_highlighting` ✅
- `enable_mouse` ✅ (NOT in docs)
- `vim_mode` ✅ (NOT in docs)
- `auto_generate_titles` ✅
- `auto_title_provider` ✅ (NOT in docs)
- `auto_title_model` ✅ (NOT in docs)
- `auto_title_api_key` ✅ (NOT in docs)
- `auto_title_prompt` ✅ (NOT in docs)
- `auto_title_max_tokens` ✅ (NOT in docs)
- `auto_title_temperature` ✅ (NOT in docs)
- ~~`auto_save`~~ ❌ (NOT REAL - should remove)
- ~~`confirm_on_quit`~~ ❌ (NOT REAL - should remove)
- ~~`confirm_on_clear`~~ ❌ (NOT REAL - should remove)
- ~~`auto_scroll`~~ ❌ (NOT REAL - should remove)

**Advanced/Debug**:
- `debug` ✅
- `log_file` ✅ (NOT in docs)
- ~~`log_level`~~ ❌ (NOT REAL - should remove)
- ~~`max_conversation_history`~~ ❌ (NOT REAL - should remove)

### 5. Features Marked as "Future" - NEED VERIFICATION

Features documented as "(future)" that may actually exist or don't exist:

- ❓ Conversation branching
- ❓ Manual conversation renaming
- ❓ Conversation deletion UI
- ❓ Custom themes
- ❓ Auto theme switching (day/night)
- ❓ Profile management via CLI (`consoul profile`)
- ❓ Config management commands (`consoul config show/edit/reset/validate`)
- ❓ Time-based themes
- ❓ Custom keybindings

### 6. Modals - NEED VERIFICATION

**Verified to exist**:
- ✅ Model Picker Modal
- ✅ Tool Manager Screen
- ✅ Settings Screen
- ✅ Export Modal
- ✅ File Attachment Modal
- ✅ Tool Approval Modal
- ✅ Profile Selector Modal
- ✅ Help Modal
- ✅ System Prompt Modal
- ✅ Import Modal
- ✅ Ollama Library Modal
- ✅ Profile Editor Modal
- ✅ MLX Conversion Modal
- ✅ Tool Call Details Modal

**Documented details that need verification**:
- Tool Manager: exact tools, risk levels, layout
- Export Modal: exact format options, UI layout
- Profile Selector: actual profiles available
- Model Picker: provider tabs, search functionality

## Files Requiring Updates (Priority Order)

### HIGH PRIORITY

1. **`keyboard-shortcuts.md`**
   - Fix all incorrect shortcuts
   - Add missing shortcuts
   - Remove non-existent shortcuts
   - Update quick reference card

2. **`themes.md`**
   - Remove Nord, Gruvbox, Tokyo Night, Flexoki detailed docs
   - Update to focus on 2 Consoul themes
   - Mention Textual built-in themes are available
   - Remove theme comparison table
   - Remove theme screenshots except Consoul ones
   - Update theme selection guide

3. **`tui.md`**
   - Fix keyboard shortcuts in quick reference table
   - Fix theme references
   - Update footer description

### MEDIUM PRIORITY

4. **`configuration.md`**
   - Remove fake config options
   - Add missing real config options
   - Update all examples
   - Fix config schema table

5. **`modals.md`**
   - Verify Settings modal tabs content
   - Update keyboard shortcuts
   - Fix theme selector description
   - Update Tool Manager details

6. **`features.md`**
   - Clearly mark "future" features
   - Verify which features actually exist
   - Remove references to non-existent features

### LOW PRIORITY

7. **`interface.md`**
   - Minor corrections
   - Update footer shortcuts
   - Fix theme color references

## Recommended Approach

1. **Phase 1**: Fix the most critical inaccuracies
   - Update keyboard shortcuts
   - Fix theme documentation
   - Update main TUI page

2. **Phase 2**: Verify and update modals
   - Check Settings Screen implementation for all tabs
   - Verify Tool Manager UI
   - Update modal documentation

3. **Phase 3**: Clean up configuration docs
   - Remove fake config options
   - Document real config options
   - Provide accurate examples

4. **Phase 4**: Mark future features
   - Clearly distinguish implemented vs. planned
   - Update features documentation
   - Add notes about work-in-progress items

## Notes

- All theme screenshots for non-Consoul themes should be removed or moved to a separate section
- The documentation should be clear about Textual's built-in themes vs. Consoul custom themes
- Many keyboard shortcuts are completely wrong and need correction
- Configuration options need major cleanup - many documented options don't exist
