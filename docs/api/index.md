# SDK Overview

Build AI-powered applications with the Consoul SDK - a simple, powerful Python library for integrating language models and tool calling into your projects.

## Why Consoul SDK?

**🚀 Simple**: 3 lines to add AI chat to any Python app

**🛠️ Powerful**: 13 built-in tools for file operations, web search, and command execution

**🔧 Flexible**: Support for OpenAI, Anthropic, Google, and local Ollama models

**🔒 Secure**: Risk-based tool approval and permission system

**📦 Batteries Included**: Conversation history, token tracking, cost estimation

## Quick Start

### Installation

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

```bash
# Set via environment variables
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="..."

# Or initialize configuration file
consoul init
```

### Your First Chat (3 Lines)

```python
from consoul import Consoul

console = Consoul()
print(console.chat("What is 2+2?"))  # → "4"
```

Done! Consoul automatically:
- Loads your configuration
- Handles API authentication
- Manages conversation history

### Add Tools (File Operations, Web Search, etc.)

```python
from consoul import Consoul

console = Consoul(tools=True)  # Enable all built-in tools
console.chat("List Python files in the current directory")
```

The AI can now use tools to interact with your system.

### Build an Agent

Agents combine AI reasoning with tools to accomplish complex tasks:

```python
from consoul import Consoul

code_analyzer = Consoul(
    tools=["grep", "code_search", "read"],
    system_prompt="You are a code analysis expert. Help find and explain code."
)

code_analyzer.chat("Find all database queries in this project")
code_analyzer.chat("Are there any security vulnerabilities?")
code_analyzer.chat("Where should I add rate limiting?")
```

The AI will use tools to search code, read files, and provide analysis.

## Core Concepts

### 1. Models

Consoul supports multiple AI providers with automatic provider detection:

```python
from consoul import Consoul

# OpenAI
console = Consoul(model="gpt-4o")

# Anthropic
console = Consoul(model="claude-3-5-sonnet-20241022")

# Google
console = Consoul(model="gemini-2.0-flash-exp")

# Local Ollama
console = Consoul(model="llama3.2")
```

### 2. Tools

Tools let the AI perform actions beyond text generation:

| Tool Category | Examples | Risk Level |
|---------------|----------|------------|
| **Search** | `grep`, `code_search`, `find_references` | SAFE |
| **File Edit** | `create_file`, `edit_lines`, `delete_file` | CAUTION-DANGEROUS |
| **Web** | `web_search`, `read_url`, `wikipedia` | SAFE |
| **Execute** | `bash` | CAUTION-DANGEROUS |

Enable tools by category, risk level, or name:

```python
# Safe tools only (read-only)
console = Consoul(tools="safe")

# Specific category
console = Consoul(tools="search")

# Specific tools
console = Consoul(tools=["bash", "grep", "code_search"])

# Risk-based filtering
console = Consoul(tools="caution")  # SAFE + CAUTION tools
```

### 3. Conversation History

Consoul maintains conversation context automatically:

```python
console = Consoul()

console.chat("My name is Alice")
console.chat("What programming language should I learn?")
response = console.chat("What's my name?")  # → "Your name is Alice."

# Start fresh
console.clear()
```

### 4. Custom Tools

Extend functionality with your own tools:

```python
from consoul import Consoul
from langchain_core.tools import tool

@tool
def calculate_fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number."""
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

console = Consoul(tools=[calculate_fibonacci, "bash"])
console.chat("What's the 15th Fibonacci number?")  # Uses your tool
```

### 5. Introspection

Monitor usage, costs, and configuration:

```python
console = Consoul(tools=True)
console.chat("Hello!")

# View settings
console.settings
# {'model': 'claude-3-5-sonnet-20241022', 'tools_enabled': True, ...}

# Estimate costs (approximation based on total tokens)
console.last_cost
# {'input_tokens': 87, 'output_tokens': 12, 'estimated_cost': 0.000441}
# Note: This is a rough estimate. Use provider dashboards for exact costs.

# Last request details
console.last_request
# {'message': 'Hello!', 'model': 'claude-...', 'tokens_before': 0}
```

## Built-in Tools Catalog

### Search Tools (SAFE)
- **`grep`** - Search file contents with patterns
- **`code_search`** - Find code patterns (classes, functions)
- **`find_references`** - Find symbol references
- **`read`** - Read file contents

### File Edit Tools (CAUTION-DANGEROUS)
- **`create_file`** - Create new files
- **`edit_lines`** - Edit specific line ranges
- **`edit_replace`** - Search and replace in files
- **`append_file`** - Append content to files
- **`delete_file`** - Delete files (DANGEROUS)

### Web Tools (SAFE)
- **`web_search`** - Search the web
- **`read_url`** - Fetch and parse web pages
- **`wikipedia`** - Search Wikipedia

### Execute Tools (CAUTION)
- **`bash`** - Execute shell commands

See [Tools Deep Dive](tools.md) for detailed documentation.

## Security & Safety

### Risk Levels

Every tool has a risk classification:

- **SAFE**: Read-only operations (grep, web_search, read)
- **CAUTION**: File operations and safe commands (create_file, bash ls)
- **DANGEROUS**: Destructive operations (delete_file, bash rm)

Filter tools by risk:

