![Consoul Banner](.art/banner/consoul-banner-100.jpg)

# Consoul

A beautiful terminal-based AI chat interface built with Textual and LangChain

Consoul brings the power of modern AI assistants directly to your terminal with a rich, interactive TUI. Built on Textual's reactive framework and LangChain's provider abstraction, it offers a ChatGPT/Claude-like experience without leaving your command line.

## 🚀 Quick Start

### Installation

```bash
pip install consoul
export ANTHROPIC_API_KEY=your-key-here  # Or OPENAI_API_KEY, GOOGLE_API_KEY
```

### Minimal Example (5 lines)

```python
from consoul import Consoul

console = Consoul()
print(console.chat("What is 2+2?"))
print(console.chat("What files are in the current directory?"))
```

### Quick Customization (~15 lines)

```python
from consoul import Consoul

# Customize as needed
console = Consoul(
    model="gpt-4o",         # Auto-detect provider
    profile="default",       # Use built-in profile
    tools=True,             # Enable bash execution with approval
    temperature=0.7,
)

# Stateful conversation - history is maintained
console.chat("List all Python files in this directory")
console.chat("Show me the first one")

# Rich response with metadata
response = console.ask("Summarize this project", show_tokens=True)
print(f"\nResponse: {response.content}")
print(f"Tokens used: {response.tokens}")
print(f"Model: {response.model}")

# Introspection
print(f"\nSettings: {console.settings}")
print(f"Last cost: {console.last_cost}")
```

### Terminal Interface

For the full interactive TUI:

```bash
consoul                                        # Launch interactive mode
consoul chat "Explain quantum computing"      # One-off question
consoul chat --model gpt-4o "Your question"  # Use specific model
consoul --profile creative chat "Write a poem" # Use specific profile
```

## ✨ Features

- 🎨 **Beautiful TUI** - Rich, interactive terminal interface powered by Textual
- 🤖 **Multi-Provider Support** - OpenAI, Anthropic Claude, Google Gemini, Ollama
- 🛠️ **Tool Calling** - AI-powered command execution with security controls
- ✏️ **File Editing** - AI-powered file manipulation with safety controls and progressive matching
- 🔍 **Code Search** - AST-based semantic search across Python, TypeScript, Go, Rust, Java, C/C++
- 📝 **Conversation History** - Save and resume conversations
- ⚙️ **Flexible Configuration** - YAML-based profiles with environment overrides
- 🔒 **Security-First** - Multi-layer approval system and audit logging
- 📊 **Streaming Responses** - Real-time token streaming
- 🎯 **Profile System** - Switch between different AI behaviors and settings

## 🔧 Tool Calling

Consoul includes a powerful tool calling system that lets AI models execute commands and interact with your system safely.

### Security Features

- **Risk Classification**: Every tool is classified as SAFE, CAUTION, DANGEROUS, or BLOCKED
- **Permission Policies**: Choose from PARANOID, BALANCED, TRUSTING, or UNRESTRICTED
- **User Approval**: Interactive confirmation for dangerous operations
- **Command Validation**: Pattern-based blocking of dangerous commands
- **Audit Logging**: Complete execution history in JSONL format
- **Whitelist/Blacklist**: Fine-grained control over allowed commands

### Quick Start

Enable tool calling in your configuration:

```yaml
profiles:
  default:
    tools:
      enabled: true
      permission_policy: balanced  # Recommended default
```

Start Consoul and ask the AI to run commands:

```bash
consoul

> "What files are in the current directory?"
```

The AI will request to use `bash_execute`, and you'll see an approval modal if required by your security policy.

### Available Tools

- **bash_execute** - Execute bash commands with security controls, timeout enforcement, and output capture

### Permission Policies

Choose your security posture:

