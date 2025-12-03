# Changelog

All notable changes to Consoul will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

---

## [0.2.0] - 2025-12-02

**First Public Release** 🎉

This is the first public release of Consoul, featuring a complete TUI, comprehensive CLI commands, multi-provider AI support, and powerful tool calling capabilities.

### Added

#### CLI Commands
- 🎯 **`consoul ask`** - One-off questions without interactive mode
  - Support for `--stdin` flag to pipe command output (SOUL-205)
  - Support for `--file` and `--glob` flags to include file context (SOUL-206)
  - Support for `--system` flag for custom system prompts (SOUL-207)
  - Integration with all AI providers and tool calling

- 💬 **`consoul chat`** - Interactive chat sessions with full context
  - Multi-line input support
  - Streaming responses
  - Tool calling integration
  - Conversation persistence

- 📚 **`consoul history`** - Conversation management commands
  - `list` - Show all conversations with metadata
  - `show` - Display conversation details
  - `summary` - Get conversation summary
  - `export` - Export to markdown/json formats
  - `delete` - Delete specific conversation
  - `clear` - Delete all conversations
  - `search` - Full-text search across conversations
  - `stats` - Usage statistics and analytics
  - `import` - Import conversations from file
  - `resume` - Resume previous conversation (SOUL-209)

- ⚙️ **`consoul config`** - Configuration management
  - Get/set configuration values
  - Profile management
  - API key configuration

#### Image Analysis (Vision Support)
- 📸 **Multimodal vision capabilities** for analyzing images with AI models
  - Support for Claude 3.5 Sonnet, GPT-4o, Gemini 2.0 Flash, and Ollama LLaVA
  - Analyze screenshots, diagrams, UI mockups, and other visual content
  - Multiple image support (up to 5 images per query)
  - Automatic image path detection in messages (e.g., "analyze screenshot.png")
  - File attachment button (📎) in TUI for easy image uploads
  - Comprehensive configuration options via `tools.image_analysis`

- **Security features** for image analysis:
  - File size limits (configurable, default 5MB)
  - Extension filtering (PNG, JPEG, GIF, WebP)
  - Path blocking for sensitive directories (~/.ssh, /etc, ~/.aws, etc.)
  - Magic byte validation to prevent extension spoofing
  - Path traversal protection

- **Image Analysis Documentation**:
  - Complete user guide: `docs/user-guide/image-analysis.md`
  - Configuration reference in `docs/user-guide/configuration.md`
  - Code examples: `docs/examples/image-analysis-example.py`
  - README section with quick start guide

#### Token Counting Improvements
- 🚀 **HuggingFace tokenizer integration** for Ollama models
  - 100% accurate token counting (vs 66% with character approximation)
  - <5ms performance (vs 3-10+ seconds with Ollama API calls)
  - 3-tier discovery strategy: static mapping → manifest discovery → approximation
  - Support for 31+ Ollama models (Granite, Llama, Qwen, Mistral, etc.)
  - Graceful fallback when transformers package unavailable
  - Comprehensive test coverage (24 tests)

#### Terminal User Interface (TUI)
- 🖥️ **Complete interactive TUI** powered by Textual
  - Real-time streaming responses with markdown rendering
  - Conversation history sidebar with search
  - Multi-line input with syntax highlighting
  - Keyboard shortcuts and mouse navigation
  - Customizable themes (light/dark modes)
  - File attachment button (📎) for easy uploads
  - Visual file chips with icons and remove buttons
  - Settings panel for runtime configuration

- 💾 **Conversation persistence**:
  - Complete UI reconstruction from database
  - Preserve tool calls, file attachments, and multimodal content
  - Historical file chips for reloaded conversations
  - Proper message ordering and threading
  - Resume any previous conversation with full context

