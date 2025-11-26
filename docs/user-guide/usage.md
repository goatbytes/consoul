# Usage

Common usage patterns and examples for Consoul.

## Basic Usage

### Simple Query

```bash
consoul chat "How do I reverse a string in Python?"
```

### Interactive Mode

```bash
consoul tui
```

## File Context

### Single File

```bash
consoul chat --file main.py "Explain this code"
```

### Multiple Files

```bash
consoul chat \
  --file app.py \
  --file config.yaml \
  --file README.md \
  "How is this project structured?"
```

### Pattern Matching

```bash
# All Python files in current directory
consoul chat --glob "*.py" "Summarize this codebase"

# Recursive search
consoul chat --glob "**/*.py" "What does this project do?"

# Multiple patterns
consoul chat --glob "src/**/*.py" --glob "tests/**/*.py" "Analyze test coverage"
```

## Pipeline Integration

### Command Output

```bash
# Git status
git status | consoul chat --stdin "What should I commit?"

# Directory listing
ls -la | consoul chat --stdin "What are these files?"

# Log analysis
tail -n 100 app.log | consoul chat --stdin "Any errors in these logs?"
```

### Error Debugging

```bash
# Python errors
python script.py 2>&1 | consoul chat --stdin "What's wrong?"

# Test failures
pytest 2>&1 | consoul chat --stdin "Why are these tests failing?"

# Build errors
make 2>&1 | consoul chat --stdin "How do I fix these build errors?"
```

## Development Workflows

### Code Review

```bash
# Review staged changes
git diff --staged | consoul chat --stdin \
  --system "You are a senior code reviewer" \
  "Review these changes"

# Review specific commit
git show HEAD | consoul chat --stdin "Review this commit"

# Review pull request diff
gh pr diff 123 | consoul chat --stdin "Review this PR"
```

### Commit Messages

```bash
# Generate conventional commit message
git diff --staged | consoul chat --stdin \
  --temperature 0.3 \
  "Generate a conventional commit message for these changes"

# Or use it directly
git diff --staged | consoul chat --stdin "Generate commit message" \
  | git commit -F -
```

### Documentation

```bash
# Generate docstrings
consoul chat --file module.py \
  --system "Add Google-style docstrings" \
  "Add comprehensive docstrings to all functions"

# Generate README
consoul chat --glob "*.py" --file setup.py \
  "Write a comprehensive README.md for this project"

# API documentation
consoul chat --glob "api/**/*.py" \
  "Generate API documentation in markdown format"
```

### Testing

```bash
# Generate tests
consoul chat --file app.py \
  "Write pytest tests for this module with fixtures"

# Explain test failures
pytest -v 2>&1 | consoul chat --stdin \
  "Explain why these tests are failing and how to fix them"

# Test coverage analysis
coverage report | consoul chat --stdin \
  "What areas need more test coverage?"
```

### Refactoring

```bash
# General refactoring
consoul chat --file legacy.py \
  --system "You are a refactoring expert" \
  "Refactor this code for better readability and maintainability"

# Extract functions
consoul chat --file large_file.py \
  "Identify functions that should be extracted and suggest a module structure"

# Type hints
consoul chat --file untyped.py \
  "Add comprehensive type hints to this module"
```

## Learning and Exploration

### Understanding Code

```bash
# Explain complex code
consoul chat --file complex.py \
  --system "You are a patient teacher" \
  "Explain this code step by step"

# Understand project structure
consoul chat --glob "**/*.py" --file setup.py \
  "Explain the architecture of this project"

# Learn from examples
consoul chat --file example.py \
  "Explain how this works and suggest improvements"
```

### Learning Concepts

```bash
# With examples
consoul chat "Explain Python decorators with 3 practical examples"

# Step by step
consoul chat "Explain async/await in Python step by step with examples"

# Comparisons
consoul chat "Compare and contrast lists vs tuples in Python"
```

## Command Line Help

### Understanding Commands

```bash
# Explain complex commands
consoul chat "Explain: find . -type f -name '*.py' -exec grep -l 'TODO' {} \;"

# Get command suggestions
consoul chat "How do I find all files larger than 100MB modified in the last week?"

# Understand output
ps aux | consoul chat --stdin "Explain this process list"
```

### Writing Scripts

```bash
# Generate bash script
consoul chat "Write a bash script to backup a directory with timestamp"

# Generate Python script
consoul chat "Write a Python script to rename files in bulk"

# Shell one-liners
consoul chat "Give me a one-liner to count lines of code in all Python files"
```

## Advanced Patterns

### Custom System Prompts

```bash
# Code review persona
consoul chat --system "You are a senior software engineer specializing in Python. \
Focus on security, performance, and maintainability." \
--file app.py "Review this code"

# Teaching persona
consoul chat --system "You are a patient teacher explaining concepts to beginners. \
Use simple language and provide examples." \
"Explain Python decorators"

# Pair programming persona
consoul chat --system "You are an experienced pair programming partner. \
Ask clarifying questions and suggest alternatives." \
--file solution.py "Help me improve this implementation"
```

