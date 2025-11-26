# CLI Chat Mode

Interactive command-line chat sessions with AI models, featuring streaming responses, slash commands, and tool execution.

## Overview

CLI chat mode provides a lightweight, terminal-based interface for conversing with AI models. Unlike the full TUI mode, CLI chat focuses on quick, single-session interactions with minimal visual overhead.

### When to Use CLI Chat

**Use CLI chat for:**

- Quick questions and answers
- Debugging sessions
- Code assistance conversations
- Scripting and automation
- Remote SSH sessions
- Minimal terminal environments

**Use TUI mode for:**

- Long, complex conversations
- Multiple simultaneous chats
- Rich visual feedback
- Image analysis with attachments
- Advanced session management

## Getting Started

### Basic Usage

Launch an interactive chat session:

```bash
consoul chat
```

You'll see a welcome message with your profile and model information:

```
╭────────────────── Consoul Chat ──────────────────╮
│ Profile: default                                  │
│ Model: anthropic/claude-3-5-sonnet-20241022       │
│                                                   │
│ Type /help for commands | exit or Ctrl+C to quit │
│ Escape clears input                               │
╰──────────────────────────────────────────────────╯

You: _
```

### Your First Conversation

Type your message and press Enter:

```
You: What is the difference between lists and tuples in Python?
Assistant: The main differences between lists and tuples in Python are...
[Response with markdown formatting and syntax highlighting]

You: Can you show me an example?
Assistant: Certainly! Here's an example...

You: /tokens
╭─────────── Token Usage ───────────╮
│ Messages: 2                        │
│ Tokens: 245 / 200,000 (0.1%)       │
│ Model: claude-3-5-sonnet-20241022  │
╰────────────────────────────────────╯

You: /exit
Exiting...

╭─────────── Session Summary ───────────╮
│ Messages: 2                            │
│ Tokens: 245                            │
╰────────────────────────────────────────╯

Goodbye!
```

### Exiting a Session

There are multiple ways to exit:

- Type `exit` and press Enter
- Press `Ctrl+C`
- Press `Ctrl+D`
- Use the `/exit` or `/quit` slash command

## Command-Line Options

### Model Selection

Override the default model from your profile:

```bash
# Use GPT-4o
consoul chat --model gpt-4o

# Use Ollama local model
consoul chat --model llama3

# Use Claude Opus
consoul chat --model claude-3-opus-20240229
```

Short form:

```bash
consoul chat -m gpt-4o
```

### Streaming Control

Disable token-by-token streaming for instant full responses:

```bash
consoul chat --no-stream
```

This shows the complete response at once instead of streaming it token-by-token.

### Markdown Rendering

Disable rich markdown rendering for plain text output:

```bash
consoul chat --no-markdown
```

Useful for:
- Copying responses to clipboard
- Piping output to other commands
- Terminal compatibility issues

### Tool Execution

Override tool execution settings:

```bash
# Disable tools for this session
consoul chat --no-tools

# Enable tools (overrides config)
consoul chat --tools
```