| Policy | SAFE Commands | CAUTION Commands | DANGEROUS Commands | Use Case |
|--------|---------------|------------------|-------------------|----------|
| **PARANOID** | ⚠️ Prompt | ⚠️ Prompt | ⚠️ Prompt | Production, maximum security |
| **BALANCED** ⭐ | ✅ Auto | ⚠️ Prompt | ⚠️ Prompt | Recommended default |
| **TRUSTING** | ✅ Auto | ✅ Auto | ⚠️ Prompt | Development, convenience |
| **UNRESTRICTED** | ✅ Auto | ✅ Auto | ✅ Auto | Testing only, DANGEROUS |

Legend: ✅ Auto-approve  ⚠️ Require approval

### Example Configuration

```yaml
tools:
  enabled: true
  permission_policy: balanced
  audit_logging: true
  audit_log_file: ~/.consoul/tool_audit.jsonl

  bash:
    timeout: 60
    whitelist_patterns:
      - "git status"
      - "git log"
      - "ls"
      - "pwd"
    blocked_patterns:
      - "^sudo\\s"
      - "rm\\s+(-[rf]+\\s+)?/"
```

### Custom Tools

Create custom tools with LangChain's `@tool` decorator:

```python
from langchain_core.tools import tool
from consoul.ai.tools import ToolRegistry, RiskLevel

@tool
def get_weather(location: str) -> str:
    """Get current weather for a location."""
    # Implementation here
    return f"Weather in {location}: Sunny, 72°F"

# Register with Consoul
registry = ToolRegistry(config=config.tools)
registry.register(get_weather, risk_level=RiskLevel.SAFE)
```

### Documentation

- **[Complete Tool Calling Guide](docs/tools.md)** - Comprehensive documentation
- **[Configuration Examples](docs/examples/tool-calling-config.yaml)** - Pre-configured templates
- **[Custom Tool Development](docs/examples/custom-tool-example.py)** - Working code examples

### Security Warning

⚠️ **Tool calling is powerful but potentially dangerous.** Always:
- Review commands before approval
- Use appropriate permission policies for your environment
- Enable audit logging for accountability
- Never use UNRESTRICTED policy in production
- Keep whitelists minimal and specific

See the [Security Policy](SECURITY.md) for best practices.

## 🔍 Code Search

Consoul includes powerful code search tools for semantic code analysis and navigation.

### Available Search Tools

- **grep_search** - Fast text-based pattern matching (uses ripgrep)
- **code_search** - AST-based symbol search (find function/class definitions)
- **find_references** - Symbol usage finder (find all usages of a symbol)

### Quick Start

Enable tools in your configuration:

```yaml
profiles:
  default:
    tools:
      enabled: true  # Enables all search tools
```

Start Consoul and use natural language:

```bash
consoul

> "Find all TODO comments in Python files"         # → grep_search
> "Find the ToolRegistry class definition"         # → code_search
> "Find all usages of bash_execute in the project" # → find_references
```

### Programmatic Usage

```python
from consoul import Consoul

console = Consoul(tools=True)

# Find function definitions
console.chat("Find the calculate_total function")

# Find all usages
console.chat("Find all places where calculate_total is called")

# Complex workflow
console.chat("""
First find the ShoppingCart class definition,
then find all places where it's instantiated
""")
```

### Direct Tool Usage

```python
from consoul.ai.tools import grep_search, code_search, find_references

# Fast text search
result = grep_search.invoke({
    "pattern": "TODO",
    "glob_pattern": "*.py"
})

# Find function definition
result = code_search.invoke({
    "query": "calculate_total",
    "symbol_type": "function"
})

# Find all usages
result = find_references.invoke({
    "symbol": "bash_execute",
    "scope": "project"
})
```

### Tool Comparison

| When to Use | Tool | Why |
|-------------|------|-----|
| Find text patterns, TODOs, comments | `grep_search` | Fast text matching |
| Find where a function is defined | `code_search` | Semantic definition search |
| Find all usages of a symbol | `find_references` | Reference tracking |
| Search across any file type | `grep_search` | Works on all text |
| Understand code structure | `code_search` | AST-based understanding |