### Temperature Control

```bash
# Deterministic (code generation, factual answers)
consoul chat --temperature 0.2 \
  "Write a function to validate email addresses"

# Balanced (default for most tasks)
consoul chat --temperature 0.7 \
  "How should I structure this project?"

# Creative (brainstorming, naming)
consoul chat --temperature 0.9 \
  "Suggest creative names for an AI terminal assistant"
```

### Response Length Control

```bash
# Brief summary
consoul chat --max-tokens 200 \
  "Summarize Python decorators in one paragraph"

# Detailed explanation
consoul chat --max-tokens 2000 \
  "Provide a comprehensive guide to Python decorators with examples"
```

## Project-Specific Workflows

### Python Projects

```bash
# Setup new project
consoul chat "Create a Python project structure for a CLI tool with poetry"

# Dependency analysis
poetry show --tree | consoul chat --stdin "Analyze these dependencies"

# Virtual environment help
consoul chat "How do I manage virtual environments with pyenv?"
```

### JavaScript/TypeScript

```bash
# Package.json analysis
consoul chat --file package.json "Explain these dependencies and scripts"

# TypeScript errors
tsc 2>&1 | consoul chat --stdin "Help me fix these TypeScript errors"

# React component
consoul chat --file Component.tsx "Review this React component"
```

### Infrastructure

```bash
# Dockerfile review
consoul chat --file Dockerfile "Review and optimize this Dockerfile"

# Kubernetes config
consoul chat --file deployment.yaml "Review this Kubernetes deployment"

# CI/CD
consoul chat --file .github/workflows/ci.yml "Review this GitHub Actions workflow"
```

## Conversation Management

### List Conversations

```bash
consoul history list
```

### Resume Conversation

```bash
consoul history resume <conversation-id>
```

### Export Conversation

```bash
# Export to markdown
consoul history export <conversation-id> --format markdown > conversation.md

# Export to JSON
consoul history export <conversation-id> --format json > conversation.json
```

### Delete Conversation

```bash
consoul history delete <conversation-id>
```

## Shell Integration

### Aliases

Add to `~/.zshrc` or `~/.bashrc`:

```bash
# Quick access
alias ask="consoul chat"
alias explain="consoul chat --stdin"
alias review="consoul chat --file"

# Specialized
alias commit-msg="git diff --staged | consoul chat --stdin --temperature 0.3 'Generate conventional commit message'"
alias test-help="pytest 2>&1 | consoul chat --stdin 'Explain test failures'"
alias code-review="git diff --staged | consoul chat --stdin --system 'You are a senior code reviewer' 'Review these changes'"
```

Usage:

```bash
ask "How do I use sed to replace text?"
cat error.log | explain "What's causing these errors?"
review main.py "Any improvements?"
```

### Functions

Add to shell config:

```bash
# Review git diff
gdiff-review() {
  git diff "$@" | consoul chat --stdin \
    --system "You are a senior code reviewer" \
    "Review these changes"
}

# Explain command
explain-cmd() {
  consoul chat "Explain this command: $*"
}

# Generate tests
gen-tests() {
  consoul chat --file "$1" \
    "Generate comprehensive pytest tests for this module"
}
```

## Tips and Best Practices

### Provide Context

```bash
# ✗ Not enough context
consoul chat "Fix this"

# ✓ Good context
consoul chat --file broken.py --file tests/test_broken.py \
  "This function raises KeyError on line 42 when processing empty input. How do I fix it?"
```

### Be Specific

```bash
# ✗ Too vague
consoul chat "Make this better"

# ✓ Specific request
consoul chat --file app.py \
  "Refactor this function to: 1) Add type hints, 2) Extract helper functions, 3) Add error handling"
```

### Iterate

```bash
# Start simple
consoul chat "Write a function to merge sorted lists"

# Then refine (in same conversation or new query)
consoul chat "Add type hints and docstrings"
consoul chat "Add error handling for invalid inputs"
consoul chat "Optimize for large lists"
```

### Use Appropriate Temperature

```bash
# Low temperature for factual/deterministic tasks
consoul chat --temperature 0.2 "Write a binary search implementation"

# High temperature for creative tasks
consoul chat --temperature 0.9 "Brainstorm project name ideas"
```

## Troubleshooting

### Rate Limits

```bash
# Switch provider
consoul chat --provider google "Your question"

# Reduce token usage
consoul chat --max-tokens 500 "Brief summary please"
```

### Context Too Large

```bash
# Be selective with files
consoul chat --file main.py "Explain this" # Instead of --glob "**/*.py"

# Pipe summary instead of full output
git log --oneline -20 | consoul chat --stdin "Summarize recent work"
```

### API Errors

```bash
# Enable debug logging
consoul config set logging.level DEBUG
consoul chat "test"

# Check logs
tail -f ~/.config/consoul/consoul.log
```

## Next Steps

- [Configuration](configuration.md) – Customize Consoul settings
- [Getting Started](getting-started.md) – Basic concepts
- [API Reference](../api/index.md) – Package documentation
