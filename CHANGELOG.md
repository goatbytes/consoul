# Changelog

All notable changes to Consoul will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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

#### UI/UX Enhancements
- 📁 **File attachment system** with visual file chips in TUI
  - Attach images, code files, documents via 📎 button
  - Support for images, text files, code files
  - Visual file chips with icons and remove buttons
  - File size indicators and validation

- 💾 **Conversation persistence improvements**:
  - Complete UI reconstruction from database
  - Preserve tool calls, file attachments, and multimodal content
  - Historical file chips for reloaded conversations
  - Proper message ordering and threading

### Changed
- **Direct multimodal messaging**: Images now sent directly to vision-capable models without intermediate tool calls
- **Disabled analyze_images tool**: Replaced with direct multimodal HumanMessage approach for better UX

### Fixed
- Token counting hangs with Ollama models (switched from API calls to local tokenizers)
- Conversation UI not reconstructed from database after reload
- Tool call widgets missing when loading historical conversations
- Empty assistant messages not showing bubbles in TUI
- Token estimation performance issues (18+ second delays eliminated)

---

## Previous Releases

*This CHANGELOG was created after the initial release. Previous changes are documented in git history.*

For older changes, see: `git log --oneline --all`
