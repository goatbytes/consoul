# Changelog

All notable changes to Consoul will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

---

## [0.4.0] - 2025-12-16

**Major Feature Release - SDK Decoupling & Thinking Mode Support**

This release represents a significant architectural milestone with the completion of SDK decoupling (EPIC-012, EPIC-013), making Consoul's AI capabilities available as a standalone SDK. It also introduces thinking mode support for reasoning models and modern async streaming architecture.

**Stats:** 104 commits since v0.3.0 (22 features, 37 fixes, 0 breaking changes)

### Added

#### SDK Service Layer (EPIC-013)
- 🏗️ **ConversationService** - Centralized conversation management
  - Message history tracking and persistence
  - Async streaming support with approval workflow
  - Tool execution orchestration
  - Integration tests verifying SDK independence (SOUL-278)
  - Comprehensive unit tests achieving 76.43% coverage (SOUL-255, SOUL-256)

- 🤖 **ModelService** - Model registry and discovery
  - Unified interface for all AI providers (OpenAI, Anthropic, Google, Ollama, HuggingFace)
  - Dynamic local model discovery (Ollama, llamacpp, MLX)
  - Context window and capability detection
  - Model metadata from centralized registry (SOUL-276)

- 🛠️ **ToolService** - Tool catalog and execution
  - Tool registration and permission management
  - Async tool execution with approval hooks
  - Configurable approval providers (SOUL-234, SOUL-235)
  - WebSocket-compatible tool handling

#### Thinking Mode Support (SOUL-280, SOUL-283)
- 🧠 **Native support for reasoning models**
  - phi4-reasoning:14b, DeepSeek-R1, Qwen QWQ, o1-preview
  - Automatic detection of thinking tags (`<think>`, `<thinking>`, `<reasoning>`)
  - Real-time streaming display with ThinkingIndicator widget
  - Collapsible thinking sections in final message bubbles

- 📦 **ThinkingDetector SDK module** (`consoul.sdk.thinking`)
  - Stateless detection of thinking tag boundaries
  - Content extraction separating reasoning from answers
  - Suitable for headless and TUI usage

- ⚙️ **Configurable system prompt tools** (SOUL-272)
  - `include_tools` config option to control tool documentation
  - Prevents large system prompts from suppressing reasoning behavior
  - Enables minimal prompts for reasoning models

#### Async Streaming Architecture (SOUL-279, SOUL-234)
- 🔄 **Modern async/await streaming**
  - `StreamingOrchestrator` for TUI streaming coordination
  - Async approval workflow for tool execution
  - Configurable approval providers (CLI, TUI, WebSocket)
  - Real-time token collection and display

- 🌐 **WebSocket streaming support** (SOUL-257, SOUL-277)
  - FastAPI proof-of-concept demonstrating SDK independence
  - WebSocket approval provider for remote tool approval
  - Concurrent message handling preventing deadlocks
  - Example implementations in SDK documentation

#### Headless SDK Support (SOUL-251)
- ✨ **`stream_chunks()` function** for UI-agnostic streaming
  - Returns `Iterator[StreamChunk]` with pure data (no UI rendering)
  - Suitable for SDK usage, web backends, and custom presentation layers
  - Example: `for chunk in stream_chunks(model, messages): print(chunk.content)`

- 📦 **StreamChunk model** (`consoul.ai.models.StreamChunk`)
  - Pydantic model for raw streaming data
  - Fields: `content`, `tokens`, `cost`, `metadata`
  - Decoupled from Rich/console dependencies

- 🎨 **`consoul.presentation` package** for optional Rich formatting
  - `display_stream_with_rich()` - Rich-based formatting extracted from streaming
  - Lazy imports - Rich only loaded when presentation layer is used
  - Enables true headless SDK usage without UI library dependencies

#### Enhanced Model Picker (SOUL-276)
- 🎨 **Card-based model picker UI**
  - `EnhancedModelPicker` with model cards showing metadata
  - Provider filtering and search functionality
  - Model registry integration for accurate context windows
  - Local model discovery for Ollama
  - Better UX for browsing 100+ models

#### Documentation & Testing
- 📚 **Service layer API reference** (SOUL-258)
  - Comprehensive SDK service documentation
  - WebSocket streaming examples (SOUL-277)
  - Developer guide updates (SOUL-259)

