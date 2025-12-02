# CLI Chat Mode

Interactive command-line chat sessions with AI models, featuring streaming responses, slash commands, and tool execution.

## Overview

The CLI provides two modes for interacting with AI models:

1. **Interactive Chat** (`consoul chat`) - Multi-turn conversations with REPL loop
2. **One-Off Questions** (`consoul ask`) - Single question/response for scripting

### When to Use Each Mode

**Use `consoul ask` for:**

- Quick one-off questions
- Scripting and automation
- CI/CD pipelines
- Shell aliases and functions
- Single-purpose queries

**Use `consoul chat` for:**

- Multi-turn conversations
- Interactive debugging sessions
- Exploratory discussions
- Context-dependent queries

**Use TUI mode for:**

- Long, complex conversations
- Multiple simultaneous chats
- Rich visual feedback
- Image analysis with attachments
- Advanced session management

## One-Off Questions with `ask`

For quick questions without starting an interactive session, use the `ask` command:

```bash
consoul ask "What is 2+2?"
```

### Basic Syntax

```bash
# Positional argument
consoul ask "Your question here"

# Or with -m flag
consoul ask -m "Your question here"
```

### Common Options

```bash
# Override model
consoul ask "Translate to Spanish" --model gpt-4o

# Enable tools
consoul ask "Find all TODO comments" --tools

# Attach images
consoul ask "What's in this screenshot?" --attach error.png

# Show token usage
consoul ask "Quick question" --show-tokens --show-cost

# Save response to file
consoul ask "Generate template" --output template.txt

# Disable streaming
consoul ask "Long response" --no-stream

# Disable markdown rendering
consoul ask "Plain text please" --no-markdown

# Custom system prompt
consoul ask --system "You are a Python expert" "Explain decorators"
```

### Custom System Prompts with --system

The `--system` flag allows you to customize the AI's role and expertise for a specific query or session without modifying your profile configuration.

**How it works:**
- Your custom prompt is **prepended** to the profile's base system prompt
- Environment context injection (if enabled) is preserved
- Tool documentation is automatically appended
- Applies for the duration of the `ask` query or entire `chat` session

**Basic Usage:**
```bash
# One-off query with custom role
consoul ask --system "You are a security expert" "Review this authentication code" --file auth.py

# Interactive session with custom expertise
consoul chat --system "You are a Python performance expert"
```

**Common Use Cases:**
```bash
# Code review with specific focus
consoul ask --system "You are a senior software engineer reviewing code for security vulnerabilities" \
  --file app.py "Review this code"

# Learning and education
consoul chat --system "You are a patient teacher explaining concepts to a beginner"

# Domain expertise
consoul ask --system "You are an expert in distributed systems and microservices" \
  "How should I design this API?"

# Specific constraints
consoul ask --system "You are a Python expert. Focus on code quality and best practices." \
  --file legacy.py "Suggest refactoring"
```

**Multi-line System Prompts:**
```bash
# Using quotes for multi-line
consoul ask --system "You are an expert programmer.
Focus on code quality and best practices.
Prioritize security and performance." "Review this function"

# Using heredoc
consoul ask --system "$(cat <<'EOF'
You are a code reviewer with expertise in:
- Security best practices
- Performance optimization
- Clean code principles
EOF
)" --file app.py "Review this code"
```

**Combining with Other Flags:**
```bash
# With file context
consoul ask --system "You are a security auditor" --file app.py --tools "Find vulnerabilities"

# With stdin
git diff | consoul ask --stdin --system "You are a code reviewer" "Review this diff"

# With model override
consoul ask --system "You are a Python expert" --model gpt-4o "Explain this pattern"
```

**System Prompt Construction:**

When you use `--system`, the final system prompt is built in this order:

1. **Your custom prompt** (from --system flag)
2. **Profile base prompt** (from your active profile configuration)
3. **Environment context** (if enabled: OS, shell, git status, etc.)
4. **Tool documentation** (automatically generated list of available tools)

Example:
```bash
consoul ask --system "You are a security expert"
```

Results in:
```
You are a security expert

<profile base system prompt>

<environment context if enabled>

<available tools documentation>
```

### Pipeline Integration with --stdin

The `--stdin` flag enables Unix pipeline patterns, allowing you to pipe command output directly to Consoul for AI analysis:

**Basic Usage:**
```bash
# Analyze command output
docker ps | consoul ask --stdin "Which containers are using most resources?"

# Debug test failures
pytest tests/ 2>&1 | consoul ask --stdin "Explain these test failures"

# Code review
git diff main..feature | consoul ask --stdin "Review this diff for bugs"

# Error analysis
python script.py 2>&1 | consoul ask --stdin "What's causing this error?"
```

**With Interactive Chat:**
```bash
# Load context then discuss interactively
tail -100 app.log | consoul chat --stdin
# Stdin content is loaded, then you're prompted for your question
# After first message, continues as normal interactive chat
```

