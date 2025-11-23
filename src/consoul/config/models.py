"""Pydantic configuration models for Consoul.

This module provides strongly-typed configuration models using Pydantic v2,
ensuring validation, type safety, and ease of use across the application.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    field_validator,
    model_serializer,
    model_validator,
)

# Import permission types (lazy import to avoid circular dependency)

if TYPE_CHECKING:
    from consoul.ai.tools.permissions.policy import PermissionPolicy
    from consoul.config.env import EnvSettings
    from consoul.tui.config import TuiConfig
else:
    # Lazy import PermissionPolicy to avoid circular import issues
    # Keep PermissionPolicy as a callable that returns the actual enum
    # This allows the default= to work properly
    try:
        from consoul.ai.tools.permissions.policy import PermissionPolicy
    except ImportError:
        PermissionPolicy = Any  # type: ignore[misc,assignment]

    EnvSettings = Any  # type: ignore[misc,assignment]
    TuiConfig = Any  # type: ignore[misc,assignment]


def _get_tui_config() -> TuiConfig:
    """Lazy import and instantiate TuiConfig to avoid circular imports."""
    from consoul.tui.config import TuiConfig as RealTuiConfig

    return RealTuiConfig()


class Provider(str, Enum):
    """AI provider enumeration."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OLLAMA = "ollama"
    HUGGINGFACE = "huggingface"
    LLAMACPP = "llamacpp"
    MLX = "mlx"


class ProviderConfig(BaseModel):
    """Configuration for a specific AI provider.

    Stores provider-specific settings like API keys, base URLs, and default parameters.
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    api_key_env: str | None = Field(
        default=None,
        description="Environment variable name for API key",
    )
    api_base: str | None = Field(
        default=None,
        description="Custom API base URL",
    )
    default_temperature: float = Field(
        default=1.0,
        ge=0.0,
        le=2.0,
        description="Default sampling temperature",
    )
    default_max_tokens: int | None = Field(
        default=None,
        gt=0,
        description="Default maximum tokens to generate",
    )
    timeout: int = Field(
        default=30,
        gt=0,
        description="Request timeout in seconds",
    )


class BaseModelConfig(BaseModel):
    """Base configuration for AI model parameters shared across all providers."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    model: str = Field(
        description="Model name/ID",
    )
    temperature: float = Field(
        default=1.0,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0-2.0)",
    )
    max_tokens: int | None = Field(
        default=None,
        gt=0,
        description="Maximum tokens to generate",
    )
    stop_sequences: list[str] | None = Field(
        default=None,
        description="Stop sequences for generation",
    )

    @field_validator("model")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        """Validate model name is not empty."""
        if not v or not v.strip():
            raise ValueError("Model name cannot be empty")
        return v.strip()


class OpenAIModelConfig(BaseModelConfig):
    """OpenAI-specific model configuration."""

    provider: Literal[Provider.OPENAI] = Provider.OPENAI
    top_p: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter (0.0-1.0)",
    )
    frequency_penalty: float | None = Field(
        default=None,
        ge=-2.0,
        le=2.0,
        description="Frequency penalty (-2.0 to 2.0)",
    )
    presence_penalty: float | None = Field(
        default=None,
        ge=-2.0,
        le=2.0,
        description="Presence penalty (-2.0 to 2.0)",
    )
    seed: int | None = Field(
        default=None,
        description="Seed for deterministic sampling (beta feature)",
    )
    logit_bias: dict[str, float] | None = Field(
        default=None,
        description="Modify likelihood of specific tokens appearing",
    )
    response_format: dict[str, Any] | None = Field(
        default=None,
        description="Response format (e.g., {'type': 'json_object'} or {'type': 'json_schema', 'json_schema': {...}})",
    )


class AnthropicModelConfig(BaseModelConfig):
    """Anthropic-specific model configuration."""

    provider: Literal[Provider.ANTHROPIC] = Provider.ANTHROPIC
    top_p: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter (0.0-1.0)",
    )
    top_k: int | None = Field(
        default=None,
        gt=0,
        description="Top-k sampling parameter (Anthropic-specific)",
    )
    thinking: dict[str, Any] | None = Field(
        default=None,
        description="Extended thinking configuration (type, budget_tokens)",
    )
    betas: list[str] | None = Field(
        default=None,
        description="Experimental features (e.g., files-api-2025-04-14, token-efficient-tools-2025-02-19)",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Metadata for run tracing",
    )


class GoogleModelConfig(BaseModelConfig):
    """Google Gemini-specific model configuration."""

    provider: Literal[Provider.GOOGLE] = Provider.GOOGLE
    top_p: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter (0.0-1.0)",
    )
    top_k: int | None = Field(
        default=None,
        gt=0,
        description="Top-k sampling parameter",
    )
    candidate_count: int | None = Field(
        default=None,
        gt=0,
        description="Number of chat completions to generate for each prompt",
    )
    safety_settings: dict[str, str] | None = Field(
        default=None,
        description="Safety settings for content filtering (HarmCategory -> HarmBlockThreshold)",
    )
    generation_config: dict[str, Any] | None = Field(
        default=None,
        description="Generation configuration (e.g., response_modalities)",
    )


