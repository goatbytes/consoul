# Integration Guide

Real-world guide for integrating Consoul SDK into your Python projects.

## Quick Integration Checklist

Before integrating Consoul, consider:

- ✅ **Dependencies**: Consoul adds ~19 core dependencies (LangChain ecosystem)
- ✅ **Install Size**: ~200MB+ with all dependencies
- ✅ **Python Version**: Requires Python 3.10+
- ✅ **API Keys**: Need keys for your chosen provider(s)
- ✅ **File System**: Creates `~/.config/consoul/` and `~/.local/share/consoul/`

## Installation for Projects

### As a Project Dependency

Add to your `requirements.txt`:

```txt
consoul>=0.2.2
```

Or `pyproject.toml`:

```toml
[project]
dependencies = [
    "consoul>=0.2.2",
]
```

Or with Poetry:

```bash
poetry add consoul
```

### Virtual Environment (Recommended)

Always use a virtual environment to avoid dependency conflicts:

```bash
# Create venv
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Consoul
pip install consoul
```

## Common Integration Patterns

### 1. Standalone Scripts

Perfect for automation, CLI tools, or one-off scripts:

```python
#!/usr/bin/env python3
"""Analyze code and generate report."""

from consoul import Consoul

def main():
    analyzer = Consoul(
        tools=["grep", "code_search", "read"],
        persist=False  # Don't save conversation history
    )

    result = analyzer.chat("Find all TODO comments and summarize them")
    print(result)

if __name__ == "__main__":
    main()
```

**Why `persist=False`?** Prevents creating conversation history files for one-off scripts.

### 2. Web Services / APIs

For FastAPI, Flask, Django, etc.:

```python
from fastapi import FastAPI
from consoul import Consoul

app = FastAPI()

# Create shared instance (optional)
# Or create per-request for better isolation
code_assistant = Consoul(
    tools=["grep", "code_search"],
    persist=False,  # Don't persist in services
    system_prompt="You are a code assistant API. Be concise."
)

@app.post("/analyze")
async def analyze_code(query: str):
    response = code_assistant.ask(query, show_tokens=True)
    return {
        "response": response.content,
        "tokens": response.tokens,
        "model": response.model
    }
```

**Best Practices for Services:**
- Set `persist=False` to avoid database writes
- Consider creating new `Consoul()` instances per-request for isolation
- Monitor token usage with `console.last_cost`
- Set appropriate timeouts for LLM calls

### 3. Long-Running Applications

For daemons, background workers, or services:

```python
import logging
from consoul import Consoul

logger = logging.getLogger(__name__)

class AIAgent:
    def __init__(self):
        self.console = Consoul(
            tools=["bash", "grep"],
            persist=False,
            temperature=0.3
        )

    def process_task(self, task: str) -> str:
        try:
            result = self.console.chat(task)

            # Log token usage
            cost = self.console.last_cost
            logger.info(
                f"Task completed. "
                f"Tokens: {cost['total_tokens']}, "
                f"Est. cost: ${cost['estimated_cost']:.4f}"
            )

            return result
        except Exception as e:
            logger.error(f"Task failed: {e}")
            raise

    def reset_context(self):
        """Clear conversation history between tasks."""
        self.console.clear()

# Usage
agent = AIAgent()
result = agent.process_task("List Python files")
agent.reset_context()  # Fresh context for next task
```

### 4. Custom Tool Integration

Add your own tools alongside Consoul's built-in tools:

```python
from consoul import Consoul
from langchain_core.tools import tool
import requests

@tool
def get_api_status(service: str) -> str:
    """Check if an API service is online."""
    try:
        response = requests.get(f"https://{service}/health", timeout=5)
        return f"{service} is {'online' if response.ok else 'offline'}"
    except Exception as e:
        return f"{service} is offline: {e}"

# Mix custom tools with built-in tools
console = Consoul(tools=[get_api_status, "bash", "grep"])

# AI can now use your custom tool
console.chat("Check if api.example.com is online")
```

