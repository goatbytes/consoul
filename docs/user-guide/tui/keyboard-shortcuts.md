# Keyboard Shortcuts

Complete reference of all keyboard shortcuts in the Consoul TUI.

## Global Shortcuts

These shortcuts work from anywhere in the TUI.

| Shortcut | Action | Description |
|----------|--------|-------------|
| `q` | Quit | Exit Consoul |
| `^c` | Quit | Alternative quit (Ctrl+C) |
| `^n` | New Chat | Create new conversation |
| `^l` | Clear | Clear current conversation messages |
| `^b` | Toggle Sidebar | Show/hide conversation list sidebar |
| `^e` | Export | Export current conversation |
| `^i` | Import | Import conversation from file |
| `^t` | Tools | Open tool manager modal |
| `^comma` | Settings | Open settings modal (Ctrl+,) |
| `^m` | Model | Open model picker modal |
| `^p` | Profile | Open profile selector |
| `^o` | Ollama Library | Browse Ollama model library |
| `^s` | Search History | Search conversation history |
| `^shift+p` | Permissions | Open permissions/tool manager (alias) |
| `^shift+s` | System Prompt | View/edit system prompt |
| `f1` | Help | Show help modal |
| `/` | Focus Input | Move focus to input area |
| `Esc` | Cancel | Cancel streaming response or close modal |
| `Tab` | Focus Next | Move focus to next UI element |
| `Shift+Tab` | Focus Previous | Move focus to previous UI element |

## Input Area

Shortcuts for composing and sending messages.

| Shortcut | Action | Description |
|----------|--------|-------------|
| `Enter` | Send Message | Send the current message |
| `Shift+Enter` | New Line | Insert newline without sending |
| `^a` | Select All | Select all text in input |
| `^c` | Copy | Copy selected text |
| `^v` | Paste | Paste from clipboard |
| `^x` | Cut | Cut selected text |
| `^z` | Undo | Undo last edit |
| `^y` | Redo | Redo last undo |
| `Home` | Start of Line | Move cursor to start of line |
| `End` | End of Line | Move cursor to end of line |
| `^Home` | Start of Input | Move cursor to start of text |
| `^End` | End of Input | Move cursor to end of text |

## Conversation Sidebar

Shortcuts for navigating and managing conversations.

| Shortcut | Action | Description |
|----------|--------|-------------|
| `^b` | Toggle Sidebar | Show/hide sidebar |
| `^s` | Search | Search conversation history |
| `↑` | Previous | Move selection up (when focused) |
| `↓` | Next | Move selection down (when focused) |
| `Enter` | Load | Load selected conversation |
| `Esc` | Clear Search | Clear search query and unfocus |

## Chat Area

Shortcuts for interacting with messages.

| Shortcut | Action | Description |
|----------|--------|-------------|
| `↑` | Scroll Up | Scroll chat area up |
| `↓` | Scroll Down | Scroll chat area down |
| `PageUp` | Page Up | Scroll up one page |
| `PageDown` | Page Down | Scroll down one page |
| `Home` | Top | Scroll to top of conversation |
| `End` | Bottom | Scroll to bottom of conversation |
| `Esc` | Cancel Stream | Stop streaming response |

## File Attachment Browser

Shortcuts in the file selection modal (if available via button).

| Shortcut | Action | Description |
|----------|--------|-------------|
| `↑` | Previous Item | Move selection up |
| `↓` | Next Item | Move selection down |
| `→` | Expand | Open/expand selected directory |
| `←` | Collapse | Close/collapse selected directory |
| `Space` | Toggle | Select/deselect file |
| `Enter` | Confirm | Open directory or confirm selection |
| `Esc` | Cancel | Close modal without attaching |
| `Backspace` | Parent | Navigate to parent directory |

## Settings Modal

Shortcuts in the settings dialog.

| Shortcut | Action | Description |
|----------|--------|-------------|
| `^comma` | Open | Open settings modal |
| `Tab` | Next Field | Move to next setting |
| `Shift+Tab` | Previous Field | Move to previous setting |
| `Space` | Toggle | Toggle boolean settings |
| `Enter` | Apply | Save and apply settings |
| `Esc` | Cancel | Close without saving |
| `→` | Next Tab | Switch to next settings tab |
| `←` | Previous Tab | Switch to previous settings tab |

**Settings Tabs**:
- Appearance
- Performance
- Behavior
- Advanced

## Model Selector Modal

Shortcuts for selecting AI models and providers.

| Shortcut | Action | Description |
|----------|--------|-------------|
| `^m` | Open | Open model selector |
| `Tab` | Next Provider | Switch to next provider tab |
| `Shift+Tab` | Previous Provider | Switch to previous provider tab |
| `↑` | Previous Model | Move selection up |
| `↓` | Next Model | Move selection down |
| `Enter` | Select | Choose selected model and close |
| `Esc` | Cancel | Close without changing model |

**Provider Tabs**:
- Openai
- Anthropic
- Google
- HuggingFace
- Local (Ollama)

## Tool Manager Modal

Shortcuts for managing AI tools.

