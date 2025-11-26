# Consoul – AI-Powered Terminal Assistant

**Consoul** brings the power of modern AI assistants directly to your terminal with a rich, interactive TUI. Built on **Textual's reactive framework** and **LangChain's provider abstraction**, it offers a ChatGPT/Claude-like experience without leaving your command line.

---

## 🚀 Why Consoul?

In the age of AI-assisted development, switching between your terminal and browser-based AI assistants breaks your flow. Consoul solves this by bringing AI directly into your terminal workflow:

* **Terminal-Native:** Rich, interactive TUI powered by Textual — beautiful and responsive
* **Multi-Provider Support:** Works with OpenAI, Anthropic Claude, Google Gemini, and more via LangChain
* **Developer-Focused:** Context-aware conversations with code, files, and terminal output
* **Offline-Ready:** Local models and cached responses when you need them
* **Extensible:** Plugin system for custom tools and integrations
* **Privacy-First:** Your conversations and data stay under your control

---

## 📦 Quick Start

```bash
# Install Consoul
pip install consoul

# Run the interactive TUI
consoul tui

# Or use the CLI directly
consoul chat "How do I reverse a string in Python?"
```

---

## ✨ Features

**Current Features:**

* ✅ **Rich Terminal UI** – Beautiful, responsive interface built with Textual
* ✅ **Multi-Provider Support** – OpenAI, Anthropic, Google, and more via LangChain
* ✅ **Context Management** – Include files, code snippets, and terminal output in conversations
* ✅ **Conversation History** – Save and resume conversations across sessions
* ✅ **Streaming Responses** – Real-time AI responses with markdown rendering
* ✅ **Configuration Management** – Flexible configuration via YAML/TOML

**Planned Features:**

* 🛠️ **Plugin System** – Extend Consoul with custom tools and integrations
* 🛠️ **Code Execution** – Run and test code suggestions directly in the terminal
* 🛠️ **Git Integration** – Context-aware assistance with commit messages, code review, etc.
* 🛠️ **Local Model Support** – Use Ollama and other local LLMs

---

## 🎯 Use Cases

### Development Assistance

```bash
# Get help with code
consoul chat --file main.py "How can I optimize this function?"

# Explain error messages
consoul chat --stdin < error.log "What's causing this error?"
```

### Learning and Documentation

```bash
# Learn new concepts
consoul chat "Explain Python async/await with examples"

# Generate documentation
consoul chat --file api.py "Write API documentation for this module"
```

### Command Line Help

```bash
# Get command help
consoul chat "How do I find large files using find?"

# Explain complex commands
consoul chat "Explain: find . -type f -name '*.py' -exec grep -l 'TODO' {} \;"
```

---

## 🔧 Configuration

Consoul can be configured via `~/.config/consoul/config.yaml`:

```yaml
# AI Provider Configuration
provider: anthropic  # or openai, google, etc.
model: claude-3-5-sonnet-20241022
api_key: ${ANTHROPIC_API_KEY}  # Use environment variables

# UI Configuration
theme: dark
editor: vim

# Conversation Settings
max_history: 50
save_conversations: true
```

---

## 📖 Documentation

- [Installation Guide](installation.md) – Get Consoul up and running
- [Quick Start](quickstart.md) – Your first conversation with Consoul
- [User Guide](user-guide/getting-started.md) – Detailed usage instructions
- [Development Setup](development.md) – Contribute to Consoul
- [API Reference](api/index.md) – Package and module documentation

---

## 🤝 Contributing

Consoul is open source and welcomes contributions! See our [Contributing Guide](contributing.md) for details on:

- Setting up your development environment
- Code style and testing requirements
- Submitting pull requests
- Signing the Contributor License Agreement

---

## 📄 License

Consoul is licensed under the [Apache License 2.0](https://github.com/goatbytes/consoul/blob/main/LICENSE).

---

## 🔗 Links

* [GitHub Repository](https://github.com/goatbytes/consoul)
* [PyPI Package](https://pypi.org/project/consoul/)
* [GoatBytes.IO](https://goatbytes.io)

---

Built with ❤️ for developers by **GoatBytes.IO**.