class OllamaModelConfig(BaseModelConfig):
    """Ollama-specific model configuration for local models."""

    provider: Literal[Provider.OLLAMA] = Provider.OLLAMA
    top_p: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter (0.0-1.0)",
    )
    top_k: int | None = Field(
        default=None,
        gt=0,
        description="Top-k sampling parameter",
    )


class HuggingFaceModelConfig(BaseModelConfig):
    """HuggingFace-specific model configuration.

    Supports both HuggingFaceEndpoint (API-based) and HuggingFacePipeline
    (local model execution) configuration parameters.
    """

    provider: Literal[Provider.HUGGINGFACE] = Provider.HUGGINGFACE
    task: (
        Literal[
            "text-generation",
            "text2text-generation",
            "summarization",
        ]
        | None
    ) = Field(
        default="text-generation",
        description="HuggingFace task type",
    )
    max_new_tokens: int | None = Field(
        default=512,
        gt=0,
        le=4096,
        description="Maximum new tokens to generate",
    )
    do_sample: bool = Field(
        default=True,
        description="Enable sampling (vs greedy decoding)",
    )
    repetition_penalty: float | None = Field(
        default=None,
        ge=1.0,
        le=2.0,
        description="Repetition penalty (1.0 = no penalty)",
    )
    top_p: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter (0.0-1.0)",
    )
    top_k: int | None = Field(
        default=None,
        gt=0,
        description="Top-k sampling parameter",
    )
    model_kwargs: dict[str, Any] | None = Field(
        default=None,
        description="Additional model-specific kwargs",
    )
    local: bool = Field(
        default=False,
        description="Use local model execution (HuggingFacePipeline) instead of API",
    )
    device: str | None = Field(
        default=None,
        description="Device for local execution (e.g., 'cuda', 'cpu', 'mps')",
    )
    quantization: Literal["4bit", "8bit"] | None = Field(
        default=None,
        description="Quantization mode for local models (requires bitsandbytes)",
    )


class LlamaCppModelConfig(BaseModelConfig):
    """Llama.cpp-specific model configuration.

    Uses llama-cpp-python for local GGUF model execution. Recommended for
    macOS as it provides reliable local execution with Metal GPU acceleration.
    """

    provider: Literal[Provider.LLAMACPP] = Provider.LLAMACPP
    model_path: str | None = Field(
        default=None,
        description="Path to GGUF model file (auto-detected if None)",
    )
    n_ctx: int = Field(
        default=4096,
        gt=0,
        le=131072,
        description="Context window size (tokens)",
    )
    n_gpu_layers: int = Field(
        default=-1,
        description="Number of layers to offload to GPU (-1 = all, 0 = CPU only)",
    )
    n_batch: int = Field(
        default=512,
        gt=0,
        description="Batch size for prompt processing",
    )
    n_threads: int | None = Field(
        default=None,
        description="Number of CPU threads (auto-detected if None)",
    )
    use_mlock: bool = Field(
        default=False,
        description="Keep model in RAM (prevents swapping)",
    )
    use_mmap: bool = Field(
        default=True,
        description="Use memory-mapped file for model (faster loading)",
    )


class MLXModelConfig(BaseModelConfig):
    """MLX-specific model configuration.

    Uses Apple's MLX framework for local model execution on Apple Silicon.
    Provides optimal performance on M-series Macs without PyTorch dependencies.
    """

    provider: Literal[Provider.MLX] = Provider.MLX
    model_path: str | None = Field(
        default=None,
        description="HuggingFace model ID or local path (e.g., mlx-community/quantized-gemma-2b-it)",
    )
    max_tokens: int = Field(
        default=2048,
        gt=0,
        description="Maximum tokens to generate",
    )
    temp: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature",
    )
    top_p: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling probability",
    )
    repetition_penalty: float = Field(
        default=1.0,
        ge=0.0,
        description="Repetition penalty (1.0 = no penalty)",
    )


# Type alias for discriminated union of all model configs
ModelConfigUnion = Annotated[
    OpenAIModelConfig
    | AnthropicModelConfig
    | GoogleModelConfig
    | OllamaModelConfig
    | HuggingFaceModelConfig
    | LlamaCppModelConfig
    | MLXModelConfig,
    Field(discriminator="provider"),
]

# For backward compatibility in tests and simpler usage
ModelConfig = ModelConfigUnion


