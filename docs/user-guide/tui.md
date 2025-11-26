# Terminal User Interface (TUI)

Consoul's Terminal User Interface provides a rich, interactive chat experience directly in your terminal. Built with [Textual](https://textual.textualize.io/), it offers a modern, responsive interface similar to ChatGPT or Claude, but with the convenience and power of staying in your command-line workflow.

![Consoul TUI Themes](../assets/screenshots/consoul-themes.gif)

## Why Use the TUI?

The TUI mode is ideal when you want:

- **Rich Interactive Experience**: Full-featured chat interface with real-time streaming, syntax highlighting, and visual tool execution
- **Conversation Management**: Easy access to conversation history, search, and resume functionality
- **Multi-turn Conversations**: Natural back-and-forth dialogue with persistent context
- **Visual Feedback**: See tool calls, system messages, and AI reasoning in real-time
- **File Attachments**: Drag and attach files visually for context
- **Settings Access**: Quick access to model selection, themes, and tool permissions

## Launching the TUI

```bash
# Basic launch
consoul tui

# Launch with specific model
consoul tui --model claude-3-5-sonnet-20241022

# Launch with specific profile
consoul tui --profile creative

# Launch with custom config
consoul tui --config ~/my-consoul-config.yaml
```

## Quick Tour

### Main Interface Components

The TUI consists of several key areas:

1. **Header Bar** - Shows app name, conversation count, search, current model, and profile
2. **Conversation Sidebar** (toggleable) - Card-based list of all conversations with search
3. **Chat Area** - Main conversation view with message bubbles and tool execution displays
4. **Input Area** - Multi-line text input with file attachment support
5. **Footer** - Keyboard shortcuts and quick actions

![TUI Interface](../assets/screenshots/consoul-screenshot-start.png)
*Empty state with sidebar showing "No conversations yet"*

### Message Types

Consoul displays different message types with distinct visual styles:

- **User Messages** - Your prompts and questions (blue border, right-aligned title)
- **Assistant Messages** - AI responses (purple border, left-aligned title)
- **System Messages** - Tool executions and system events (muted colors)
- **Tool Call Widgets** - Interactive display of tool execution with status indicators

![Tool Execution](../assets/screenshots/consoul-screenshot-conversation-with-tool-calls.png)
*Tool calls shown as expandable widgets with execution status*

## Key Features

### 🗨️ Conversation Management

- Create unlimited conversations
- Search through conversation titles
- Resume previous conversations with full context
- Rename conversations
- Delete conversations
- Auto-generated conversation titles

### ⚡ Real-Time Streaming

- Streaming token display as the AI generates responses
- Live tool execution feedback
- Thinking indicators for extended reasoning
- Token count and performance metrics

### 📎 File Attachments

- Attach files to provide context
- Visual file browser with tree navigation
- Multi-file selection
- File chips showing attached files
- Easy removal of attachments

![File Attachment](../assets/screenshots/modal-attach.png)

### 🛠️ Tool Execution

- Visual tool call widgets
- Execution status (pending, executing, success, error, denied)
- Expandable tool output
- Approval/denial workflow for dangerous operations
- Tool manager for enabling/disabling tools

![Tool Manager](../assets/screenshots/modal-tool-manager.png)

### 🎨 Themes

Consoul provides two official brand themes, plus access to Textual's built-in themes:

**Official Consoul Themes:**
- **Consoul Dark** - Brand dark theme (default)
- **Consoul Light** - Brand light theme

**Available Textual Themes:**
- Nord, Gruvbox, Tokyo Night, Dracula, Monokai, Catppuccin, Solarized, Flexoki, and more

![Theme Example](../assets/screenshots/theme-consoul-dark.png)

[See all themes →](tui/themes.md)

### ⚙️ Settings

Quick access to configuration:

- Theme selection
- Display options (sidebar, timestamps, token counts)
- Syntax highlighting toggle
- Multiple tabs: Appearance, Performance, Behavior, Advanced

![Settings Modal](../assets/screenshots/modal-settings.png)

## Getting Started

### 1. Launch Consoul

```bash
consoul tui
```

### 2. Start a Conversation

- Type your message in the input area
- Press `Enter` to send (or `Shift+Enter` for new line)
- Watch the response stream in real-time

### 3. Attach Files (Optional)

- Click the `+ Attach` button
- Navigate the file tree
- Select files with `Space`
- Confirm with `Enter`

### 4. Manage Conversations

- Click conversation count in header to toggle sidebar
- Search conversations with the search bar
- Click any conversation card to load it
- Use `^n` to create a new conversation

### 5. Customize

- Press `^comma` (Ctrl+,) to open settings
- Choose your preferred theme
- Toggle display options
- Press `^t` to access the tool manager

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `q` | Quit application |
| `^n` | New conversation |
| `^l` | Clear current conversation |
| `^b` | Toggle sidebar |
| `^comma` | Settings (Ctrl+,) |
| `^m` | Model picker |
| `^p` | Profile selector |
| `^e` | Export conversation |
| `^i` | Import conversation |
| `^t` | Tools manager |
| `^s` | Search history |
| `shift+^p` | Permissions (alias for ^t) |
| `f1` | Help |
| `Enter` | Send message |
| `Shift+Enter` | New line in input |

[Full keyboard shortcuts reference →](tui/keyboard-shortcuts.md)

## Learn More

- [TUI Interface Guide](tui/interface.md) - Detailed UI component reference
- [TUI Features](tui/features.md) - In-depth feature documentation
- [Keyboard Shortcuts](tui/keyboard-shortcuts.md) - Complete shortcut reference
- [Modals & Dialogs](tui/modals.md) - Settings, tools, and model selection
- [Themes](tui/themes.md) - Theme gallery and customization
- [Configuration](tui/configuration.md) - TUI-specific configuration options

## Tips & Tricks

### Productivity

- Use `^n` frequently to keep conversations organized by topic
- Search conversations with `^b` to quickly find past discussions
- Attach files before asking questions for better context
- Use the tool manager to enable only the tools you need

### Performance

- Toggle timestamps and token counts off for cleaner UI
- Collapse the sidebar when focusing on a single conversation
- Use lighter themes on slower terminals for better performance

### Workflows

1. **Code Review**: Attach files → Ask for review → Use tool execution for fixes
2. **Debugging**: Copy error → Paste in Consoul → Attach relevant files → Get diagnosis
3. **Learning**: Ask questions → Save conversation → Resume later for follow-ups
4. **Research**: Multi-turn conversation → Export to markdown for documentation

## Troubleshooting

### TUI Won't Launch

```bash
# Check if consoul is installed
which consoul

# Verify Python version (3.12+ required)
python --version

# Try with explicit python
python -m consoul.tui
```

### Display Issues

- Ensure your terminal supports 24-bit color
- Try different themes in settings
- Increase terminal window size
- Check terminal font supports Unicode

### Performance Issues

- Reduce max tokens in settings
- Disable syntax highlighting
- Use a lighter theme
- Close other terminal applications

## Next Steps

Ready to dive deeper? Check out:

- **[Interface Guide](tui/interface.md)** - Learn every component of the UI
- **[Keyboard Shortcuts](tui/keyboard-shortcuts.md)** - Become a power user
- **[Configuration](tui/configuration.md)** - Customize your experience