**Combining with Other Flags:**
```bash
# With file attachments
git diff | consoul ask --stdin "Review this" --attach README.md --tools

# With model override
curl https://api.example.com | consoul ask --stdin "Analyze this API response" --model gpt-4o

# Save analysis to file
docker stats --no-stream | consoul ask --stdin "Summarize resource usage" --output report.txt
```

**Common Patterns:**
```bash
# Log monitoring
tail -f app.log | consoul ask --stdin "Alert me on errors"

# Performance analysis
time ./benchmark.sh 2>&1 | consoul ask --stdin "How can I optimize this?"

# Security review
git show HEAD | consoul ask --stdin "Security review this commit"

# Data transformation
cat data.json | consoul ask --stdin "Convert this to CSV format"
```

**Shell Redirection:**
```bash
# Read from file
consoul ask --stdin "Analyze this log" < error.log

# Here document
consoul ask --stdin "Fix these issues" <<EOF
Error 1: Connection timeout
Error 2: Memory leak
EOF
```

### File Context with --file and --glob

Provide code and configuration files directly as context for AI analysis:

**Single File:**
```bash
consoul ask --file app.py "Review this code for bugs"
consoul ask --file config.yaml "Explain this configuration"
```

**Multiple Files:**
```bash
consoul ask \
  --file src/app.py \
  --file src/utils.py \
  --file tests/test_app.py \
  "How do these components work together?"
```

**Glob Patterns:**
```bash
# All Python files in current directory
consoul ask --glob "*.py" "What does this project do?"

# Recursive search
consoul ask --glob "src/**/*.ts" "Analyze the TypeScript codebase"

# Multiple patterns
consoul ask --glob "*.py" --glob "*.yaml" "Review code and configuration"

# Specific directory pattern
consoul ask --glob "tests/**/*.py" "Summarize test coverage"
```

**Combining File and Glob:**
```bash
# Mix explicit files and patterns
consoul ask --file README.md --glob "src/*.py" "Explain this project"

# Multiple glob patterns
consoul ask --glob "*.py" --glob "*.js" --glob "*.ts" "Compare implementations"
```

**With Other Flags:**
```bash
# Files + tools
consoul ask --file app.py --tools "Fix the TODO comments in this file"

# Files + stdin
git diff | consoul ask --stdin "Review diff" --file README.md

# Files + model override
consoul ask --file auth.py --model gpt-4o "Security audit this code"

# Save analysis
consoul ask --glob "src/**/*.py" "Generate report" --output analysis.md
```

**Interactive Chat with Files:**
```bash
# Load files as context for interactive session
consoul chat --file app.py --file utils.py --glob "tests/*.py"
# Files are loaded once, then you can ask multiple questions interactively
```

**Limits:**
- Single file: 100KB max
- Total context: 500KB max across all files
- Glob expansion: 50 files max per pattern
- Binary files are rejected (except PDFs with vision models)

**Use Cases:**
```bash
# Code review
consoul ask --glob "src/**/*.py" "Code review with focus on error handling"

# Refactoring suggestions
consoul ask --file legacy.py "Suggest refactoring to modern Python"

# Documentation generation
consoul ask --glob "*.py" "Generate API documentation" --output API.md

# Security audit
consoul ask --glob "**/*auth*.py" "Security review authentication code"

# Cross-file analysis
consoul ask --file frontend.ts --file backend.py "Check API contract consistency"
```

### Use Cases

**Shell Aliases:**
```bash
# Add to ~/.zshrc or ~/.bashrc
alias ai='consoul ask'
alias aicode='consoul ask --model claude-3-5-sonnet-20241022 --tools'

# Usage
ai "What's the weather like?"
aicode "Refactor this function"
```

**Git Hooks:**
```bash
#!/bin/bash
# .git/hooks/pre-commit
STAGED=$(git diff --cached --name-only)
consoul ask "Review these changes: $STAGED" --tools --no-stream
```

**CI/CD Pipeline:**
```yaml
# .github/workflows/review.yml
- name: AI Code Review
  run: |
    consoul ask "Review this PR and suggest improvements" \
      --tools --output review.md
```

## Interactive Chat with `chat`

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
**Total Tokens**: (not tracked in CLI export)

---

## 👤 User
*2025-01-15T10:30:05*

What is the difference between lists and tuples?

---

## 🤖 Assistant
*2025-01-15T10:30:08*

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
- (Cancel the session to abort the request)

3. **Tool executes and AI continues:**
```
Approve? [y/N]: y

[Tool Output]
total 48
drwxr-xr-x  12 user staff  384 Jan 15 10:30 .
drwxr-xr-x   8 user staff  256 Jan 15 09:15 ..
-rw-r--r--   1 user staff 1234 Jan 15 10:25 main.py
...