| Shortcut | Action | Description |
|----------|--------|-------------|
| `^t` | Open | Open tool manager |
| `↑` | Previous Tool | Move selection up |
| `↓` | Next Tool | Move selection down |
| `Space` | Toggle | Enable/disable selected tool |
| `Enter` | Apply | Save tool configuration |
| `Esc` | Cancel | Close without saving |

## Profile Selector Modal

Shortcuts for selecting profiles.

| Shortcut | Action | Description |
|----------|--------|-------------|
| `^p` | Open | Open profile selector |
| `↑` | Previous | Move selection up |
| `↓` | Next | Move selection down |
| `Enter` | Select | Load selected profile |
| `Esc` | Cancel | Close without changing profile |

## Export Dialog

Shortcuts for exporting conversations.

| Shortcut | Action | Description |
|----------|--------|-------------|
| `^e` | Open | Open export dialog |
| `Tab` | Next Option | Move to next export option |
| `Shift+Tab` | Previous | Move to previous option |
| `Space` | Toggle | Toggle checkboxes |
| `Enter` | Export | Export with selected options |
| `Esc` | Cancel | Close without exporting |

## Help Modal

View keyboard shortcuts and help.

| Shortcut | Action | Description |
|----------|--------|-------------|
| `f1` | Open | Show help modal |
| `Esc` | Close | Close help modal |

## Import Dialog

Import conversations from file.

| Shortcut | Action | Description |
|----------|--------|-------------|
| `^i` | Open | Open import dialog |
| `Enter` | Confirm | Import selected file |
| `Esc` | Cancel | Close without importing |

## Platform-Specific Modifiers

The `^` symbol represents the Control key:

### macOS
- `^` = `Control` (not `Command`)
- `⌘` (Command) is not used in Consoul shortcuts
- `⌥` (Option) = `Alt`

### Linux/Windows
- `^` = `Control` (Ctrl)
- `Alt` available but not currently used

## Quick Reference Card

Essential shortcuts for daily use:

```
╔══════════════════════════════════════════╗
║      CONSOUL KEYBOARD SHORTCUTS          ║
╠══════════════════════════════════════════╣
║ GLOBAL                                   ║
║ q         Quit                           ║
║ ^n        New conversation               ║
║ ^l        Clear conversation             ║
║ ^b        Toggle sidebar                 ║
║ ^comma    Settings (Ctrl+,)              ║
║ ^m        Model picker                   ║
║ ^p        Profile selector               ║
║ ^e        Export                         ║
║ ^t        Tools                          ║
║ ^shift+p  Permissions                    ║
║ ^s        Search history                 ║
║ f1        Help                           ║
╠══════════════════════════════════════════╣
║ INPUT                                    ║
║ Enter     Send message                   ║
║ Shift+↵   New line                       ║
║ /         Focus input                    ║
╠══════════════════════════════════════════╣
║ NAVIGATION                               ║
║ ↑↓        Scroll/Navigate                ║
║ PgUp/PgDn Page up/down                   ║
║ Home/End  Top/Bottom                     ║
║ Tab       Next focus                     ║
║ Esc       Cancel/Close                   ║
╚══════════════════════════════════════════╝
```

## Tips for Power Users

### Essential Workflow

**Quick conversation management:**
```
^n          → New conversation
^s          → Search conversations
^e          → Export current
^i          → Import conversation
```

**Quick settings:**
```
^comma      → Open settings
^m          → Switch model
^p          → Switch profile
^t          → Manage tools
```

**Navigation:**
```
^b          → Toggle sidebar
/           → Focus input
Esc         → Cancel/close
Tab         → Cycle through UI
```

### Efficiency Tips

1. **Keep Hands on Keyboard**: Master global shortcuts to avoid mouse
2. **Use Search**: `^s` to quickly find past conversations
3. **Quick Navigation**: `Home`/`End` in chat to jump to start/end
4. **Model Switching**: `^m` for rapid model changes
5. **Tool Management**: `^t` for quick tool enable/disable

## Troubleshooting

### Shortcut Not Working

**Common Issues:**

1. **Terminal Compatibility**: Some terminals intercept certain key combinations
   - Try different terminal emulator
   - Check terminal preferences for key mappings

2. **Focus Context**: Some shortcuts only work in specific contexts
   - Ensure correct widget is focused
   - Try clicking on the target area first

3. **Platform Differences**: macOS vs Linux/Windows
   - `^` = Control on all platforms
   - Command key is not used

### Terminal-Specific Issues

**tmux/screen:**
```bash
# May need to configure pass-through in config
# Check .tmux.conf or .screenrc
```

**iTerm2/Terminal.app (macOS):**
```
Preferences → Profiles → Keys
Check "Use Option as Meta key" setting
```

**Windows Terminal:**
```json
// settings.json
// Check for conflicting keybindings
```

## Next Steps

- [TUI Features](features.md) - Explore all features
- [Modals & Dialogs](modals.md) - Detailed modal documentation
- [Interface Guide](interface.md) - UI component reference
- [Configuration](configuration.md) - Configure keybindings (future)