```python
# Only safe, read-only tools
console = Consoul(tools="safe")

# Safe + caution (file operations)
console = Consoul(tools="caution")

# All tools (be careful!)
console = Consoul(tools="dangerous")
```

### Best Practices

1. **Start with `tools="safe"`** for untrusted AI interactions
2. **Use version control (git)** when enabling file-edit tools
3. **Principle of least privilege**: Only grant necessary tools
4. **Review tool approvals**: Check what the AI wants to do
5. **Monitor usage**: Track `console.last_cost` for token estimates (use provider dashboards for exact costs)

## Common Use Cases

### Code Analysis

```python
analyzer = Consoul(
    tools=["grep", "code_search", "read"],
    system_prompt="You are a code reviewer. Find issues and suggest improvements."
)

analyzer.chat("Find all TODO comments")
analyzer.chat("Are there security vulnerabilities?")
analyzer.chat("Check for code duplication")
```

### File Management

```python
file_manager = Consoul(
    tools=["bash", "create_file", "edit_lines"],
    system_prompt="You are a file organization assistant."
)

file_manager.chat("Create a Python project structure")
file_manager.chat("Add type hints to all functions")
file_manager.chat("Organize imports according to PEP 8")
```

### Web Research

```python
researcher = Consoul(
    tools=["web_search", "read_url", "wikipedia"],
    system_prompt="You are a research assistant. Cite your sources."
)

researcher.chat("What's new in Python 3.13?")
researcher.chat("Compare FastAPI vs Flask")
researcher.chat("Explain quantum computing")
```

### DevOps Automation

```python
devops = Consoul(
    tools=["bash", "create_file", "edit_lines"],
    system_prompt="You are a DevOps expert. Follow best practices."
)

devops.chat("Create a Dockerfile for this app")
devops.chat("Set up GitHub Actions CI/CD")
devops.chat("Configure Docker Compose")
```

## API Reference

### Consoul Class

```python
Consoul(
    model: str | None = None,
    profile: str = "default",
    tools: bool | str | list = True,
    temperature: float | None = None,
    system_prompt: str | None = None,
    persist: bool = True,
    api_key: str | None = None,
    discover_tools: bool = False
)
```

**Methods:**

- **`chat(message: str) -> str`**: Send a message, get a response
- **`ask(message: str, show_tokens: bool) -> ConsoulResponse`**: Get structured response with metadata
- **`clear() -> None`**: Clear conversation history

**Properties:**

- **`settings`**: Current configuration
- **`last_request`**: Last API request details
- **`last_cost`**: Token usage and cost estimate

### ConsoulResponse Class

```python
class ConsoulResponse:
    content: str    # Response text
    tokens: int     # Token count (if show_tokens=True)
    model: str      # Model name
```

See [API Reference](reference.md) for complete documentation.

## Configuration

Consoul uses profiles stored in `~/.config/consoul/config.yaml`:

```yaml
profiles:
  default:
    model: claude-3-5-sonnet-20241022
    temperature: 0.7
    system_prompt: "You are a helpful AI assistant."

  code-expert:
    model: gpt-4o
    temperature: 0.3
    system_prompt: "You are a senior software engineer."
```

Use profiles:

```python
# Use default profile
console = Consoul()

# Use specific profile
console = Consoul(profile="code-expert")

# Override profile settings
console = Consoul(profile="default", temperature=0.9)
```

Initialize configuration:

```bash
consoul init  # Create config file
```

## Learning Path

1. **[Tutorial](tutorial.md)** - Learn SDK fundamentals step-by-step
2. **[Integration Guide](integration-guide.md)** - Real-world project integration patterns
3. **[Tools](tools.md)** - Master all 13 built-in tools
4. **[Building Agents](agents.md)** - Create specialized AI agents
5. **[API Reference](reference.md)** - Complete API documentation

## Examples

### Minimal Chat (3 Lines)

```python
from consoul import Consoul

console = Consoul()
print(console.chat("Hello!"))
```

### Multi-Turn Conversation

```python
from consoul import Consoul

console = Consoul()
console.chat("My name is Alice")
console.chat("I'm learning Python")
response = console.chat("What's my name and what am I learning?")
# → "Your name is Alice and you're learning Python."
```

### Custom Tool Example

```python
from consoul import Consoul
from langchain_core.tools import tool

@tool
def get_weather(city: str) -> str:
    """Get weather for a city."""
    return f"The weather in {city} is sunny, 72°F"

console = Consoul(tools=[get_weather])
print(console.chat("What's the weather in San Francisco?"))
# → "The weather in San Francisco is sunny, 72°F"
```

### Cost Tracking

```python
from consoul import Consoul

console = Consoul(model="gpt-4o")
console.chat("Explain quantum computing")

cost = console.last_cost
print(f"Tokens: {cost['total_tokens']}")
print(f"Estimated cost: ${cost['estimated_cost']:.4f}")
# Note: This is a rough approximation. Check provider dashboards for exact costs.
```

## Support

- **[GitHub Issues](https://github.com/goatbytes/consoul/issues)** - Report bugs
- **[Discussions](https://github.com/goatbytes/consoul/discussions)** - Ask questions
- **[Documentation](https://goatbytes.github.io/consoul/)** - Full docs

## License

MIT License - see [LICENSE](https://github.com/goatbytes/consoul/blob/main/LICENSE)

---

**Ready to build?** Start with the [Tutorial](tutorial.md) →
