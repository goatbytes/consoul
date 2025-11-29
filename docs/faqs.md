# Frequently Asked Questions

## General

### What is Consoul?

Consoul is an AI-powered terminal assistant that brings modern AI capabilities directly to your terminal. It offers three interfaces: a beautiful TUI (Terminal User Interface), a powerful CLI, and a flexible SDK for integration.

### Which AI models does Consoul support?

Consoul supports multiple AI providers:

- **OpenAI**: GPT-4o, GPT-4o-mini, GPT-4 Turbo, and more
- **Anthropic**: Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku
- **Google**: Gemini 2.0 Flash, Gemini 1.5 Pro, Gemini 1.5 Flash
- **Ollama**: Any locally-hosted models (Llama, Mistral, etc.)

### Do I need API keys?

Yes, you need API keys for the cloud providers you want to use:

- `OPENAI_API_KEY` for OpenAI models
- `ANTHROPIC_API_KEY` for Claude models
- `GOOGLE_API_KEY` for Gemini models

Ollama models run locally and don't require API keys.

## Installation & Setup

### How do I install Consoul?

```bash
pip install consoul
```

Or with all features:

```bash
pip install consoul[all]
```

### Where are the configuration files stored?

Configuration files are stored in:

- **macOS/Linux**: `~/.config/consoul/`
- **Windows**: `%APPDATA%\consoul\`

### How do I configure my API keys?

Run the interactive configuration:

```bash
consoul config
```

Or set environment variables:

```bash
export OPENAI_API_KEY="your-key-here"
export ANTHROPIC_API_KEY="your-key-here"
export GOOGLE_API_KEY="your-key-here"
```

## Using the TUI

### How do I launch the TUI?

```bash
consoul
```

Or for a specific model:

```bash
consoul --model claude-3-5-sonnet-20241022
```

### What are the keyboard shortcuts?

See the [Keyboard Shortcuts](user-guide/tui/keyboard-shortcuts.md) page for a complete list. Common ones:

- `Ctrl+N`: New conversation
- `Ctrl+S`: Settings
- `Ctrl+M`: Model selector
- `Ctrl+C`: Quit

### Can I customize the theme?

Yes! Consoul comes with multiple built-in themes:

- Consoul Dark/Light
- Tokyo Night
- Nord
- Gruvbox
- Flexoki

Switch themes in Settings (`Ctrl+S`) or via configuration.

### How do I attach files in the TUI?

Press `Ctrl+A` to open the attach modal, then:

1. Select files from your filesystem
2. Choose images to analyze
3. Add code snippets

## Using the CLI

### How do I ask a quick question?

```bash
consoul ask "What is the capital of France?"
```

### How do I start a chat session?

```bash
consoul chat
```

### Can I pipe content to Consoul?

Yes! Pipe any content:

```bash
cat myfile.py | consoul ask "Explain this code"
```

### How do I attach files from the CLI?

```bash
consoul ask "Review this code" --attach file.py
```

## Using the SDK

### How do I use Consoul in my Python code?

```python
from consoul.chat.manager import ChatManager
from consoul.config.manager import ConfigurationManager

config = ConfigurationManager()
chat = ChatManager(config, model_name="gpt-4o")

async for chunk in chat.send_message("Hello!"):
    print(chunk.content, end="")
```

### Can I create custom tools?

Yes! See the [Tools documentation](api/tools.md) for details on creating custom tools.

### Is the SDK async or sync?

The SDK is async-first, using `asyncio` for efficient concurrent operations and streaming responses.

## Troubleshooting

### I'm getting "API key not found" errors

Make sure you've set your API keys:

1. Run `consoul config` to set them interactively
2. Or export them as environment variables
3. Check the configuration file at `~/.config/consoul/config.yaml`

### The TUI doesn't display properly

Try:

1. Update your terminal emulator
2. Ensure your terminal supports 256 colors or true color
3. Check if your terminal font supports Unicode characters

### Models are responding slowly

- Cloud models depend on API response times
- Try switching to a faster model (e.g., GPT-4o-mini, Claude Haiku)
- For local models via Ollama, ensure your hardware is sufficient

### How do I report bugs?

Please report bugs on our [GitHub Issues](https://github.com/goatbytes/consoul/issues) page.

## Features

### Does Consoul support streaming responses?

Yes! All interfaces support streaming responses for real-time output.

### Can I save conversation history?

Yes, conversations are automatically saved. You can:

- Resume previous conversations in the TUI
- Export conversations to markdown or JSON
- List and search past conversations

### Does Consoul support code execution?

Not directly. However, you can use tools to run code safely in sandboxed environments.

### Can I use Consoul offline?

Yes, with Ollama models running locally. Cloud models require an internet connection.

## Privacy & Security

### Is my data stored on your servers?

No. Consoul runs locally on your machine. Conversations are only sent to the AI providers you choose (OpenAI, Anthropic, Google, or local Ollama).

### Are my API keys secure?

API keys are stored locally in your configuration file. Never commit them to version control. Use environment variables in production.

### What data does Consoul collect?

Consoul doesn't collect any usage data or telemetry. All processing happens locally on your machine.

## Advanced

### Can I use custom prompts or system messages?

Yes! Configure system prompts in your configuration file or via the Settings modal in the TUI.

### How do I switch between different model providers?

Use the model selector (`Ctrl+M` in TUI) or specify the model via CLI:

```bash
consoul ask "Question" --model claude-3-5-sonnet-20241022
```

### Can I run multiple conversations in parallel?

Yes, using the SDK you can manage multiple `ChatManager` instances concurrently.

### How do I contribute to Consoul?

See our [Contributing Guide](contributing.md) for details on:

- Setting up the development environment
- Code style guidelines
- Submitting pull requests

## Support

### Where can I get help?

- **Documentation**: [https://goatbytes.github.io/consoul/](https://goatbytes.github.io/consoul/)
- **GitHub Issues**: [https://github.com/goatbytes/consoul/issues](https://github.com/goatbytes/consoul/issues)
- **Discussions**: [https://github.com/goatbytes/consoul/discussions](https://github.com/goatbytes/consoul/discussions)

### Is Consoul open source?

Yes! Consoul is open source under the MIT License.