#### AI Provider Support
- 🤖 **Multi-provider architecture** via LangChain
  - **Anthropic Claude** - Claude 3.5 Sonnet, Opus, Haiku
  - **OpenAI** - GPT-4o, GPT-4, GPT-3.5 Turbo
  - **Google Gemini** - Gemini 2.0 Flash, Gemini 1.5 Pro
  - **Ollama** - Local models (Llama 3, Mistral, DeepSeek, etc.)
  - Streaming support across all providers
  - Automatic model capability detection
  - Cost tracking and token counting

#### Tool Calling System
- 🛠️ **Comprehensive tool ecosystem** with safety controls
  - **File Operations** - Read, write, edit files with approval workflows
  - **Code Search** - Grep-based search, AST analysis, reference finder
  - **Image Analysis** - Vision capabilities for screenshots and diagrams
  - **Bash Execution** - Safe command execution with approval
  - **Web Search** - DuckDuckGo integration for current information
  - **Wikipedia** - Quick reference and fact-checking
  - Configurable permission policies (paranoid, balanced, trusting, unrestricted)
  - Audit logging for all tool executions
  - Interactive approval UI for dangerous operations

#### Documentation
- 📖 **Comprehensive documentation** (70+ fixes in this release)
  - Complete user guide with examples
  - CLI reference for all commands
  - Configuration guide with all options
  - Tool usage documentation
  - API/SDK reference
  - Troubleshooting guides
  - Fixed 70+ command syntax errors across documentation (SOUL-208)

### Changed
- **Version bumped to 0.2.0** - First public release (SOUL-214)
- **Documentation URLs** - Updated to https://consoul.goatbytes.io (SOUL-213)
- **Command syntax** - Fixed 70+ documentation errors (proper use of `consoul ask` vs `consoul chat`)
- **Direct multimodal messaging** - Images now sent directly to vision-capable models without intermediate tool calls
- **Disabled analyze_images tool** - Replaced with direct multimodal HumanMessage approach for better UX
- **CLI flag syntax** - Global flags (--temperature, --max-tokens) now properly documented before command name

### Fixed
- **Token counting hangs** - Ollama models now use local HuggingFace tokenizers (100% accuracy, <5ms)
- **Conversation UI reconstruction** - Historical conversations now fully restore with tool calls and attachments
- **Tool call widgets** - Missing widgets when loading historical conversations now preserved
- **Empty assistant messages** - Fixed missing bubbles in TUI for empty responses
- **Token estimation performance** - Eliminated 18+ second delays with Ollama API
- **Documentation accuracy** - Corrected --temperature and --max-tokens flag documentation (SOUL-208)
- **Type checking errors** - Resolved mypy errors across core modules

### Security
- **Image analysis security** - Path blocking for sensitive directories (~/.ssh, /etc, ~/.aws)
- **File validation** - Extension filtering and magic byte validation
- **Permission policies** - Configurable tool execution safety levels
- **Audit logging** - Complete execution history in JSONL format
- **Command validation** - Pattern-based blocking of risky commands

### Performance
- **Token counting** - 3-10+ seconds → <5ms for Ollama models
- **HuggingFace tokenizer cache** - Lazy loading with persistent caching
- **Streaming responses** - Real-time token display across all providers

### Developer Experience
- **CLI improvements** - Added --stdin, --file, --glob, --system flags to `consoul ask`
- **History resume** - Resume any conversation with `consoul history resume <id>` (SOUL-209)
- **Better error messages** - Clear validation and helpful suggestions
- **Type safety** - Comprehensive mypy coverage

### Upgrade Notes
- This is the first public release - no breaking changes from 0.1.0 (internal version)
- Configuration location: `~/.config/consoul/config.yaml`
- Conversation history stored in: `~/.local/share/consoul/conversations.db`
- See [documentation](https://consoul.goatbytes.io) for complete setup guide

---

## Previous Releases

*This CHANGELOG was created after the initial release. Previous changes are documented in git history.*

For older changes, see: `git log --oneline --all`