- ✅ **Comprehensive test coverage**
  - ConversationService unit tests (SOUL-255)
  - ModelService and ToolService tests (SOUL-256)
  - SDK independence integration tests (SOUL-278)
  - Overall test coverage improvements

### Fixed

- 🐛 **IndexError in docs generator** (SOUL-272)
  - Fixed crash when processing empty/whitespace command names
  - Added comprehensive unit tests for edge cases
  - Ensures `consoul describe` works reliably

- 🎨 **Thinking mode UI improvements**
  - Removed black background from thinking collapsible label
  - Fixed thinking content extraction for MessageBubble
  - Proper separation of reasoning from final answers

- 🔧 **Model switching updates**
  - ConversationService now updates model reference correctly
  - Tool execution bugs fixed in SDK services
  - Ollama models without tool support handled gracefully (SOUL-280)

- 🌐 **WebSocket streaming fixes** (SOUL-277)
  - AIMessage serialization for JSON transmission
  - Approval deadlock resolution with concurrent receivers
  - Correct ToolRegistry and approval provider initialization

### Changed

- 🏗️ **TUI refactored to use SDK services** (EPIC-012, SOUL-270)
  - Extracted 1,600+ lines of code from `app.py` to reusable SDK
  - 10-phase refactoring completed over 40+ commits
  - Message submission orchestration (SOUL-270 Phase 9)
  - Streaming widget management extracted
  - Profile and tool approval orchestration separated
  - Conversation loading moved to `ConversationDisplayService`
  - Better separation of concerns and testability

- 📝 **System prompt building** (SOUL-253)
  - Moved to SDK with full programmatic control
  - Profile-based configuration support
  - Tool documentation inclusion now optional

- 🎯 **CLI session orchestration** (SOUL-252, SOUL-254)
  - Extracted from ChatSession to SDK
  - Slash command processor separated
  - Reusable across CLI and TUI

- 📊 **Model registry integration**
  - Replaced static catalog with dynamic registry
  - Accurate pricing and context window data
  - Support for 100+ models across all providers

### Deprecated

- ⚠️ **`stream_response()` deprecated** - will be removed in v1.0.0
  - Use `stream_chunks()` for headless streaming
  - Use `consoul.presentation.display_stream_with_rich()` for Rich formatting
  - Backward compatibility maintained with deprecation warnings

### Migration Guide

**Headless streaming (new SDK approach):**
```python
from consoul.ai import stream_chunks

for chunk in stream_chunks(model, messages):
    print(chunk.content, end="")
```

**CLI/TUI with Rich formatting:**
```python
from consoul.ai import stream_chunks
from consoul.presentation import display_stream_with_rich

chunks = stream_chunks(model, messages)
response_text = display_stream_with_rich(chunks)
```

**Using SDK services:**
```python
from consoul.sdk import ConversationService, ModelService, ToolService

# Initialize services
model_service = ModelService(model, config)
tool_service = ToolService(tool_registry)
conversation_service = ConversationService(
    config=config,
    model_service=model_service,
    tool_service=tool_service
)

# Send message with streaming
async for chunk in conversation_service.send_message_stream("Hello!"):
    print(chunk.content, end="")
```

---

## [0.3.0] - 2025-12-08

**Feature Release - Inline Command Execution**

This release introduces a powerful inline shell command execution feature, allowing users to run shell commands directly from the chat interface and automatically include their output in AI conversations. Also includes security fixes and AI provider improvements.

### Added

#### Inline Command Execution (SOUL-196)
- 🚀 **Inline shell command execution** with `!`-prefix syntax
  - Standalone mode: `!ls -la` executes command and displays output
  - Inline mode: `Here is the file: !`cat README.md`` embeds output in message
  - Support for complex commands with pipes, redirects, and arguments
  - Automatic output truncation for large results (1000 lines for standalone, 10KB for inline)
  - Real-time command execution with visual feedback
  - Exit code display and error handling
  - Syntax-highlighted command output with collapsible sections
  - Structured XML-like context injection for LLM comprehension

- **CommandOutputBubble widget** for displaying command results
  - Success/error indicators with color coding
  - Command syntax highlighting (bash)
  - Combined stdout/stderr display
  - Execution time tracking
  - Exit code status

