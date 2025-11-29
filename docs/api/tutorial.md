# SDK Tutorial

Learn how to integrate Consoul's AI capabilities into your Python applications through hands-on examples.

!!! tip "Learning Philosophy"
    You'll learn fastest by writing and running code. Each example is ready to copy and run immediately. Type it out or copy it - then experiment!

## Installation

Install Consoul in your Python project:

```bash
# Basic installation
pip install consoul

# With all features (MLX, Ollama support)
pip install consoul[all]

# For development
pip install consoul[dev]
```

**Requirements:**
- Python 3.10+
- API keys for your chosen provider (OpenAI, Anthropic, Google, or Ollama)

**Setup API Keys:**

Set your API keys via environment variables:

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="..."
```

Or initialize a configuration file:

```bash
consoul init
```

This creates `~/.config/consoul/config.yaml` with default settings.

## First Steps

### Your First Chat

The simplest possible AI chat in 3 lines:

```python
from consoul import Consoul

console = Consoul()
print(console.chat("What is 2+2?"))
```

**Output:**
```
4
```

That's it! Consoul automatically:

- Loads your configuration from `~/.config/consoul/`
- Uses your default profile's model (e.g., `claude-3-5-sonnet-20241022`)
- Handles API authentication via environment variables

### Getting Response Metadata

Want more than just the text? Use `.ask()` for structured responses:

```python
from consoul import Consoul

console = Consoul()
response = console.ask("Explain Python decorators", show_tokens=True)

print(response.content)
print(f"\nModel: {response.model}")
print(f"Tokens: {response.tokens}")
```

**Output:**
```
Decorators are functions that modify other functions...

Model: claude-3-5-sonnet-20241022
Tokens: 127
```

## Multi-Turn Conversations

Consoul maintains conversation history automatically:

```python
from consoul import Consoul

console = Consoul()

# First message
console.chat("My name is Alice")

# Ask about programming
console.chat("What programming language should I learn?")

# Reference earlier context
response = console.chat("What's my name?")
print(response)  # "Your name is Alice."
```

The AI remembers your entire conversation. Clear it when starting fresh:

```python
console.clear()  # Removes history, keeps system prompt
console.chat("What's my name?")  # "I don't have that information"
```

## Choosing Models

Override the default model:

```python
from consoul import Consoul

# Use GPT-4o
console = Consoul(model="gpt-4o")
console.chat("Hello!")

# Use Gemini
console = Consoul(model="gemini-2.0-flash-exp")
console.chat("Hello!")

# Use local Ollama model
console = Consoul(model="llama3.2")
console.chat("Hello!")
```

Consoul auto-detects the provider from the model name.

## Custom Configuration

Control temperature, system prompts, and more:

```python
from consoul import Consoul

console = Consoul(
    model="gpt-4o",
    temperature=0.7,  # 0.0 = deterministic, 2.0 = creative
    system_prompt="You are a helpful Python expert who gives concise answers.",
    persist=True  # Save conversation history (default)
)

response = console.chat("How do I sort a list?")
print(response)
```

## Adding Tools

Tools let the AI perform actions - search files, execute commands, read URLs, and more.

### Enable All Tools

```python
from consoul import Consoul

console = Consoul(tools=True)  # All 13 built-in tools
console.chat("List Python files in the current directory")
```

The AI can now use tools like `bash_execute`, `grep_search`, `code_search`, etc.

!!! warning "Tool Security"
    Tools can modify your system (create/delete files, run commands). Start with `tools="safe"` for read-only operations.

### Safe Tools Only

For untrusted AI interactions, use read-only tools:

```python
from consoul import Consoul

console = Consoul(tools="safe")  # Only SAFE risk level
console.chat("Search for TODO comments in Python files")
```

Safe tools include:
- `grep` - Search file contents
- `code_search` - Find code patterns
- `read_file` - Read file contents
- `web_search` - Search the web
- `read_url` - Fetch web pages

### Tool Categories

Filter tools by category:

```python
from consoul import Consoul

# Only search tools
console = Consoul(tools="search")
console.chat("Find all functions named 'calculate'")

# Only web tools
console = Consoul(tools="web")
console.chat("What's the latest Python release?")

# Multiple categories
console = Consoul(tools=["search", "web"])
console.chat("Search docs and check online")
```

Available categories: `search`, `file-edit`, `web`, `execute`

### Specific Tools

Choose exactly which tools to enable:

```python
from consoul import Consoul

# Bash and grep only
console = Consoul(tools=["bash", "grep"])
console.chat("List files and search for 'TODO'")

# File editing tools
console = Consoul(tools=["create_file", "edit_lines", "read"])
console.chat("Create a new README.md file")
```

## Risk Levels Explained

Tools are classified by risk:

| Risk Level | Description | Examples |
|------------|-------------|----------|
| **SAFE** | Read-only operations | `grep`, `code_search`, `read_file`, `web_search` |
| **CAUTION** | File operations, command execution | `create_file`, `edit_file`, `bash` (safe commands) |
| **DANGEROUS** | Destructive operations | `delete_file`, `bash` (rm, kill, etc.) |

Use risk levels to filter tools:

```python
from consoul import Consoul

# Safe tools only (read-only)
console = Consoul(tools="safe")

# Safe + Caution tools (file operations)
console = Consoul(tools="caution")

# All tools including dangerous (be careful!)
console = Consoul(tools="dangerous")
```

## Custom Tools

Create your own tools using LangChain's `@tool` decorator:

```python
from consoul import Consoul
from langchain_core.tools import tool