class ConversationConfig(BaseModel):
    """Configuration for conversation management and persistence."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    persist: bool = Field(
        default=True,
        description="Enable SQLite persistence for conversation history",
    )
    db_path: Path = Field(
        default=Path.home() / ".consoul" / "history.db",
        description="Path to SQLite database file for conversation history",
    )
    auto_resume: bool = Field(
        default=False,
        description="Automatically resume the last conversation on startup",
    )
    retention_days: int = Field(
        default=0,
        ge=0,
        description="Auto-delete conversations older than N days (0 = keep forever)",
    )

    # Summarization settings
    summarize: bool = Field(
        default=False,
        description="Enable automatic conversation summarization for context compression",
    )
    summarize_threshold: int = Field(
        default=20,
        gt=0,
        description="Trigger summarization after this many messages",
    )
    keep_recent: int = Field(
        default=10,
        gt=0,
        description="Number of recent messages to keep verbatim when summarizing",
    )
    summary_model: str | None = Field(
        default=None,
        description="Optional separate model name for summarization (use cheaper model)",
    )

    @field_validator("db_path", mode="before")
    @classmethod
    def expand_path(cls, v: Any) -> Path:
        """Expand user path and convert to Path object."""
        if isinstance(v, str):
            return Path(v).expanduser()
        return Path(v) if not isinstance(v, Path) else v


class ContextConfig(BaseModel):
    """Configuration for context management."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    max_context_tokens: int = Field(
        default=0,
        ge=0,
        description="Maximum number of tokens for context (0 = auto-size to 75% of model capacity)",
    )
    include_system_info: bool = Field(
        default=True,
        description="Include system information in context",
    )
    include_git_info: bool = Field(
        default=True,
        description="Include git repository information in context",
    )
    custom_context_files: list[Path] = Field(
        default_factory=list,
        description="Additional context files to include",
    )

    @field_validator("custom_context_files", mode="before")
    @classmethod
    def expand_paths(cls, v: Any) -> list[Path]:
        """Expand user paths and convert to Path objects.

        Accepts:
        - List or tuple of strings/Paths
        - Single string (converted to single-item list)
        - Single Path (converted to single-item list)
        - None or empty (returns empty list)
        """
        if not v:
            return []
        # Handle single string or Path
        if isinstance(v, (str, Path)):
            path = Path(v).expanduser() if isinstance(v, str) else v.expanduser()
            return [path]
        # Handle list/tuple
        if isinstance(v, (list, tuple)):
            return [Path(p).expanduser() if isinstance(p, str) else p for p in v]
        # Invalid type
        raise ValueError(
            f"custom_context_files must be a string, Path, or list/tuple of strings/Paths, "
            f"got {type(v).__name__}"
        )


class BashToolConfig(BaseModel):
    """Configuration for bash tool execution.

    Controls security, timeouts, and command blocking/whitelisting for bash tool.

    Example:
        >>> config = BashToolConfig(
        ...     timeout=30,
        ...     working_directory="/tmp",
        ...     allow_dangerous=False,
        ...     whitelist_patterns=["git status", "npm test"]
        ... )
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    timeout: int = Field(
        default=30,
        gt=0,
        le=600,
        description="Default timeout for bash commands in seconds (max 10 minutes)",
    )
    working_directory: str | None = Field(
        default=None,
        description="Default working directory for bash commands (None = current directory)",
    )
    blocked_patterns: list[str] = Field(
        default_factory=lambda: [
            r"^sudo\s",  # sudo commands
            r"rm\s+(-[rf]+\s+)?/",  # rm with root paths
            r"dd\s+if=",  # disk operations
            r"chmod\s+777",  # dangerous permissions
            r":\(\)\{.*:\|:.*\};:",  # fork bomb
            r"wget.*\|.*bash",  # download-and-execute
            r"curl.*\|.*sh",  # download-and-execute
            r">\s*/dev/sd[a-z]",  # write to disk devices
            r"mkfs",  # format filesystem
            r"fdisk",  # partition operations
        ],
        description="Regex patterns for blocked commands",
    )
    whitelist_patterns: list[str] = Field(
        default_factory=list,
        description="Command patterns that bypass approval (exact matches or regex patterns)",
    )
    allow_dangerous: bool = Field(
        default=False,
        description="DANGEROUS: Disable command blocking (for testing only)",
    )

    @field_validator("allow_dangerous")
    @classmethod
    def validate_allow_dangerous(cls, v: bool) -> bool:
        """Validate allow_dangerous is not enabled (security check)."""
        if v:
            import warnings

            warnings.warn(
                "allow_dangerous=True is DANGEROUS and disables command blocking. "
                "This should ONLY be used in testing environments.",
                UserWarning,
                stacklevel=2,
            )
        return v


class GrepSearchToolConfig(BaseModel):
    """Configuration for grep_search tool execution.

    Controls timeouts for text search operations using ripgrep or grep.

    Example:
        >>> config = GrepSearchToolConfig(
        ...     timeout=60,
        ... )
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    timeout: int = Field(
        default=30,
        gt=0,
        le=600,
        description="Default timeout for search operations in seconds (max 10 minutes)",
    )


