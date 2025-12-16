# Usage

Common usage patterns and examples for Consoul.

## Basic Usage

### Simple Query

```bash
consoul ask "How do I reverse a string in Python?"
```

### Interactive Mode

```bash
consoul tui
```

## File Context

### Single File

```bash
consoul ask --file main.py "Explain this code"
```

### Multiple Files

```bash
consoul ask \
  --file app.py \
  --file config.yaml \
  --file README.md \
  "How is this project structured?"
```

### Pattern Matching

```bash
# All Python files in current directory
consoul ask --glob "*.py" "Summarize this codebase"

# Recursive search
consoul ask --glob "**/*.py" "What does this project do?"

# Multiple patterns
consoul ask --glob "src/**/*.py" --glob "tests/**/*.py" "Analyze test coverage"
```

## Pipeline Integration

### Command Output

```bash
# Git status
git status | consoul ask --stdin "What should I commit?"

# Directory listing
ls -la | consoul ask --stdin "What are these files?"

# Log analysis
tail -n 100 app.log | consoul ask --stdin "Any errors in these logs?"
```

### Error Debugging

```bash
# Python errors
python script.py 2>&1 | consoul ask --stdin "What's wrong?"

# Test failures
pytest 2>&1 | consoul ask --stdin "Why are these tests failing?"

# Build errors
make 2>&1 | consoul ask --stdin "How do I fix these build errors?"
```

## Development Workflows

### Code Review

```bash
# Review staged changes
git diff --staged | consoul ask --stdin \
  --system "You are a senior code reviewer" \
  "Review these changes"

# Review specific commit
git show HEAD | consoul ask --stdin "Review this commit"

# Review pull request diff
gh pr diff 123 | consoul ask --stdin "Review this PR"
```

### Commit Messages

```bash
# Generate conventional commit message
git diff --staged | consoul --temperature 0.3 ask --stdin \
  "Generate a conventional commit message for these changes"

# Or use it directly
git diff --staged | consoul ask --stdin "Generate commit message" \
  | git commit -F -
```

### Documentation

```bash
# Generate docstrings
consoul ask --file module.py \
  --system "Add Google-style docstrings" \
  "Add comprehensive docstrings to all functions"

# Generate README
consoul ask --glob "*.py" --file setup.py \
  "Write a comprehensive README.md for this project"

# API documentation
consoul ask --glob "api/**/*.py" \
  "Generate API documentation in markdown format"
```

### Testing

```bash
# Generate tests
consoul ask --file app.py \
  "Write pytest tests for this module with fixtures"

# Explain test failures
pytest -v 2>&1 | consoul ask --stdin \
  "Explain why these tests are failing and how to fix them"

# Test coverage analysis
coverage report | consoul ask --stdin \
  "What areas need more test coverage?"
```

### Refactoring

```bash
# General refactoring
consoul ask --file legacy.py \
  --system "You are a refactoring expert" \
  "Refactor this code for better readability and maintainability"

# Extract functions
consoul ask --file large_file.py \
  "Identify functions that should be extracted and suggest a module structure"

# Type hints
consoul ask --file untyped.py \
  "Add comprehensive type hints to this module"
```

## Learning and Exploration

### Understanding Code

```bash
# Explain complex code
consoul ask --file complex.py \
  --system "You are a patient teacher" \
  "Explain this code step by step"

# Understand project structure
consoul ask --glob "**/*.py" --file setup.py \
  "Explain the architecture of this project"

# Learn from examples
consoul ask --file example.py \
  "Explain how this works and suggest improvements"
```

### Learning Concepts

```bash
# With examples
consoul ask "Explain Python decorators with 3 practical examples"

# Step by step
consoul ask "Explain async/await in Python step by step with examples"

# Comparisons
consoul ask "Compare and contrast lists vs tuples in Python"
```

## Command Line Help

### Understanding Commands

```bash
# Explain complex commands
consoul ask "Explain: find . -type f -name '*.py' -exec grep -l 'TODO' {} \;"

# Get command suggestions
consoul ask "How do I find all files larger than 100MB modified in the last week?"

# Understand output
ps aux | consoul ask --stdin "Explain this process list"
```

### Writing Scripts

```bash
# Generate bash script
consoul ask "Write a bash script to backup a directory with timestamp"

# Generate Python script
consoul ask "Write a Python script to rename files in bulk"

# Shell one-liners
consoul ask "Give me a one-liner to count lines of code in all Python files"
```

## Advanced Patterns

### Custom System Prompts