@tool
def calculate_fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number.

    Args:
        n: Position in Fibonacci sequence (1-indexed)
    """
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

# Add custom tool alongside built-in tools
console = Consoul(tools=[calculate_fibonacci, "bash", "grep"])
console.chat("What's the 15th Fibonacci number? Use the tool.")
```

**Output:**
```
The 15th Fibonacci number is 610.
```

The AI automatically discovers your tool, reads its docstring, and calls it with the right arguments.

### Tool Requirements

Custom tools must:

1. Be decorated with `@tool`
2. Have a descriptive docstring (the AI reads this!)
3. Use type hints for parameters
4. Return a string or JSON-serializable value

```python
@tool
def search_database(query: str, limit: int = 10) -> str:
    """Search the product database.

    Args:
        query: Search query string
        limit: Maximum results to return (default: 10)

    Returns:
        JSON string with search results
    """
    # Your implementation
    results = db.search(query, limit=limit)
    return json.dumps(results)
```

## Tool Discovery

Store custom tools in `.consoul/tools/` for automatic discovery:

```
your_project/
├── .consoul/
│   └── tools/
│       ├── database.py      # @tool decorated functions
│       ├── api_client.py    # @tool decorated functions
│       └── helpers.py       # @tool decorated functions
├── main.py
└── README.md
```

Enable discovery:

```python
from consoul import Consoul

# Discover tools from .consoul/tools/
console = Consoul(discover_tools=True)

# Combine with built-in tools
console = Consoul(tools=["bash", "grep"], discover_tools=True)

# Only discovered tools (no built-in)
console = Consoul(tools=False, discover_tools=True)
```

Discovered tools default to `RiskLevel.CAUTION` for safety.

## Session Introspection

Monitor your AI usage:

```python
from consoul import Consoul

console = Consoul(model="gpt-4o", tools=True)
console.chat("Hello!")

# View settings
print(console.settings)
# {'model': 'gpt-4o', 'profile': 'default', 'tools_enabled': True, ...}

# Check last request
print(console.last_request)
# {'message': 'Hello!', 'model': 'gpt-4o', 'messages_count': 2, ...}

# Estimate costs (rough approximation)
print(console.last_cost)
# {'input_tokens': 87, 'output_tokens': 12, 'estimated_cost': 0.000441, ...}
# Note: This is a rough estimate. Use provider dashboards for exact costs.
```

## Error Handling

Handle API errors gracefully:

```python
from consoul import Consoul

console = Consoul()

try:
    response = console.chat("Hello!")
    print(response)
except Exception as e:
    print(f"Error: {e}")
    # Handle rate limits, API errors, network issues, etc.
```

Common errors:
- **Authentication**: Missing API keys
- **Rate Limits**: Too many requests
- **Network**: Connection failures
- **Tool Execution**: Tool-specific errors

## Async Support

For async applications, use standard Python async patterns:

```python
import asyncio
from consoul import Consoul

async def main():
    console = Consoul(model="claude-3-5-sonnet-20241022")

    # Consoul's .chat() is synchronous, but you can run it in executor
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        console.chat,
        "Explain async/await"
    )
    print(response)

asyncio.run(main())
```

For true async streaming, use the underlying `ChatManager` API (see API Reference).

## Best Practices

### Security
- **Start with `tools="safe"`** for untrusted AI interactions
- **Use version control (git)** when enabling file-edit tools
- **Principle of least privilege**: Only grant necessary tools
- **Review tool approvals**: Check what the AI wants to do

### Performance
- **Reuse Consoul instances**: Don't create new ones per message
- **Use `console.clear()`**: When starting unrelated conversations
- **Monitor `console.last_cost`**: Track token usage and costs
- **Choose appropriate models**: GPT-4o-mini vs GPT-4o vs Claude

### Development
- **Start simple**: Basic chat first, then add tools
- **Test custom tools**: Verify they work before giving to AI
- **Read tool docstrings**: The AI reads them too!
- **Use descriptive system prompts**: Guide the AI's behavior

## Next Steps

- **[Building Agents](agents.md)** - Create specialized AI agents for complex tasks
- **[Tools Deep Dive](tools.md)** - Learn about all 13 built-in tools
- **[API Reference](reference.md)** - Complete API documentation

## Example Projects

### Code Search Assistant

```python
from consoul import Consoul

console = Consoul(
    tools=["grep", "code_search", "read"],
    system_prompt="You are a code search assistant. Help find code patterns."
)

console.chat("Find all TODO comments in Python files")
console.chat("Show me the implementation of the User class")
console.chat("Where is the database connection configured?")
```

### File Organizer

```python
from consoul import Consoul

console = Consoul(
    tools=["bash", "create_file", "edit_lines"],
    system_prompt="You are a file organization assistant."
)

console.chat("List all .txt files in Downloads/")
console.chat("Create a folder structure for a Python project")
console.chat("Move all PDFs to Documents/PDFs/")
```

### Web Research Bot

```python
from consoul import Consoul

console = Consoul(
    tools=["web_search", "read_url", "wikipedia"],
    system_prompt="You are a research assistant. Cite your sources."
)

console.chat("What's the latest on Python 3.13 release?")
console.chat("Compare React vs Vue.js in 2024")
console.chat("Summarize the Wikipedia article on quantum computing")
```

Start building! 🚀
