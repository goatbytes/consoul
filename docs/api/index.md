# API Reference

API documentation for the Consoul package.

## Package Overview

Consoul provides a Python API for integrating AI-powered terminal assistance into your own applications.

## Installation

```bash
pip install consoul
```

## Quick Example

```python
# Example code will be added once the implementation is complete
# This is a placeholder for the API documentation structure
```

## Core Modules

The Consoul package will provide the following modules:

### Main Interface

- **consoul.Consoul** - Main class for interacting with AI providers
- **consoul.Provider** - Enumeration of supported AI providers

### Configuration

- **consoul.config** - Configuration management and settings

### AI Integration

- **consoul.ai** - AI provider integrations via LangChain

### Terminal UI

- **consoul.tui** - Textual-based terminal UI components

### Utilities

- **consoul.utils** - Helper functions and utilities

*Full API documentation will be auto-generated once the implementation is complete.*

## Usage Examples

### Basic Chat

```python
from consoul import Consoul, Provider

# Initialize
consoul = Consoul(provider=Provider.ANTHROPIC)

# Single message
response = consoul.chat("What is Python?")
print(response.content)
```

### With Context

```python
# Include file context
response = consoul.chat(
    message="Review this code",
    files=["app.py", "utils.py"]
)

# Include text context
response = consoul.chat(
    message="Explain this error",
    context="KeyError: 'username' on line 42"
)
```

### Streaming Responses

```python
# Stream response chunks
for chunk in consoul.chat_stream("Write a haiku about Python"):
    print(chunk.content, end="", flush=True)
print()  # Newline at end
```

### Conversation History

```python
# Multi-turn conversation
consoul.chat("My name is Alice")
consoul.chat("What programming language should I learn?")
response = consoul.chat("What's my name?")
# Response: "Your name is Alice."

# Clear history
consoul.clear_history()
```

### Custom Configuration

```python
from consoul import Consoul, Provider, Config

# Custom config
config = Config(
    provider=Provider.OPENAI,
    model="gpt-4",
    temperature=0.7,
    max_tokens=2048
)

consoul = Consoul(config=config)
```

### Error Handling

```python
from consoul import Consoul, ConsoulError, RateLimitError

try:
    response = consoul.chat("Hello")
except RateLimitError:
    print("Rate limit exceeded, try again later")
except ConsoulError as e:
    print(f"Error: {e}")
```

## Advanced Usage

### Custom System Prompts

```python
response = consoul.chat(
    message="Review this code",
    system="You are a senior Python developer specializing in code review",
    files=["app.py"]
)
```

### Provider-Specific Options

```python
# Anthropic-specific
response = consoul.chat(
    "Hello",
    provider_options={
        "top_p": 0.9,
        "top_k": 40
    }
)
```

### Async Support

```python
import asyncio
from consoul import AsyncConsoul

async def main():
    consoul = AsyncConsoul(provider=Provider.ANTHROPIC)
    response = await consoul.chat("Hello")
    print(response.content)

asyncio.run(main())
```

### Conversation Management

```python
# Save conversation
conversation_id = consoul.save_conversation("My first chat")

# Load conversation
consoul.load_conversation(conversation_id)

# List conversations
conversations = consoul.list_conversations()
for conv in conversations:
    print(f"{conv.id}: {conv.title}")
```

## Type Hints

Consoul is fully typed with mypy support:

```python
from consoul import Consoul, Response
from typing import Iterator

def chat_with_files(
    consoul: Consoul,
    message: str,
    files: list[str]
) -> Response:
    return consoul.chat(message, files=files)

def stream_response(
    consoul: Consoul,
    message: str
) -> Iterator[Response]:
    return consoul.chat_stream(message)
```

## CLI Integration

Use Consoul programmatically from the CLI:

```python
import sys
from consoul import Consoul

def main():
    consoul = Consoul()
    message = " ".join(sys.argv[1:])
    response = consoul.chat(message)
    print(response.content)

if __name__ == "__main__":
    main()
```

## Testing

Mock Consoul for testing:

```python
from unittest.mock import Mock, patch
from consoul import Consoul, Response

def test_chat():
    with patch('consoul.Consoul.chat') as mock_chat:
        mock_chat.return_value = Response(
            content="Mocked response",
            model="test-model"
        )

        consoul = Consoul()
        response = consoul.chat("test")

        assert response.content == "Mocked response"
        mock_chat.assert_called_once_with("test")
```

## Next Steps

- [User Guide](../user-guide/getting-started.md) – Learn to use Consoul
- [Configuration](../user-guide/configuration.md) – Configure Consoul
- [GitHub](https://github.com/goatbytes/consoul) – Source code and examples