class CodeSearchToolConfig(BaseModel):
    """Configuration for code_search tool execution.

    Controls AST-based code structure search behavior and performance limits.

    Example:
        >>> config = CodeSearchToolConfig(
        ...     max_file_size_kb=2048,
        ... )
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    max_file_size_kb: int = Field(
        default=1024,
        gt=0,
        le=10240,
        description="Maximum file size to parse in KB (skip larger files, max 10MB)",
    )
    supported_extensions: list[str] = Field(
        default_factory=lambda: [
            ".py",
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
            ".go",
            ".rs",
            ".java",
            ".kt",
            ".c",
            ".cpp",
            ".h",
            ".hpp",
        ],
        description="File extensions supported for AST parsing",
    )


class FindReferencesToolConfig(BaseModel):
    """Configuration for find_references tool execution.

    Controls symbol reference finding behavior and performance limits.

    Example:
        >>> config = FindReferencesToolConfig(
        ...     max_file_size_kb=2048,
        ...     max_results=200,
        ... )
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    max_file_size_kb: int = Field(
        default=1024,
        gt=0,
        le=10240,
        description="Maximum file size to parse in KB (skip larger files, max 10MB)",
    )
    max_results: int = Field(
        default=100,
        gt=0,
        le=1000,
        description="Maximum number of references to return (prevents overflow)",
    )
    supported_extensions: list[str] = Field(
        default_factory=lambda: [
            ".py",
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
            ".go",
            ".rs",
            ".java",
            ".kt",
            ".c",
            ".cpp",
            ".h",
            ".hpp",
        ],
        description="File extensions supported for reference finding",
    )


class WebSearchToolConfig(BaseModel):
    """Configuration for web_search tool execution.

    Supports three backends with automatic fallback priority:
    1. Jina AI Search (LLM-optimized, requires free API key) - Best quality
    2. SearxNG (self-hosted, production-grade) - Privacy and control
    3. DuckDuckGo (zero setup) - No configuration needed

    Example:
        >>> # DuckDuckGo only (zero setup)
        >>> config = WebSearchToolConfig(
        ...     max_results=10,
        ...     safesearch="strict",
        ... )
        >>>
        >>> # Jina Search with fallback
        >>> config = WebSearchToolConfig(
        ...     jina_api_key="your-api-key",
        ...     max_results=5,
        ... )
        >>>
        >>> # All three backends configured
        >>> config = WebSearchToolConfig(
        ...     jina_api_key="your-api-key",
        ...     searxng_url="http://localhost:8888",
        ...     searxng_engines=["google", "github", "arxiv"],
        ...     max_results=10,
        ... )
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    # Common settings
    max_results: int = Field(
        default=5,
        gt=0,
        le=10,
        description="Maximum number of search results to return (1-10)",
    )
    timeout: int = Field(
        default=10,
        gt=0,
        le=30,
        description="Request timeout in seconds (max 30s)",
    )

    # DuckDuckGo settings (used as fallback or standalone)
    region: str = Field(
        default="wt-wt",
        description="Region code for DuckDuckGo search results (default 'wt-wt' for global)",
    )
    safesearch: Literal["strict", "moderate", "off"] = Field(
        default="moderate",
        description="SafeSearch filter level for DuckDuckGo",
    )

    # SearxNG settings (optional, enterprise-grade)
    searxng_url: str | None = Field(
        default=None,
        description="SearxNG instance URL (e.g., 'http://localhost:8888'). If None, uses DuckDuckGo only.",
    )
    searxng_engines: list[str] = Field(
        default_factory=lambda: ["google", "duckduckgo", "bing"],
        description="Default SearxNG engines to use when searxng_url is configured",
    )
    enable_engine_selection: bool = Field(
        default=True,
        description="Allow users to specify custom engines via tool parameters (SearxNG only)",
    )
    enable_categories: bool = Field(
        default=True,
        description="Allow users to specify search categories like 'it', 'news' (SearxNG only)",
    )
    searxng_verify_ssl: bool = Field(
        default=False,
        description="Verify SSL certificates for SearxNG requests. Set to False for self-signed certificates.",
    )

    # Jina Search settings (optional, best quality)
    jina_api_key: str | None = Field(
        default=None,
        description="Jina AI API key for semantic search (get free key at jina.ai, 10M tokens free)",
    )
    jina_enabled: bool = Field(
        default=True,
        description="Enable Jina Search when API key is present (highest priority backend)",
    )


class ReadUrlToolConfig(BaseModel):
    """Configuration for read_url tool execution.

    Reads web pages and converts them to LLM-ready markdown using Jina AI Reader
    (primary) with trafilatura fallback. Zero configuration for basic usage.

    Example:
        >>> # Basic usage (no API key, 20 RPM free tier)
        >>> config = ReadUrlToolConfig()
        >>>
        >>> # With Jina API key (500 RPM free tier)
        >>> config = ReadUrlToolConfig(
        ...     jina_api_key="jina_xxx",
        ... )
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    # Jina Reader settings (optional, best quality)
    jina_api_key: str | None = Field(
        default=None,
        description="Jina AI API key for higher rate limits (500 RPM vs 20 RPM). Get free key at jina.ai",
    )

    # Common settings
    timeout: int = Field(
        default=10,
        gt=0,
        le=30,
        description="Request timeout in seconds (max 30s)",
    )

    # Fallback settings
    enable_fallback: bool = Field(
        default=True,
        description="Enable trafilatura fallback if Jina fails or is unavailable",
    )

    # Output settings
    max_length: int = Field(
        default=50000,
        gt=0,
        description="Maximum output length in characters (content will be truncated)",
    )


