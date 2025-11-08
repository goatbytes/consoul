# Quick Start

Get up and running with Consoul in just a few minutes!

## Prerequisites

Make sure you've [installed Consoul](installation.md) and configured your API keys.

## Your First Conversation

### Using the Interactive TUI

Launch Consoul's terminal UI:

```bash
consoul
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

### Using the CLI

For quick one-off questions:

```bash
consoul chat "How do I list all Python files in a directory?"
```

## Common Use Cases

### Getting Code Help

Ask for coding assistance:

```bash
consoul chat "Write a Python function to merge two sorted lists"
```

### Explaining Code

Include a file in your conversation:

```bash
consoul chat --file main.py "Explain what this code does"
```

### Debugging Errors

Pipe error output directly:

```bash
python script.py 2>&1 | consoul chat --stdin "What's causing this error?"
```

### Learning Commands

Get help with shell commands:

```bash
consoul chat "How do I find all files larger than 100MB?"
```

## Working with Context

### Include Files

```bash
# Single file
consoul chat --file app.py "Review this code"

# Multiple files
consoul chat --file app.py --file utils.py "How do these modules work together?"
```

### Include Directory Context

```bash
# Include all Python files in current directory
consoul chat --glob "*.py" "What does this project do?"
```

### Pipe Terminal Output

```bash
# Include command output
git status | consoul chat --stdin "Explain these changes"

# Include error logs
cat error.log | consoul chat --stdin "Help me debug this"
```

## Conversation Management

### Save Conversations

Conversations are automatically saved (if enabled in config):

```bash
# List saved conversations
consoul history list

# Resume a conversation
consoul history resume <conversation-id>

# Export a conversation
consoul history export <conversation-id> --format markdown
```

### Start a New Conversation

```bash
# Start fresh
consoul chat --new "Let's discuss Python decorators"
```

## Configuration

### Quick Config Changes

```bash
# Switch AI provider
consoul config set provider openai

# Change model
consoul config set model gpt-4

# Set theme
consoul config set theme light
```

### View Current Config

```bash
consoul config show
```

## Advanced Usage

### System Prompts

Set a custom system prompt for the session:

```bash
consoul chat --system "You are a Python expert" "Explain list comprehensions"
```

### Temperature Control

Adjust response creativity:

```bash
# More deterministic (0.0 - 1.0)
consoul chat --temperature 0.2 "Write a sorting function"

# More creative
consoul chat --temperature 0.9 "Write a creative story"
```

### Token Limits

Control response length:

```bash
consoul chat --max-tokens 500 "Summarize Python decorators briefly"
```

## Interactive Commands

Within the TUI, you can use commands:

```
/help              Show available commands
/clear             Clear the screen
/new               Start a new conversation
/save              Save current conversation
/config            View configuration
/provider <name>   Switch AI provider
/model <name>      Switch model
/quit              Exit Consoul
```

## Tips and Tricks

### Use Aliases

Add shell aliases for common tasks:

```bash
# Add to ~/.zshrc or ~/.bashrc
alias ask="consoul chat"
alias explain="consoul chat --stdin"
alias code-review="consoul chat --file"
```

Then use them:

```bash
ask "What's the difference between lists and tuples?"
git diff | explain "Review these changes"
code-review main.py "Any improvements?"
```

### Context-Aware Development

```bash
# Get project overview
consoul chat --glob "**/*.py" "Summarize this Python project"

# Code review
git diff main | consoul chat --stdin "Review this change"

# Generate tests
consoul chat --file app.py "Write pytest tests for this module"
```

### Workflow Integration

```bash
# Git commit messages
git diff --staged | consoul chat --stdin "Generate a conventional commit message" \
  | git commit -F -

# Code documentation
consoul chat --file api.py "Generate docstrings" > docs/api.md

# Error investigation
pytest 2>&1 | consoul chat --stdin "Why are these tests failing?"
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
