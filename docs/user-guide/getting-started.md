# Getting Started

Welcome to Consoul! This guide will help you get the most out of your AI-powered terminal assistant.

## Overview

Consoul is designed to bring AI assistance directly into your terminal workflow. Whether you're debugging code, learning new concepts, or getting help with commands, Consoul provides a seamless, terminal-native experience.

## Core Concepts

### Providers

Consoul supports multiple AI providers through LangChain:

- **Anthropic** (Claude) – Excellent at code and reasoning
- **OpenAI** (GPT) – Versatile general-purpose AI
- **Google** (Gemini) – Fast and efficient
- **Local Models** (Ollama) – Privacy-focused, offline-capable

### Conversations

Each interaction with Consoul is part of a conversation that maintains context across multiple messages. This allows for:

- Follow-up questions
- Iterative refinement
- Context-aware responses

### Context

You can provide context to Consoul in several ways:

- **Files** – Include source code, configs, logs
- **Stdin** – Pipe command output directly
- **Globs** – Include multiple files matching a pattern
- **System Prompts** – Set the AI's role and behavior

## Usage Modes

### 1. Interactive TUI Mode

The Terminal UI provides a rich, interactive experience:

```bash
consoul tui
```

**Features:**

- Live streaming responses
- Syntax highlighting
- Conversation history
- Settings panel
- Multi-line input

### 2. CLI Mode

Quick one-off queries:

```bash
consoul ask "Your question here"
```

**Use cases:**

- Quick questions
- Scripting and automation
- Pipeline integration

### 3. Pipeline Mode

Integrate with Unix pipelines:

```bash
cat README.md | consoul ask --stdin "summarize"
```

## Working with Files

### Single File

```bash
consoul chat --file main.py "Review this code"
```

### Multiple Files

```bash
consoul chat \
  --file app.py \
  --file utils.py \
  --file config.yaml \
  "How do these files work together?"
```

### Pattern Matching

```bash
# All Python files
consoul chat --glob "*.py" "What does this project do?"

# Recursive
consoul chat --glob "**/*.py" "Analyze the codebase structure"
```

## Configuration

### Location

Consoul configuration is stored at:

```
~/.config/consoul/config.yaml
```

### Basic Settings

```yaml
# Default AI provider
provider: anthropic

# Model to use
model: claude-3-5-sonnet-20241022

# UI theme
theme: dark

# Save conversations
save_conversations: true

# Maximum conversation history
max_history: 50
```

### Provider-Specific Settings

```yaml
providers:
  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
    default_model: claude-3-5-sonnet-20241022
    max_tokens: 4096

  openai:
    api_key: ${OPENAI_API_KEY}
    default_model: gpt-4
    temperature: 0.7

  google:
    api_key: ${GOOGLE_API_KEY}
    default_model: gemini-pro
```

## Best Practices

### 1. Provide Context

More context = better responses:

```bash
# Good
consoul chat --file app.py "How can I optimize this function?"

# Better
consoul chat \
  --file app.py \
  --file requirements.txt \
  --system "You are a Python performance expert" \
  "How can I optimize this function?"
```

### 2. Be Specific

```bash
# Vague
consoul ask "Fix my code"

# Specific
consoul ask --file broken.py "This function raises a KeyError on line 42. How do I fix it?"
```

### 3. Use System Prompts

Tailor the AI's expertise:

```bash
# For code review
consoul chat --system "You are a senior software engineer reviewing code" \
  --file pr.diff "Review this pull request"

# For learning
consoul chat --system "You are a patient teacher explaining to a beginner" \
  "Explain Python decorators"
```

### 4. Iterate

Don't expect perfection on the first try:

```bash
consoul ask "Write a merge sort function"
# Review the output, then:
consoul ask "Add type hints and docstrings"
consoul ask "Add error handling for edge cases"
```

## Common Workflows

### Code Review

```bash
# Review staged changes
git diff --staged | consoul ask --stdin "Review these changes"

# Review specific file
consoul ask --file src/main.py "Code review with focus on performance"
```

### Debugging

```bash
# Debug test failures
pytest 2>&1 | consoul ask --stdin "Why are these tests failing?"

# Explain errors
python app.py 2>&1 | consoul ask --stdin "What's causing this error?"
```

### Documentation

```bash
# Generate docstrings
consoul ask --file api.py "Add Google-style docstrings"

# Write README
consoul ask --glob "*.py" "Write a README.md for this project"
```

### Learning

```bash
# Understand code
consoul ask --file complex.py "Explain this code step by step"

# Learn concepts
consoul ask "Explain async/await in Python with examples"
```

### Refactoring

```bash
# Improve code
consoul ask --file legacy.py "Refactor this code for better readability"

# Extract functions
consoul ask --file monolith.py "Identify functions that should be extracted"
```

## Advanced Features

### Custom Temperature

Control creativity vs. determinism:

```bash
# Deterministic (code generation)
consoul --temperature 0.2 ask "Write a binary search function"

# Creative (brainstorming)
consoul --temperature 0.9 ask "Suggest project names for an AI terminal assistant"
```

### Token Limits

Control response length:

```bash
# Brief response
consoul --max-tokens 200 ask "Summarize Python decorators"

# Detailed response
consoul --max-tokens 2000 ask "Explain Python decorators with examples"
```

### Conversation History

```bash
# List conversations
consoul history list

# Resume conversation
consoul history resume <id>

# Export to markdown
consoul history export <id> --format markdown > conversation.md
```

## Troubleshooting

### API Key Issues

```bash
# Verify API key is set
echo $ANTHROPIC_API_KEY

# Set temporarily
ANTHROPIC_API_KEY=your-key consoul ask "test"

# Set permanently
echo 'export ANTHROPIC_API_KEY="your-key"' >> ~/.zshrc
```

### Rate Limits

If you hit rate limits:

- Switch to a different provider
- Wait and retry
- Use a lower temperature for faster responses
- Reduce max_tokens

### Context Too Large

If your context exceeds limits:

- Be more selective with files
- Use specific line ranges
- Summarize large outputs before piping

## Next Steps

- [Configuration Guide](configuration.md) – Detailed configuration options
- [Usage Examples](usage.md) – More examples and patterns
- [API Reference](../api/index.md) – Package documentation
