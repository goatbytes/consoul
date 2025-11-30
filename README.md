![Consoul Banner](.art/banner/consoul-banner-100.jpg)

# Consoul

**AI-Powered Terminal Assistant** — Beautiful TUI · Powerful CLI · Flexible SDK

Bring modern AI assistance directly to your terminal. Chat with Claude, GPT-4, Gemini, and local models using a rich interactive interface or simple CLI commands.

📖 **[Full Documentation](https://consoul.goatbytes.io)** | 🚀 [Quick Start](#quick-start) | 🎨 [Features](#features)

---

## Quick Start

### Installation

```bash
pip install consoul
```

### Set Your API Key

```bash
# Choose your provider
export ANTHROPIC_API_KEY=your-key-here  # Claude
export OPENAI_API_KEY=your-key-here     # GPT-4
export GOOGLE_API_KEY=your-key-here     # Gemini
```

### Launch the TUI

```bash
consoul
```

### Or Use the SDK

```python
from consoul import Consoul

console = Consoul()
print(console.chat("What is 2+2?"))
```

---

## Features

### 🎨 Beautiful TUI
Rich, interactive terminal interface powered by [Textual](https://textual.textualize.io/)

![Consoul TUI](docs/assets/screenshots/consoul-themes.gif)

- Multi-turn conversations with streaming responses
- Conversation history and search
- File attachments and image analysis
- Customizable themes (light/dark)
- Mouse and keyboard navigation

### 🤖 Multi-Provider Support
Use your favorite AI model or run locally:

- **Anthropic Claude** - Claude 3.5 Sonnet, Opus, Haiku
- **OpenAI** - GPT-4o, GPT-4, GPT-3.5
- **Google Gemini** - Gemini 2.0 Flash, Pro
- **Ollama** - Run models locally (Llama, Mistral, etc.)
- **LlamaCpp** - GGUF models with GPU acceleration

### 🛠️ AI-Powered Tools

**File Editing**
Let AI create, modify, and delete files with safety controls:
```bash
consoul chat "Add error handling to calculate_total in src/utils.py"
```

**Code Search**
Navigate your codebase semantically:
```bash
consoul chat "Find all usages of deprecated_function"
```

**Image Analysis**
Debug with screenshots:
```bash
consoul chat "What's wrong with this error?" --attach screenshot.png
```

**And More:**
- Bash command execution with approval workflows
- Web search and URL fetching
- Session management and history

### 📝 Simple CLI

For quick questions without the TUI:

```bash
# Chat mode
consoul chat

# One-off questions
consoul ask "Explain Python decorators"

# Attach files
consoul chat --attach requirements.txt "What dependencies are outdated?"
```

### 🔌 SDK Integration

Embed AI capabilities in your Python applications:

```python
from consoul import Consoul

# Enable tools for file operations and code search
console = Consoul(tools=True)

# Stateful conversation
console.chat("List all TODO comments in Python files")
console.chat("Create a summary.md file with the results")

# Rich responses with metadata
response = console.ask("Summarize this project", show_tokens=True)
print(f"Tokens: {response.tokens}, Cost: ${response.cost:.4f}")
```

---

## Documentation

📖 **[Full Documentation](https://consoul.goatbytes.io)**

**Getting Started:**
- [Installation Guide](https://consoul.goatbytes.io/installation/)
- [Quick Start](https://consoul.goatbytes.io/quickstart/)
- [Configuration](https://consoul.goatbytes.io/user-guide/configuration/)

**TUI:**
- [Interface Guide](https://consoul.goatbytes.io/user-guide/tui/interface/)
- [Keyboard Shortcuts](https://consoul.goatbytes.io/user-guide/tui/keyboard-shortcuts/)
- [Themes](https://consoul.goatbytes.io/user-guide/tui/themes/)

**Tools:**
- [File Editing](https://consoul.goatbytes.io/user-guide/file-editing/)
- [Image Analysis](https://consoul.goatbytes.io/user-guide/image-analysis/)
- [Code Search](https://consoul.goatbytes.io/user-guide/code-search/)

**SDK:**
- [SDK Overview](https://consoul.goatbytes.io/api/)
- [Tutorial](https://consoul.goatbytes.io/api/tutorial/)
- [API Reference](https://consoul.goatbytes.io/api/reference/)

---

## Configuration

Create `~/.consoul/config.yaml`:

```yaml
# Default profile
profiles:
  default:
    model:
      provider: anthropic
      model: claude-3-5-sonnet-20241022
      temperature: 0.7

    tools:
      enabled: true
      permission_policy: balanced  # Require approval for risky operations

    conversation:
      save_history: true
      max_history: 50

  # Local model profile
  local:
    model:
      provider: ollama
      model: llama3.2:latest
```

**Switch profiles:**
```bash
consoul --profile local
```

See the [Configuration Guide](https://consoul.goatbytes.io/user-guide/configuration/) for all options.

---

## Security

Consoul includes comprehensive security controls for tool execution:

- **Permission Policies** - PARANOID, BALANCED, TRUSTING, UNRESTRICTED
- **Approval Workflows** - Interactive confirmation for dangerous operations
- **Audit Logging** - Complete execution history in JSONL format
- **Command Validation** - Pattern-based blocking of risky commands

See the [Security Policy](SECURITY.md) for best practices.

---

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT License - see [LICENSE](LICENSE) file for details.

---

## Built With

- [Textual](https://textual.textualize.io/) - Beautiful TUI framework
- [LangChain](https://python.langchain.com/) - AI orchestration
- [Anthropic](https://www.anthropic.com/) - Claude AI models
- [OpenAI](https://openai.com/) - GPT models
- [Google AI](https://ai.google.dev/) - Gemini models

---

**Made with ❤️ by [GoatBytes.IO](https://goatbytes.io)**