### 5. Multiple Consoul Instances

Use different instances for different purposes:

```python
from consoul import Consoul

# Code reviewer (safe, read-only tools)
reviewer = Consoul(
    tools="safe",
    system_prompt="You are a code reviewer. Find issues.",
    temperature=0.3
)

# Code writer (file editing enabled)
writer = Consoul(
    tools=["create_file", "edit_lines", "bash"],
    system_prompt="You are a code generator. Write clean code.",
    temperature=0.7
)

# Research assistant (web tools only)
researcher = Consoul(
    tools=["web_search", "read_url"],
    system_prompt="You are a research assistant. Cite sources."
)

# Use each for specific tasks
issues = reviewer.chat("Review this file for bugs")
researcher.chat("What are best practices for FastAPI?")
writer.chat("Create a FastAPI endpoint for user auth")
```

## Configuration Management

### Environment Variables

Recommended approach for API keys:

```python
import os
from consoul import Consoul

# Consoul automatically reads from environment
# OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, etc.

console = Consoul(model="gpt-4o")
```

Set in your environment:

```bash
# .env file
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

### Programmatic Configuration

Override settings per-instance:

```python
from consoul import Consoul

console = Consoul(
    model="gpt-4o",
    temperature=0.5,
    system_prompt="Custom prompt",
    api_key="sk-...",  # Override environment variable
)
```

### Profile-Based Configuration

Create `~/.config/consoul/config.yaml`:

```yaml
profiles:
  production:
    model: claude-3-5-sonnet-20241022
    temperature: 0.3

  development:
    model: gpt-4o
    temperature: 0.7

  local:
    model: llama3.2
    provider: ollama
```

Use profiles in code:

```python
from consoul import Consoul

# Use specific profile
console = Consoul(profile="production")

# Override profile settings
console = Consoul(profile="production", temperature=0.5)
```

## Dependency Considerations

### What Consoul Installs

Consoul has ~19 core dependencies:

- **LangChain ecosystem** (langchain, langchain-community, langchain-openai, etc.)
- **AI Providers** (anthropic, openai, google-ai-generativelanguage)
- **Tools** (tiktoken, tree-sitter, grep-ast, duckduckgo-search)
- **Utilities** (pydantic, rich, pyyaml, requests)

### Potential Conflicts

If your project already uses:

- **LangChain**: Ensure version compatibility (Consoul requires langchain>=1.0.7)
- **Pydantic**: Consoul requires pydantic>=2.12.4
- **Tiktoken**: Consoul requires tiktoken>=0.12.0

### Minimal Installation

If you only need the SDK (no TUI):

```bash
pip install consoul  # Core SDK only
```

## Error Handling

### Graceful Degradation

```python
from consoul import Consoul

def safe_chat(query: str) -> str:
    try:
        console = Consoul(persist=False)
        return console.chat(query)
    except ValueError as e:
        # Configuration error
        return f"Configuration error: {e}"
    except Exception as e:
        # API error, network error, etc.
        return f"Error: {e}"

result = safe_chat("Hello")
```

### Timeout Handling

For web services, set timeouts:

```python
import signal
from contextlib import contextmanager

@contextmanager
def timeout(seconds):
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds}s")

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

# Use with timeout
try:
    with timeout(30):
        result = console.chat("Complex query...")
except TimeoutError:
    print("LLM request timed out")
```

## Performance Tips

### 1. Reuse Instances

Creating `Consoul()` instances has overhead. Reuse when possible:

```python
# ❌ Don't do this
def query(text):
    console = Consoul()  # Creates new instance each time
    return console.chat(text)

# ✅ Do this
console = Consoul()

def query(text):
    return console.chat(text)