class WikipediaToolConfig(BaseModel):
    """Configuration for wikipedia_search tool execution.

    Fetches Wikipedia article summaries using the public Wikipedia API.
    No API key required. Useful for factual queries about people, places,
    companies, historical events, and technical concepts.

    Example:
        >>> # Basic usage (1 article, 1000 chars)
        >>> config = WikipediaToolConfig()
        >>>
        >>> # Multiple articles with more detail
        >>> config = WikipediaToolConfig(
        ...     max_results=3,
        ...     chars_per_result=2000,
        ... )
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    max_results: int = Field(
        default=1,
        gt=0,
        le=5,
        description="Number of Wikipedia articles to fetch (1-5)",
    )
    chars_per_result: int = Field(
        default=1000,
        gt=0,
        le=4000,
        description="Character limit per article summary (1-4000)",
    )
    timeout: int = Field(
        default=10,
        gt=0,
        le=30,
        description="Request timeout in seconds (max 30s)",
    )


class ReadToolConfig(BaseModel):
    """Configuration for read file tool.

    Controls file reading behavior, security, and output limits.
    Supports text files, PDFs, and various encodings with security controls
    to prevent reading sensitive system files.

    Example:
        >>> config = ReadToolConfig(
        ...     max_lines_default=2000,
        ...     max_line_length=2000,
        ...     enable_pdf=True,
        ...     blocked_paths=["/etc/shadow", "/proc"]
        ... )
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    max_lines_default: int = Field(
        default=2000,
        gt=0,
        le=10000,
        description="Default maximum lines to read (prevents context overflow)",
    )
    max_line_length: int = Field(
        default=2000,
        gt=0,
        description="Maximum characters per line before truncation",
    )
    max_output_chars: int = Field(
        default=40000,
        gt=0,
        description="Maximum total characters in output",
    )
    allowed_extensions: list[str] = Field(
        default_factory=lambda: [
            "",  # Extensionless files (Dockerfile, Makefile, LICENSE, etc.)
            ".py",
            ".md",
            ".txt",
            ".json",
            ".yaml",
            ".yml",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".java",
            ".kt",
            ".go",
            ".rs",
            ".c",
            ".cpp",
            ".h",
            ".hpp",
            ".sh",
            ".bash",
            ".zsh",
            ".fish",
            ".toml",
            ".ini",
            ".cfg",
            ".conf",
            ".xml",
            ".html",
            ".css",
            ".scss",
            ".sql",
            ".gradle",
            ".properties",
            ".pdf",  # Special handling
        ],
        description="Allowed file extensions (empty list = allow all, empty string '' = extensionless files)",
    )
    blocked_paths: list[str] = Field(
        default_factory=lambda: [
            "/etc/shadow",
            "/etc/passwd",
            "/proc",
            "/dev",
            "/sys",
        ],
        description="File paths/prefixes that cannot be read (security)",
    )
    enable_pdf: bool = Field(
        default=True,
        description="Enable PDF text extraction (requires PyPDF2 or pdfplumber)",
    )
    pdf_max_pages: int = Field(
        default=50,
        gt=0,
        le=500,
        description="Maximum PDF pages to read",
    )