See [Tool Execution & Approval](#tool-execution--approval) for details.

### Multi-Line Input

Enable multi-line input mode for entering code blocks:

```bash
consoul chat --multiline
```

In multi-line mode:
- Press `Enter` to add new lines
- Press `Alt+Enter` to submit your message

### Global Options

These work with all Consoul commands:

```bash
# Use specific profile
consoul --profile creative chat

# Override temperature
consoul --temperature 0.2 chat

# Set max tokens
consoul --max-tokens 1000 chat

# Combine options
consoul --profile code-assistant --temperature 0.1 chat --model gpt-4o
```

## Keyboard Shortcuts

Master these shortcuts for efficient chat sessions:

| Shortcut | Action |
|----------|--------|
| **Enter** | Send message (submit in single-line mode) |
| **Alt+Enter** | Submit message (in multi-line mode only) |
| **Ctrl+C** | Quit the chat session |
| **Ctrl+D** | Quit the chat session (EOF) |
| **Escape** | Clear current input line |
| **Up Arrow** | Navigate to previous input (history) |
| **Down Arrow** | Navigate to next input (history) |
| **Home** | Move cursor to start of line |
| **End** | Move cursor to end of line |

### History Navigation

Use arrow keys to navigate through your input history:

```
You: How do I sort a list?
Assistant: You can use the sorted() function...

You: [Press Up Arrow]
You: How do I sort a list? [Previous input restored]

You: [Press Down Arrow]
You: [Empty - returns to current input]
```

## Slash Commands

Slash commands provide in-session control without exiting. Type `/help` to see all available commands.

### Command Reference

#### `/help` - Show Available Commands

Display all slash commands with descriptions:

```
You: /help

╭───────────── Available Slash Commands ─────────────╮
│ Command     Arguments      Description              │
├────────────────────────────────────────────────────┤
│ /help                      Show this help message   │
│ /clear                     Clear conversation       │
│ /tokens                    Show token usage         │
│ /stats                     Show session statistics  │
│ /exit                      Exit chat session        │
│ /model      <model_name>   Switch to different model│
│ /tools      <on|off>       Toggle tool execution    │
│ /export     <filename>     Export conversation      │
╰────────────────────────────────────────────────────╯
```

Alias: `/help` can also be invoked as `/?`

#### `/clear` - Clear Conversation History

Remove all messages from the current conversation (preserves system prompt):

```
You: /clear
✓ Conversation history cleared (system prompt preserved)
```

Use this to start fresh without exiting and restarting.

#### `/tokens` - Show Token Usage

Display current token count and usage percentage:

```
You: /tokens

╭─────────── Token Usage ───────────╮
│ Messages: 5                        │
│ Tokens: 1,247 / 200,000 (0.6%)     │
│ Model: claude-3-5-sonnet-20241022  │
╰────────────────────────────────────╯
```

Helps monitor usage against model context limits.

#### `/stats` - Session Statistics

Show detailed session information:

```
You: /stats

╭─────────── Session Statistics ───────────╮
│ Model: anthropic/claude-3-5-sonnet-20241022│
│ Session ID: abc123def456                   │
│                                            │
│ Messages:                                  │
│   User: 3                                  │
│   Assistant: 3                             │
│   System: 1                                │
│   Tool: 2                                  │
│   Total: 9                                 │
│                                            │
│ Tokens: 2,456 / 200,000 (1.2%)             │
│                                            │
│ Tools: enabled (5 available)               │
╰────────────────────────────────────────────╯
```

#### `/exit` or `/quit` - Exit Session

Gracefully end the chat session:

```
You: /exit
Exiting...

╭─────────── Session Summary ───────────╮
│ Messages: 10                           │
│ Tokens: 3,421                          │
╰────────────────────────────────────────╯

Goodbye!
```

Aliases: Both `/exit` and `/quit` work identically.

#### `/model <model_name>` - Switch Models

Change to a different AI model mid-session:

```
You: /model gpt-4o
✓ Switched to model: openai/gpt-4o

You: /model llama3
✓ Switched to model: ollama/llama3

You: /model claude-3-opus-20240229
✓ Switched to model: anthropic/claude-3-opus-20240229
```

The provider is auto-detected from the model name. Conversation history is preserved when switching models.

**Common use cases:**

- Switch to a stronger model for complex questions
- Use faster/cheaper models for simple queries
- Compare responses from different models

#### `/tools <on|off>` - Toggle Tool Execution

Enable or disable tool execution during the session:

```
You: /tools off
✓ Tools disabled

You: /tools on
✓ Tools enabled (5 tools available)

You: /tools
Tools: enabled (5 tools available)
Usage: /tools <on|off>
```

Without arguments, `/tools` shows current status.

#### `/export <filename>` - Export Conversation

Save the conversation to a file in markdown or JSON format:

```
You: /export conversation.md
✓ Conversation exported to: conversation.md

You: /export chat-2025-01-15.json
✓ Conversation exported to: chat-2025-01-15.json
```

Format is auto-detected from file extension:

- `.md` - Markdown format with metadata and formatted messages
- `.json` - JSON format with complete message history

**Markdown export example:**

```markdown
# Conversation: abc123def456

**Model**: claude-3-5-sonnet-20241022
**Created**: 2025-01-15T10:30:00
**Messages**: 6
**Total Tokens**: 1,245

---

## 👤 User
*2025-01-15T10:30:05* | *45 tokens*

What is the difference between lists and tuples?

---

## 🤖 Assistant
*2025-01-15T10:30:08* | *312 tokens*

The main differences are...
```

## Tool Execution & Approval

When tools are enabled, the AI can execute commands and search your codebase. The approval workflow depends on your security policy.

### How It Works

1. **AI requests tool execution:**
```
You: What files are in this directory?
Assistant: I'll use the bash tool to check...

╭───────── Tool Execution Request ─────────╮
│ Tool: bash_execute                        │
│ Command: ls -la                           │
│ Risk: SAFE                                │
│                                           │
│ Approve? [y/N]: _                         │
╰───────────────────────────────────────────╯
```

2. **You approve or deny:**
- Type `y` and press Enter to approve
- Type `n` or press Enter to deny
- Press `Ctrl+C` to cancel

3. **Tool executes and AI continues:**
```
Approve? [y/N]: y

[Tool Output]
total 48
drwxr-xr-x  12 user staff  384 Jan 15 10:30 .
drwxr-xr-x   8 user staff  256 Jan 15 09:15 ..
-rw-r--r--   1 user staff 1234 Jan 15 10:25 main.py
...