```

### 2. Disable Persistence for Stateless Operations

```python
# Faster for one-off queries
console = Consoul(persist=False)
```

### 3. Use Appropriate Tools

Only enable tools you need:

```python
# ❌ All tools (slower, more tokens)
console = Consoul(tools=True)

# ✅ Only needed tools (faster)
console = Consoul(tools=["grep", "code_search"])
```

### 4. Monitor Token Usage

```python
console = Consoul()
response = console.chat("Query...")

cost = console.last_cost
print(f"Tokens used: {cost['total_tokens']}")
print(f"Estimated cost: ${cost['estimated_cost']:.4f}")
```

## Security Considerations

### Tool Permissions

Start with minimal permissions:

```python
# ✅ Safe (read-only)
console = Consoul(tools="safe")

# ⚠️ Caution (file operations)
console = Consoul(tools="caution")

# ⚠️ Dangerous (destructive operations)
console = Consoul(tools="dangerous")
```

### API Key Management

Never hardcode API keys:

```python
# ❌ DON'T
console = Consoul(api_key="sk-hardcoded-key")

# ✅ DO - Use environment variables
console = Consoul()  # Reads from env

# ✅ DO - Load from secrets manager
import boto3
secrets = boto3.client('secretsmanager')
api_key = secrets.get_secret_value(SecretId='openai-key')['SecretString']
console = Consoul(api_key=api_key)
```

### Input Validation

Sanitize user input before passing to AI:

```python
def sanitize_input(text: str) -> str:
    # Remove potential prompt injection attempts
    text = text.replace("Ignore previous instructions", "")
    text = text.strip()[:1000]  # Limit length
    return text

user_query = sanitize_input(user_input)
result = console.chat(user_query)
```

## Testing

### Unit Tests

Mock Consoul for testing:

```python
from unittest.mock import Mock, patch
import pytest

def process_query(query: str) -> str:
    from consoul import Consoul
    console = Consoul(persist=False)
    return console.chat(query)

def test_process_query():
    with patch('consoul.Consoul') as MockConsoul:
        mock_console = Mock()
        mock_console.chat.return_value = "Mocked response"
        MockConsoul.return_value = mock_console

        result = process_query("test")
        assert result == "Mocked response"
```

### Integration Tests

Test with real API (use test keys):

```python
import pytest
from consoul import Consoul

@pytest.mark.integration
def test_real_chat():
    console = Consoul(
        model="gpt-4o-mini",  # Cheaper model for testing
        persist=False
    )
    result = console.chat("What is 2+2?")
    assert "4" in result
```

## Troubleshooting

### Common Issues

**1. "No API key found"**
```python
# Solution: Set environment variable
export ANTHROPIC_API_KEY="sk-ant-..."
```

**2. "ModuleNotFoundError: No module named 'rich'"**
```bash
# Solution: Upgrade to v0.2.1+
pip install --upgrade consoul
```

**3. "Profile 'xyz' not found"**
```python
# Solution: Use valid profile or create config
consoul init
```

**4. Large dependency footprint**
```bash
# Solution: Use virtual environment
python3 -m venv venv
source venv/bin/activate
pip install consoul
```

## Examples Repository

See [GitHub examples](https://github.com/goatbytes/consoul/tree/main/examples) for:

- FastAPI integration
- Django integration
- Background worker example
- Custom tool examples
- Testing examples

## Next Steps

- [Tutorial](tutorial.md) - Step-by-step SDK learning
- [Tools Documentation](tools.md) - Master built-in tools
- [API Reference](reference.md) - Complete API docs
- [Building Agents](agents.md) - Create specialized agents

## Support

- **[GitHub Issues](https://github.com/goatbytes/consoul/issues)** - Report bugs
- **[Discussions](https://github.com/goatbytes/consoul/discussions)** - Ask questions
- **[Discord](https://discord.gg/consoul)** - Community chat

---

**Ready to integrate?** Start with a [minimal example](#1-standalone-scripts) and expand from there.