class ImageAnalysisToolConfig(BaseModel):
    """Configuration for image analysis tool.

    Controls image analysis behavior, security, and limits for multimodal AI
    vision capabilities. Supports analyzing screenshots, diagrams, UI mockups,
    and other visual content using vision-capable LLM providers.

    Security features:
    - File size limits prevent large uploads
    - Extension filtering ensures only image files
    - Path blocking prevents access to sensitive directories
    - Magic byte validation prevents extension spoofing

    Example:
        >>> config = ImageAnalysisToolConfig(
        ...     enabled=True,
        ...     auto_detect_in_messages=True,
        ...     max_image_size_mb=5,
        ...     max_images_per_query=5,
        ...     allowed_extensions=[".png", ".jpg", ".jpeg", ".gif", ".webp"]
        ... )
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    enabled: bool = Field(
        default=True,
        description="Enable image analysis tool (requires vision-capable model)",
    )
    auto_detect_in_messages: bool = Field(
        default=True,
        description=(
            "Automatically detect and analyze image paths in user messages. "
            "When enabled, typing 'describe screenshot.png' will directly send "
            "the image to the vision model. When disabled, users must use the "
            "analyze_images tool explicitly or attach images via the UI."
        ),
    )
    max_image_size_mb: int = Field(
        default=5,
        gt=0,
        le=20,
        description="Maximum image file size in megabytes",
    )
    max_images_per_query: int = Field(
        default=5,
        gt=0,
        le=10,
        description="Maximum number of images per analysis request",
    )
    allowed_extensions: list[str] = Field(
        default_factory=lambda: [
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".webp",
            ".bmp",
        ],
        description="Allowed image file extensions",
    )
    blocked_paths: list[str] = Field(
        default_factory=lambda: [
            "/etc",
            "/proc",
            "/dev",
            "/sys",
            "~/.ssh",
            "~/.aws",
            "~/.config",
        ],
        description="File paths/prefixes that cannot be read (security)",
    )


class FileEditToolConfig(BaseModel):
    """Configuration for file editing tools.

    Controls security, validation, and operational limits for file editing operations
    including edit_file_lines, edit_file_search_replace, create_file, delete_file,
    and append_to_file.

    Security features:
    - Extension allowlisting prevents editing dangerous file types
    - Path blocking prevents editing sensitive system files
    - Payload size limits prevent memory exhaustion
    - Edit count limits prevent runaway LLM modifications

    Example:
        >>> config = FileEditToolConfig(
        ...     max_edits=25,
        ...     max_payload_bytes=524288,  # 512KB
        ...     allow_overwrite=True,
        ...     allowed_extensions=[".py", ".md", ".txt"]
        ... )
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    allowed_extensions: list[str] = Field(
        default_factory=lambda: [
            "",  # Extensionless files (Dockerfile, Makefile, LICENSE, etc.)
            ".py",
            ".md",
            ".txt",
            ".json",
            ".yaml",
            ".yml",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".java",
            ".kt",
            ".go",
            ".rs",
            ".c",
            ".cpp",
            ".h",
            ".hpp",
            ".sh",
            ".bash",
            ".zsh",
            ".fish",
            ".toml",
            ".ini",
            ".cfg",
            ".conf",
            ".xml",
            ".html",
            ".css",
            ".scss",
            ".sql",
            ".gradle",
            ".properties",
        ],
        description="File extensions allowed for editing (empty list = allow all, empty string '' = extensionless files)",
    )
    blocked_paths: list[str] = Field(
        default_factory=lambda: [
            "/etc/shadow",
            "/etc/passwd",
            "/proc",
            "/dev",
            "/sys",
        ],
        description="File paths/prefixes that cannot be edited (security)",
    )
    max_edits: int = Field(
        default=50,
        gt=0,
        le=100,
        description="Maximum number of edit operations per tool call (prevents runaway LLM edits)",
    )
    max_payload_bytes: int = Field(
        default=1048576,  # 1MB
        gt=0,
        description="Maximum total bytes for edit payloads (prevents memory exhaustion)",
    )
    default_encoding: str = Field(
        default="utf-8",
        description="Default text encoding for file operations",
    )
    allow_overwrite: bool = Field(
        default=False,
        description="Allow create_file to overwrite existing files (requires approval)",
    )
    timeout: int = Field(
        default=30,
        gt=0,
        le=600,
        description="Default timeout for file edit operations in seconds (max 10 minutes)",
    )


