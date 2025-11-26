# Quick Start

Get up and running with Consoul in just a few minutes!

## Prerequisites

Make sure you've [installed Consoul](installation.md) and configured your API keys.

## Your First Conversation

### Using the Interactive TUI

Launch Consoul's terminal UI:

```bash
consoul tui
```

This opens an interactive interface where you can:

- Type messages and get AI responses
- View conversation history
- Switch between AI providers
- Manage settings

**Basic Controls:**

- `Ctrl+C` or `/quit` – Exit Consoul
- `Ctrl+L` – Clear screen
- `↑/↓` – Navigate history
- `Tab` – Auto-complete commands

### Using CLI Chat Mode

Launch an interactive chat session:

```bash
consoul chat
```

Once in the session, you can have a conversation:

```
You: How do I list all Python files in a directory?
Assistant: You can use several methods...

You: /tokens
[Shows token usage]

You: /exit
```

## Common Use Cases

### Getting Code Help

Use CLI chat for coding assistance:

```bash
$ consoul chat

You: Write a Python function to merge two sorted lists
Assistant: [Provides solution with explanation]

You: Can you show me how to test this?
Assistant: [Provides testing examples]
```

### Code Exploration

Use the TUI mode for exploring code:

```bash
$ consoul tui

# In TUI, enable tools and ask:
You: Find all TODO comments in Python files
# AI uses grep_search tool with approval

You: Show me the User class definition
# AI uses code_search tool
```

### Debugging Sessions

Use slash commands during debugging:

```bash
$ consoul chat --model gpt-4o

You: I'm getting a KeyError in my dictionary access. How do I debug this?
Assistant: [Provides debugging strategies]

You: /model claude-3-5-sonnet-20241022
# Switch to Claude for a second opinion

You: Same question - what's your approach?
Assistant: [Provides alternative perspective]

You: /export debug-session.md
# Save the conversation for reference
```

### Quick Command Help

Fast answers to shell questions:

```bash
$ consoul chat

You: How do I find all files larger than 100MB?
Assistant: You can use the find command: `find . -type f -size +100M`

You: /exit
```

## Working with Context

### TUI Mode Features

The TUI mode supports rich context management:

- **File attachments** - Click the 📎 button to attach files to your message
- **Image analysis** - Attach screenshots and images for visual analysis
- **Multiple conversations** - Manage separate conversation tabs

```bash
consoul tui
```

### CLI Chat Mode

CLI chat mode is focused on conversational interactions. For file analysis and complex workflows, use the TUI mode.

## Conversation Management

Conversations are automatically persisted to a local SQLite database when enabled in your configuration.

### Managing History

```bash
# List recent conversations
consoul history list

# Show a specific conversation
consoul history show <session-id>

# Export a conversation
consoul history export <session-id> output.md --format markdown

# Search conversation history
consoul history search "python decorators"

# Clear all history
consoul history clear
```

### Session Controls

Within CLI chat mode, use slash commands:

```bash
You: /export my-session.md    # Export current conversation
You: /clear                    # Clear history, start fresh
You: /tokens                   # Check usage
```

## Configuration

Configuration is managed through YAML files. See the [Configuration Guide](user-guide/configuration.md) for details.

### Profile Selection

```bash
# Use a specific profile
consoul --profile creative chat

# List available profiles
consoul --list-profiles
```

### Quick Overrides

```bash
# Override model
consoul chat --model gpt-4o

# Override temperature
consoul --temperature 0.2 chat

# Combine options
consoul --profile code-assistant --temperature 0.1 chat
```

## Advanced Usage

### Model Switching Mid-Session

Switch models during a conversation using the `/model` slash command:

```bash
$ consoul chat

You: Explain Python decorators
Assistant: [GPT-4o response]

You: /model claude-3-5-sonnet-20241022
✓ Switched to model: anthropic/claude-3-5-sonnet-20241022

You: Now explain the same concept
Assistant: [Claude response with different perspective]
```

### Temperature Control

Adjust response creativity via global options:

```bash
# More deterministic (good for code)
consoul --temperature 0.2 chat

# More creative (good for writing)
consoul --temperature 0.9 chat

# Change mid-session using profile switch
You: /model gpt-4o
```

### Export and Share

Export conversations for documentation or sharing:

```bash
You: /export session-2025-01-15.md
✓ Conversation exported to: session-2025-01-15.md

You: /export debug-notes.json
✓ Conversation exported to: debug-notes.json
```

## Interactive Commands

### TUI Mode Commands

Within the TUI mode (`consoul tui`), use menu-driven interface:

- **Ctrl+N** - New conversation
- **Ctrl+S** - Save conversation
- **Ctrl+O** - Open/switch conversations
- **Ctrl+Q** or `/quit` - Exit

See [TUI Guide](user-guide/tui.md) for complete keyboard shortcuts.

### CLI Chat Mode Slash Commands

Within CLI chat sessions (`consoul chat`), use slash commands:

```
/help                   Show available commands
/clear                  Clear conversation history
/tokens                 Show token usage
/stats                  Session statistics
/exit, /quit            Exit session
/model <name>           Switch model
/tools <on|off>         Toggle tools
/export <filename>      Export conversation
```

See [CLI Chat Guide](user-guide/cli-chat.md) for complete documentation.

## Tips and Tricks

### Use Aliases

Add shell aliases for quick access:

```bash
# Add to ~/.zshrc or ~/.bashrc
alias ask="consoul chat"
alias tui="consoul tui"
```

Then use them:

```bash
ask            # Launch CLI chat
tui            # Launch TUI mode
```

### Efficient Workflows

**Quick questions:**
```bash
# Launch, ask, exit
$ consoul chat
You: What's the difference between lists and tuples?
Assistant: [Answer]
You: /exit
```

**Code exploration (use TUI):**
```bash
$ consoul tui
# Use rich interface with file attachments and tools
```

**Compare models:**
```bash
$ consoul chat
You: Explain decorators
Assistant: [GPT-4o answer]

You: /model claude-3-5-sonnet-20241022
Assistant: [Claude answer]

You: /export model-comparison.md
```

### Session Management

```bash
# Save and review later
$ consoul chat
You: [Long debugging session]
You: /export debug-2025-01-15.md

# Search history later
$ consoul history search "decorator"
```

## Keyboard Shortcuts

**TUI Mode:**

| Shortcut | Action |
|----------|--------|
| `Ctrl+C` | Exit |
| `Ctrl+L` | Clear screen |
| `Ctrl+D` | Delete character |
| `Ctrl+U` | Clear line |
| `↑/↓` | Navigate history |
| `Home/End` | Move to line start/end |
| `Tab` | Auto-complete |

## Next Steps

- [User Guide](user-guide/getting-started.md) – Learn all features in depth
- [Configuration](user-guide/configuration.md) – Customize Consoul
- [Development](development.md) – Contribute to Consoul

## Getting Help

- Run `consoul --help` for CLI help
- Type `/help` in TUI mode for interactive help
- Visit the [documentation](index.md) for detailed guides
- Report issues on [GitHub](https://github.com/goatbytes/consoul/issues)