### Language Support

| Language | grep_search | code_search | find_references |
|----------|-------------|-------------|-----------------|
| Python | ✅ | ✅ | ✅ |
| JavaScript/TypeScript | ✅ | ✅ | ✅ |
| Go | ✅ | ✅ | ✅ |
| Kotlin | ✅ | ✅ | ✅ |
| Java | ✅ | ✅ | ✅ |
| Rust | ✅ | ✅ | ❌ |
| C/C++ | ✅ | ✅ | ❌ |

**Legend:** ✅ Full support | ❌ No support

**Note:** find_references currently supports Python, JavaScript/TypeScript, Go, Kotlin, and Java. For other languages, use grep_search for text-based reference finding.

### Performance

- **grep_search**: Very fast (<1s typical)
- **code_search**: Fast with cache (~2s first run, <1s cached)
- **find_references**: Medium (~3s first run, <1s cached)

**Cache benefit**: 5-10x speedup on repeated searches

### Documentation

- **[Code Search Guide](docs/user-guide/code-search.md)** - Comprehensive usage guide
- **[Troubleshooting](docs/user-guide/code-search-troubleshooting.md)** - Common issues and solutions
- **[Code Examples](docs/examples/code-search-example.py)** - Working Python examples

## 📚 Documentation

- [Installation Guide](docs/installation.md)
- [Quick Start](docs/quickstart.md)
- [Configuration Reference](docs/user-guide/configuration.md)
- [Tool Calling Guide](docs/tools.md)
- **[SDK Integration Guide](docs/sdk/tool-calling-integration.md)** - Embed Consoul in your application
- [Development Guide](docs/development.md)

## 🔌 SDK Integration

Consoul is designed as an SDK for embedding AI capabilities into your applications. Integrate tool calling without the TUI:

### CLI Tools
```python
from consoul.ai.tools import ToolRegistry, bash_execute
from consoul.ai.tools.providers import CliApprovalProvider

provider = CliApprovalProvider(verbose=True)
registry = ToolRegistry(config.tools, approval_provider=provider)
registry.register(bash_execute, risk_level=RiskLevel.CAUTION)
```

### Web Applications
```python
class WebApprovalProvider:
    async def request_approval(self, request):
        # Send to your web API
        response = await http_client.post("/approve", json=request.to_dict())
        return ToolApprovalResponse(**response.json())
```

### Custom Audit Logging
```python
class DatabaseAuditLogger:
    async def log_event(self, event):
        await db.execute("INSERT INTO audit_log VALUES (...)", event.to_dict())
```

**Complete examples**: See [examples/sdk/](examples/sdk/) for working code

**Full documentation**: [SDK Integration Guide](docs/sdk/tool-calling-integration.md)

## 🔑 API Keys

Consoul supports multiple AI providers. Set the appropriate environment variable:

```bash
# Anthropic Claude
export ANTHROPIC_API_KEY=your-key-here

# OpenAI
export OPENAI_API_KEY=your-key-here

# Google Gemini
export GOOGLE_API_KEY=your-key-here

# Ollama (no API key needed - runs locally)
# Just install from https://ollama.com
```

## ⚙️ Configuration

Create `~/.consoul/config.yaml`:

```yaml
profiles:
  default:
    model:
      provider: anthropic
      model: claude-3-5-sonnet-20241022
      temperature: 0.7
      max_tokens: 4096

    conversation:
      save_history: true
      max_history: 50

    tools:
      enabled: true
      permission_policy: balanced
```

See [Configuration Guide](docs/user-guide/configuration.md) for all options.

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built with:
- [Textual](https://textual.textualize.io/) - Beautiful TUI framework
- [LangChain](https://python.langchain.com/) - AI orchestration
- [Anthropic](https://www.anthropic.com/) - Claude AI models
- [OpenAI](https://openai.com/) - GPT models
- [Google AI](https://ai.google.dev/) - Gemini models