class ToolConfig(BaseModel):
    """Configuration for tool calling system.

    Controls tool execution behavior, security policies, and approval workflows.
    This configuration is SDK-level (not TUI-specific) to support headless usage.

    Supports both predefined permission policies and manual configuration:
    - Use permission_policy for preset security postures (PARANOID/BALANCED/TRUSTING/UNRESTRICTED)
    - Use manual settings (approval_mode, auto_approve) for custom configurations
    - Policy takes precedence over manual settings when both are specified

    Example (with policy):
        >>> from consoul.ai.tools.permissions import PermissionPolicy
        >>> config = ToolConfig(
        ...     enabled=True,
        ...     permission_policy=PermissionPolicy.BALANCED
        ... )

    Example (manual):
        >>> config = ToolConfig(
        ...     enabled=True,
        ...     approval_mode="always",
        ...     allowed_tools=["bash"]
        ... )
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    enabled: bool = Field(
        default=True,
        description="Enable tool calling system (master switch)",
    )
    permission_policy: PermissionPolicy | None = Field(
        default=None,  # Will be set to BALANCED in model_validator if not specified
        description="Predefined permission policy (overrides approval_mode/auto_approve when set). "
        "Set to None to use manual settings.",
    )
    auto_approve: bool = Field(
        default=False,
        description="DANGEROUS: Auto-approve all tool executions (NEVER set to True in production). "
        "Ignored if permission_policy is set.",
    )
    allowed_tools: list[str] = Field(
        default_factory=list,
        description="Whitelist of allowed tools (empty = all tools allowed with approval)",
    )
    approval_mode: Literal[
        "always", "once_per_session", "whitelist", "risk_based", "never"
    ] = Field(
        default="always",
        description="When to request approval: 'always' (every execution), 'once_per_session' (first use only), "
        "'whitelist' (only for non-whitelisted tools), 'risk_based' (based on risk level), "
        "'never' (auto-approve all - DANGEROUS). Ignored if permission_policy is set.",
    )
    timeout: int = Field(
        default=30,
        gt=0,
        le=600,
        description="Default timeout for tool execution in seconds (max 10 minutes). "
        "NOTE: This field is deprecated in favor of tool-specific timeout configs (e.g., bash.timeout). "
        "Individual tools should use their own timeout configuration.",
    )
    bash: BashToolConfig = Field(
        default_factory=BashToolConfig,
        description="Bash tool-specific configuration",
    )
    grep_search: GrepSearchToolConfig = Field(
        default_factory=GrepSearchToolConfig,
        description="Grep search tool-specific configuration",
    )
    code_search: CodeSearchToolConfig = Field(
        default_factory=CodeSearchToolConfig,
        description="Code search tool-specific configuration",
    )
    find_references: FindReferencesToolConfig = Field(
        default_factory=FindReferencesToolConfig,
        description="Find references tool-specific configuration",
    )
    web_search: WebSearchToolConfig = Field(
        default_factory=WebSearchToolConfig,
        description="Web search tool-specific configuration",
    )
    wikipedia: WikipediaToolConfig = Field(
        default_factory=WikipediaToolConfig,
        description="Wikipedia search tool-specific configuration",
    )
    read_url: ReadUrlToolConfig = Field(
        default_factory=ReadUrlToolConfig,
        description="Read URL tool-specific configuration",
    )
    read: ReadToolConfig = Field(
        default_factory=ReadToolConfig,
        description="Read file tool-specific configuration",
    )
    file_edit: FileEditToolConfig = Field(
        default_factory=FileEditToolConfig,
        description="File editing tools configuration",
    )
    image_analysis: ImageAnalysisToolConfig = Field(
        default_factory=ImageAnalysisToolConfig,
        description="Image analysis tool configuration (multimodal vision)",
    )
    audit_logging: bool = Field(
        default=True,
        description="Enable audit logging of tool executions (requests, approvals, results, errors)",
    )
    audit_log_file: Path = Field(
        default=Path.home() / ".consoul" / "tool_audit.jsonl",
        description="Path to audit log file in JSONL format (one JSON event per line)",
    )

    @field_validator("auto_approve")
    @classmethod
    def validate_auto_approve(cls, v: bool) -> bool:
        """Validate auto_approve is not enabled (security check).

        Raises a warning in logs if auto_approve is True, but allows it
        for testing purposes. Production code should never set this to True.
        """
        if v:
            import warnings

            warnings.warn(
                "auto_approve=True is DANGEROUS and should NEVER be used in production. "
                "All tool executions will be approved automatically without user confirmation.",
                UserWarning,
                stacklevel=2,
            )
        return v

    @model_validator(mode="after")
    def validate_permission_policy(self) -> ToolConfig:
        """Validate permission policy and warn about dangerous configurations.

        Checks for UNRESTRICTED policy and warns about security implications.
        Also validates that policy settings are consistent.
        Sets default policy to BALANCED if not specified.
        """
        # Lazy import to avoid circular dependency
        from consoul.ai.tools.permissions.policy import PermissionPolicy

        # Set default policy to BALANCED if not specified
        if self.permission_policy is None:
            self.permission_policy = PermissionPolicy.BALANCED

        if self.permission_policy == PermissionPolicy.UNRESTRICTED:
            import warnings

            warnings.warn(
                "UNRESTRICTED policy is DANGEROUS and should ONLY be used in testing environments. "
                "All tool executions will be auto-approved without user confirmation.",
                UserWarning,
                stacklevel=2,
            )

        return self


class ProfileConfig(BaseModel):
    """Configuration profile with conversation and context settings.

    Profiles define HOW to use AI (system prompts, context, conversation settings),
    not WHICH AI to use (model/provider are configured separately).
    """

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    name: str = Field(
        description="Profile name",
        examples=["default", "creative", "code-review", "fast"],
    )
    description: str = Field(
        description="Profile description",
    )
    system_prompt: str | None = Field(
        default=None,
        description="Custom system prompt for this profile",
    )
    conversation: ConversationConfig = Field(
        default_factory=ConversationConfig,
        description="Conversation configuration",
    )
    context: ContextConfig = Field(
        default_factory=ContextConfig,
        description="Context configuration",
    )

    @field_validator("name")
    @classmethod
    def validate_profile_name(cls, v: str) -> str:
        """Validate profile name."""
        if not v or not v.strip():
            raise ValueError("Profile name cannot be empty")
        # Profile names should be valid identifiers
        if not v.replace("-", "_").replace("_", "").isalnum():
            raise ValueError(
                "Profile name must contain only alphanumeric characters, hyphens, or underscores"
            )
        return v.strip().lower()


class ConsoulConfig(BaseModel):
    """Root configuration for Consoul application.

    This is the main configuration model that contains all settings.
    Profiles define HOW to use AI (prompts, settings).
    Provider/model define WHICH AI to use (tracked separately).
    """

    model_config = ConfigDict(
        extra="forbid",  # Reject unknown fields to catch typos and enforce schema
        validate_assignment=True,
        arbitrary_types_allowed=True,  # Allow EnvSettings type
    )

    profiles: dict[str, ProfileConfig] = Field(
        description="Available configuration profiles",
    )
    active_profile: str = Field(
        default="default",
        description="Currently active profile name",
    )
    current_provider: Provider = Field(
        default=Provider.ANTHROPIC,
        description="Currently active AI provider",
    )
    current_model: str = Field(
        default="claude-sonnet-4-5-20250929",
        description="Currently active model name",
    )
    provider_configs: dict[Provider, ProviderConfig] = Field(
        default_factory=dict,
        description="Per-provider configuration settings",
    )
    api_keys: dict[str, SecretStr] = Field(
        default_factory=dict,
        description="API keys for providers (runtime only, never serialized)",
    )
    env_settings: EnvSettings | None = Field(
        default=None,
        exclude=True,
        description="Environment settings for lazy API key loading",
    )
    tui: TuiConfig = Field(
        default_factory=lambda: _get_tui_config(),
        description="TUI-specific settings (only loaded when TUI module is used)",
    )
    tools: ToolConfig = Field(
        default_factory=ToolConfig,
        description="Tool calling configuration (SDK-level, not TUI-specific)",
    )
    show_thinking: Literal["always", "auto", "never", "collapsed"] = Field(
        default="auto",
        description="Control display of AI reasoning/thinking blocks. "
        "'always' = show for all responses, "
        "'auto' = show only for known reasoning models, "
        "'never' = extract but don't display, "
        "'collapsed' = show but collapsed by default",
    )
    thinking_models: list[str] = Field(
        default_factory=lambda: [
            "qwq",
            "deepseek-r1",
            "deepseek",
            "phi4-reasoning",
            "cogito",
        ],
        description="Model name patterns known to produce reasoning/thinking output. "
        "Used with show_thinking='auto' to auto-detect reasoning models.",
    )
    global_settings: dict[str, Any] = Field(
        default_factory=dict,
        description="Global settings for extensibility",
    )

    @field_validator("active_profile")
    @classmethod
    def validate_active_profile(cls, v: str) -> str:
        """Validate active profile name is not empty."""
        if not v or not v.strip():
            raise ValueError("Active profile name cannot be empty")
        return v.strip().lower()

    @model_validator(mode="after")
    def validate_active_profile_exists(self) -> ConsoulConfig:
        """Validate that the active profile exists in profiles."""
        if self.active_profile not in self.profiles:
            raise ValueError(
                f"Active profile '{self.active_profile}' not found in profiles. "
                f"Available profiles: {', '.join(self.profiles.keys())}"
            )
        return self

    @model_serializer(mode="wrap")
    def serialize_model(self, serializer: Any) -> dict[str, Any]:
        """Custom serializer to exclude API keys from all serialization modes.

        This ensures API keys are never leaked via model_dump(), YAML export,
        or any other serialization path.
        """
        data: dict[str, Any] = serializer(self)
        # Remove api_keys from serialized output for security
        data.pop("api_keys", None)
        return data

    def get_active_profile(self) -> ProfileConfig:
        """Get the currently active profile configuration.

        Returns:
            The active ProfileConfig instance.

        Raises:
            KeyError: If the active profile doesn't exist.
        """
        return self.profiles[self.active_profile]

    def get_current_model_config(self) -> ModelConfig:
        """Build ModelConfig from current_provider and current_model.

        Returns:
            Appropriate ModelConfig subclass based on current provider.
        """
        # Get provider-specific settings, or use defaults
        provider_config = self.provider_configs.get(
            self.current_provider, ProviderConfig()
        )

        # Build base model parameters
        model_params: dict[str, Any] = {
            "model": self.current_model,
            "temperature": provider_config.default_temperature,
        }

        # Only include max_tokens if it's set (some providers default to None)
        if provider_config.default_max_tokens is not None:
            model_params["max_tokens"] = provider_config.default_max_tokens

        # Return appropriate ModelConfig subclass based on provider
        if self.current_provider == Provider.OPENAI:
            return OpenAIModelConfig(**model_params)
        elif self.current_provider == Provider.ANTHROPIC:
            return AnthropicModelConfig(**model_params)
        elif self.current_provider == Provider.GOOGLE:
            return GoogleModelConfig(**model_params)
        elif self.current_provider == Provider.HUGGINGFACE:
            # Check if model is available locally in cache
            # This allows using cached models without an API key
            is_local = False
            try:
                from consoul.ai.providers import get_huggingface_local_models

                local_models = get_huggingface_local_models()
                is_local = any(m["name"] == self.current_model for m in local_models)
            except Exception:
                # If check fails, default to False (requires API key)
                pass

            model_params["local"] = is_local

            return HuggingFaceModelConfig(**model_params)
        elif self.current_provider == Provider.LLAMACPP:
            # Llama.cpp uses GGUF files
            # Model path will be auto-detected from cache if not specified
            return LlamaCppModelConfig(**model_params)
        elif self.current_provider == Provider.MLX:
            # MLX uses HuggingFace model IDs from mlx-community
            # Falls back to model_path if specified
            # If model looks like a file path, set it as model_path
            if "/" in self.current_model or "\\" in self.current_model:
                model_params["model_path"] = self.current_model
            return MLXModelConfig(**model_params)
        else:  # OLLAMA
            # Note: api_base is retrieved from provider_config by get_chat_model(),
            # not stored in OllamaModelConfig
            return OllamaModelConfig(**model_params)

    def get_api_key(self, provider: Provider) -> SecretStr | None:
        """Get API key for a provider with lazy loading from environment.

        Args:
            provider: The provider to get the API key for.

        Returns:
            SecretStr containing the API key, or None if not found.
        """
        from consoul.config.env import EnvSettings as RealEnvSettings
        from consoul.config.env import get_api_key

        return get_api_key(
            provider,
            self.env_settings
            if isinstance(self.env_settings, RealEnvSettings)
            else None,
        )