#### AI Provider Improvements
- 🧠 **Anthropic prompt caching cost tracking** (SOUL-186)
  - Track cache creation and read tokens separately
  - Accurate cost calculation for cached vs non-cached tokens
  - Defensive programming for missing usage metadata

- 🦙 **ChatLlamaCpp context size extraction** (SOUL-231)
  - Runtime extraction of actual n_ctx from loaded models
  - Persistent caching in `~/.consoul/ollama_context_cache.json`
  - Fallback to pattern-based defaults when extraction fails
  - Eliminates manual configuration for context sizes

- 🎯 **Pattern-based intelligent defaults** for new AI models
  - Automatic context size detection based on model name patterns
  - Support for Gemini 2.0, GPT-4o, Claude 3.5, and local models
  - Graceful fallback to conservative defaults

#### TUI Enhancements
- 🔍 **Search configuration improvements** (SOUL-183)
  - Enhanced search metadata and indexing
  - Better result relevance

- ⚠️ **InitializationErrorScreen** (SOUL-192)
  - Graceful handling of TUI initialization failures
  - Clear error messages with recovery suggestions
  - Professional error presentation

#### CLI Enhancements
- 📄 **PDF support** for `--file` and `--glob` flags (SOUL-211)
  - Read and analyze PDF documents
  - Extract text content for AI processing

- 📝 **`--system-file` flag** (SOUL-212)
  - Read system prompts from files
  - Better management of long system instructions

### Fixed

#### Security & Dependencies (SOUL-228)
- 🔒 **Security vulnerability fixes**
  - torch updated to 2.9.1 (CVE-2025-32434, CVE-2025-3730, CVE-2025-2953)
  - urllib3 updated to 2.6.0 (CVE-2025-66471, CVE-2025-66418)
  - Comprehensive dependency security audit

#### AI Provider Fixes
- 🔧 **OpenAI stream_options fix** (SOUL-233)
  - Removed unconditional `stream_options` parameter for non-streaming calls
  - Prevents errors with models that don't support streaming metadata
  - Conditional parameter inclusion only when streaming enabled

#### TUI Fixes
- 🎨 **ProfileEditorModal improvements**
  - Model field made optional in ProfileConfig
  - Temperature field added to profile editor
  - Markdown syntax highlighting for profile editing
  - Better field validation

### Changed
- **Command output display** - Always expanded by default for better UX (previously collapsed for long output)
- **Context injection format** - Improved from delimiters to structured XML-like tags for better LLM comprehension
- **Model field** - Made optional in ProfileConfig for better flexibility

### Documentation
- 📚 **SDK integration guide** for real-world usage
- 📖 **Installation instructions** updated for latest version
- 🎓 **CLI usage examples** added to README
- 📝 **TUI documentation** completed (SOUL-54)
- ⚡ **Performance optimization** documentation completed (SOUL-51)

### Testing
- ✅ **Comprehensive test coverage** for inline command execution
  - 20 unit tests for command detection (standalone and inline modes)
  - Pattern matching validation
  - Edge case handling (empty commands, multiline, special characters)
  - All tests passing

### Performance
- ⚡ **Command execution** - Async execution via thread pool to prevent UI blocking
- ⚡ **Output handling** - Smart truncation for large outputs
- ⚡ **Context caching** - Ollama context sizes cached to avoid repeated extraction

### Developer Experience
- 🛠️ **Better command detection** - Robust regex patterns for standalone vs inline modes
- 🔍 **Improved error messages** - Clear feedback for command failures
- 📊 **Execution metrics** - Time tracking for performance monitoring

### Upgrade Notes
- This release is backward compatible with 0.2.x
- New inline command execution feature requires no configuration changes
- Security updates are strongly recommended (torch, urllib3)
- Configuration location: `~/.config/consoul/config.yaml`
- Conversation history: `~/.local/share/consoul/conversations.db`
- Ollama context cache: `~/.consoul/ollama_context_cache.json`

---

## [0.2.2] - 2025-12-03

**Documentation Fix**

### Changed
- **Installation instructions** - Updated README to show `pip install consoul[tui]` as the recommended installation method, clarifying that the TUI requires optional extras

---

## [0.2.1] - 2025-12-03

**Hotfix Release**

### Fixed
- **Missing dependency** - Added `rich>=14.2.0` as core dependency (was causing import errors in fresh installations)

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