```bash
# Code review persona
consoul ask --system "You are a senior software engineer specializing in Python. \
Focus on security, performance, and maintainability." \
--file app.py "Review this code"

# Teaching persona
consoul ask --system "You are a patient teacher explaining concepts to beginners. \
Use simple language and provide examples." \
"Explain Python decorators"

# Pair programming persona
consoul ask --system "You are an experienced pair programming partner. \
Ask clarifying questions and suggest alternatives." \
--file solution.py "Help me improve this implementation"
```

### Temperature Control

```bash
# Deterministic (code generation, factual answers)
consoul --temperature 0.2 ask \
  "Write a function to validate email addresses"

# Balanced (default for most tasks)
consoul --temperature 0.7 ask \
  "How should I structure this project?"

# Creative (brainstorming, naming)
consoul --temperature 0.9 ask \
  "Suggest creative names for an AI terminal assistant"
```

### Response Length Control

```bash
# Brief summary
consoul --max-tokens 200 ask \
  "Summarize Python decorators in one paragraph"

# Detailed explanation
consoul --max-tokens 2000 ask \
  "Provide a comprehensive guide to Python decorators with examples"
```

## Project-Specific Workflows

### Python Projects

```bash
# Setup new project
consoul ask "Create a Python project structure for a CLI tool with poetry"

# Dependency analysis
poetry show --tree | consoul ask --stdin "Analyze these dependencies"

# Virtual environment help
consoul ask "How do I manage virtual environments with pyenv?"
```

### JavaScript/TypeScript

```bash
# Package.json analysis
consoul ask --file package.json "Explain these dependencies and scripts"

# TypeScript errors
tsc 2>&1 | consoul ask --stdin "Help me fix these TypeScript errors"

# React component
consoul ask --file Component.tsx "Review this React component"
```

### Infrastructure

```bash
# Dockerfile review
consoul ask --file Dockerfile "Review and optimize this Dockerfile"

# Kubernetes config
consoul ask --file deployment.yaml "Review this Kubernetes deployment"

# CI/CD
consoul ask --file .github/workflows/ci.yml "Review this GitHub Actions workflow"
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
alias ask="consoul ask"
alias explain="consoul ask --stdin"
alias review="consoul ask --file"

# Specialized
alias commit-msg="git diff --staged | consoul --temperature 0.3 ask --stdin 'Generate conventional commit message'"
alias test-help="pytest 2>&1 | consoul ask --stdin 'Explain test failures'"
alias code-review="git diff --staged | consoul ask --stdin --system 'You are a senior code reviewer' 'Review these changes'"
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
  git diff "$@" | consoul ask --stdin \
    --system "You are a senior code reviewer" \
    "Review these changes"
}

# Explain command
explain-cmd() {
  consoul ask "Explain this command: $*"
}

# Generate tests
gen-tests() {
  consoul ask --file "$1" \
    "Generate comprehensive pytest tests for this module"
}
```

## Tips and Best Practices

### Provide Context

```bash
# ✗ Not enough context
consoul ask "Fix this"

# ✓ Good context
consoul ask --file broken.py --file tests/test_broken.py \
  "This function raises KeyError on line 42 when processing empty input. How do I fix it?"
```

### Be Specific

```bash
# ✗ Too vague
consoul ask "Make this better"

# ✓ Specific request
consoul ask --file app.py \
  "Refactor this function to: 1) Add type hints, 2) Extract helper functions, 3) Add error handling"
```

### Iterate

```bash
# Start simple
consoul ask "Write a function to merge sorted lists"

# Then refine (in same conversation or new query)
consoul ask "Add type hints and docstrings"
consoul ask "Add error handling for invalid inputs"
consoul ask "Optimize for large lists"
```

### Use Appropriate Temperature

```bash
# Low temperature for factual/deterministic tasks
consoul --temperature 0.2 ask "Write a binary search implementation"

# High temperature for creative tasks
consoul --temperature 0.9 ask "Brainstorm project name ideas"
```

## Troubleshooting

### Rate Limits

```bash
# Switch provider
consoul ask --provider google "Your question"

# Reduce token usage
consoul --max-tokens 500 ask "Brief summary please"
```

### Context Too Large

```bash
# Be selective with files
consoul ask --file main.py "Explain this" # Instead of --glob "**/*.py"

# Pipe summary instead of full output
git log --oneline -20 | consoul ask --stdin "Summarize recent work"
```

### API Errors

```bash
# Enable debug logging
consoul config set logging.level DEBUG
consoul ask "test"

# Check logs
tail -f ~/.config/consoul/consoul.log
```

## Next Steps

- [Configuration](configuration.md) – Customize Consoul settings
- [Getting Started](getting-started.md) – Basic concepts
- [API Reference](../api/index.md) – Package documentation
