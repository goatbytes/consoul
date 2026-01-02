"""Context management and token counting utilities for conversation history.

This module provides utilities for managing conversation context windows and counting
tokens across different AI providers. It handles provider-specific token counting
with appropriate fallbacks.

Provider-Specific Token Counting:
    - OpenAI (gpt-*, o1-*, o2-*, etc.): Uses tiktoken for accurate counting
    - Ollama (llama*, granite*, qwen*, etc.): Uses HuggingFace tokenizers (100% accurate)
      Falls back to character approximation if transformers not installed
    - Anthropic (claude-*): Uses LangChain's get_num_tokens_from_messages
    - Google (gemini-*): Uses LangChain's get_num_tokens_from_messages
    - Others: Uses character-based approximation (4 chars ≈ 1 token)

Token Limit Resolution (Multi-Tier Fallback Chain):
    1. Model registry (curated models with full pricing/metadata)
    2. Hardcoded MODEL_TOKEN_LIMITS dictionary (fast offline lookup)
    3. Ollama API query (for local Ollama models)
    4. LiteLLM registry (community-maintained, auto-updates from GitHub)
    5. Pattern-based intelligent defaults (version-based heuristics)
    6. Conservative 4K default

Token Limits (as of 2025-11-12):
    - OpenAI GPT-5/4.1: 400K/1M tokens
    - OpenAI GPT-4o: 128K tokens
    - Anthropic Claude Sonnet 4: 1M tokens (beta/enterprise)
    - Anthropic Claude 3.5/3: 200K tokens
    - Google Gemini 1.5 Pro: 2M tokens
    - Google Gemini 2.5: 1M tokens
    - Qwen 3: 262K tokens
    - Qwen 2.5: 128K tokens

Example:
    >>> counter = create_token_counter("gpt-4o")
    >>> tokens = counter([{"role": "user", "content": "Hello!"}])
    >>> print(f"Tokens: {tokens}")
    Tokens: 8

    >>> limit = get_model_token_limit("claude-3-5-sonnet")
    >>> print(f"Max tokens: {limit}")
    Max tokens: 200000
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from langchain_core.language_models import BaseChatModel
    from langchain_core.messages import BaseMessage

# Model token limits (context window sizes)
# Updated: 2025-11-12
# Notes:
# - OpenAI GPT-5/4.1 support 400K/1M token context; GPT-4o remains 128K.
# - Anthropic Claude defaults to 200K; Sonnet 4 supports 1M (beta/enterprise).
# - Gemini 1.5 Pro allows 2M; 2.5 Pro is 1M (2M announced); 2.5 Flash is ~1M.
# - Qwen 3 supports 262K tokens; Qwen 2.5 supports 128K tokens.
# - Open-source models (Llama, Mistral, etc.) may have configurable limits.
MODEL_TOKEN_LIMITS: dict[str, int] = {
    # OpenAI models - GPT-5 series
    "gpt-5": 400_000,  # API spec: 400K context window
    "gpt-5-mini": 400_000,
    "gpt-5-nano": 400_000,
    # OpenAI models - GPT-4.1 series
    "gpt-4.1": 1_000_000,  # Full API version: ~1M tokens
    "gpt-4.1-mini": 1_000_000,
    "gpt-4.1-nano": 1_000_000,
    # OpenAI models - GPT-4 series
    "gpt-4o": 128_000,
    "gpt-4o-mini": 128_000,
    "gpt-4-turbo": 128_000,
    "gpt-4": 8_192,
    "gpt-3.5-turbo": 16_385,
    # OpenAI reasoning models
    "o1-preview": 128_000,
    "o1-mini": 128_000,
    # Anthropic models - Claude 4.5 (November 2025 release)
    "claude-opus-4-5": 200_000,  # Opus 4.5: 200K context
    "claude-sonnet-4-5": 200_000,  # Sonnet 4.5: 200K context
    "claude-haiku-4-5": 200_000,  # Haiku 4.5: 200K context
    # Anthropic models - Claude 4.x
    "claude-opus-4-1": 200_000,  # Opus 4.1: 200K context
    "claude-opus-4": 200_000,  # Opus 4: 200K context
    "claude-sonnet-4": 1_000_000,  # Beta/enterprise: 1M context
    # Anthropic models - Claude 3.7 (February 2025)
    "claude-3-7-sonnet": 200_000,  # Sonnet 3.7: 200K context
    "claude-3-7-opus": 200_000,  # Opus 3.7: 200K context (if released)
    "claude-3-7-haiku": 200_000,  # Haiku 3.7: 200K context (if released)
    # Anthropic models - Claude 3.5
    "claude-3-5-sonnet": 200_000,
    # Anthropic models - Claude 3
    "claude-3-opus": 200_000,
    "claude-3-sonnet": 200_000,
    "claude-3-haiku": 200_000,
    # Google models - Gemini 2.5
    "gemini-2.5-pro": 1_048_576,  # API spec: 2^20 (~1M)
    "gemini-2.5-flash": 1_048_576,  # API spec: 2^20 (~1M)
    # Google models - Gemini 1.5
    "gemini-1.5-pro": 2_097_152,  # API spec: 2^21 (~2M)
    "gemini-1.5-flash": 1_048_576,  # API spec: 2^20 (~1M)
    "gemini-pro": 32_000,  # Legacy
    # Ollama / Open-source models
    "llama3": 8_192,
    "llama3.1": 128_000,  # Llama 3.1 family supports 128K
    "mistral": 32_000,
    "phi": 4_096,
    # IBM Granite models
    "granite4": 128_000,  # Granite 4.x series: 128K context
    "granite3": 128_000,  # Granite 3.x series: 128K context
    "granite3-moe": 128_000,  # Granite 3 MoE: 128K context
    "granite3-dense": 128_000,  # Granite 3 Dense: 128K context
    # Qwen models
    "qwen3": 262_000,  # Qwen 3 series: 262K context
    "qwen2.5": 128_000,  # Qwen 2.5 series: 128K context
    "qwen2": 32_000,  # Qwen 2 series: 32K context
    "qwen": 32_000,  # Legacy/Qwen 1: 32K context
    "codellama": 16_000,
}

# Default fallback for unknown models
DEFAULT_TOKEN_LIMIT = 4_096

# Cache for Ollama context lengths (in-memory, persists for session)
_OLLAMA_CONTEXT_CACHE: dict[str, int] = {}


def _load_ollama_cache() -> dict[str, int]:
    """Load cached Ollama context lengths from disk.

    Returns:
        Dictionary mapping model names to context lengths
    """
    try:
        import json
        from pathlib import Path

        cache_file = Path.home() / ".consoul" / "ollama_context_cache.json"
        if cache_file.exists():
            result: dict[str, int] = json.loads(cache_file.read_text())
            return result
    except Exception:
        pass
    return {}


def _save_ollama_cache(cache: dict[str, int]) -> None:
    """Save Ollama context length cache to disk.

    Args:
        cache: Dictionary mapping model names to context lengths
    """
    try:
        import json
        from pathlib import Path

        cache_file = Path.home() / ".consoul" / "ollama_context_cache.json"
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(cache, indent=2))
    except Exception:
        pass


def _get_ollama_context_length(model_name: str) -> int | None:
    """Query Ollama API for actual context length of a model.

    Results are cached both in-memory and on disk to avoid repeated API calls.
    Cache is stored at ~/.consoul/ollama_context_cache.json

    Args:
        model_name: Ollama model name (e.g., "qwen3:30b", "llama3.1:8b")

    Returns:
        Context length in tokens, or None if query fails

    Example:
        >>> _get_ollama_context_length("qwen3:30b")
        262144
    """
    global _OLLAMA_CONTEXT_CACHE

    # Check in-memory cache first (fastest)
    if model_name in _OLLAMA_CONTEXT_CACHE:
        return _OLLAMA_CONTEXT_CACHE[model_name]

    # Load disk cache if not already loaded
    if not _OLLAMA_CONTEXT_CACHE:
        _OLLAMA_CONTEXT_CACHE = _load_ollama_cache()
        # Check again after loading
        if model_name in _OLLAMA_CONTEXT_CACHE:
            return _OLLAMA_CONTEXT_CACHE[model_name]

    # Cache miss - query Ollama API
    try:
        from consoul.ai.providers import get_ollama_models

        # Get all models with context info and find matching model
        models = get_ollama_models(include_context=True)
        for model in models:
            if model.get("name") == model_name:
                context_length: int | None = model.get("context_length")
                if context_length:
                    # Cache the result (both in-memory and on disk)
                    _OLLAMA_CONTEXT_CACHE[model_name] = context_length
                    _save_ollama_cache(_OLLAMA_CONTEXT_CACHE)
                    return context_length
    except Exception:
        # Silently fail - we'll fall back to hardcoded limits
        pass

    return None


def save_llamacpp_context_length(model_path: str, n_ctx: int) -> None:
    """Cache the context length for a LlamaCpp GGUF model.

    Stores the context size in the same cache file as Ollama models for simplicity.
    Uses absolute path as key to avoid issues with relative paths.

    Args:
        model_path: Path to the GGUF model file
        n_ctx: Context length in tokens
    """
    global _OLLAMA_CONTEXT_CACHE

    try:
        from pathlib import Path

        # Normalize to absolute path for consistent cache keys
        abs_path = str(Path(model_path).resolve())

        # Load existing cache
        if not _OLLAMA_CONTEXT_CACHE:
            _OLLAMA_CONTEXT_CACHE = _load_ollama_cache()

        # Update cache
        _OLLAMA_CONTEXT_CACHE[abs_path] = n_ctx

        # Save to disk
        _save_ollama_cache(_OLLAMA_CONTEXT_CACHE)
    except Exception:
        # Silently fail - caching is optional
        pass


def _get_llamacpp_context_length(model_path: str) -> int | None:
    """Retrieve cached context length for a LlamaCpp GGUF model.

    Args:
        model_path: Path to the GGUF model file

    Returns:
        Cached context length in tokens, or None if not found
    """
    global _OLLAMA_CONTEXT_CACHE

    try:
        from pathlib import Path

        # Normalize to absolute path for consistent cache keys
        abs_path = str(Path(model_path).resolve())

        # Check in-memory cache first
        if abs_path in _OLLAMA_CONTEXT_CACHE:
            return _OLLAMA_CONTEXT_CACHE[abs_path]

        # Load disk cache if not already loaded
        if not _OLLAMA_CONTEXT_CACHE:
            _OLLAMA_CONTEXT_CACHE = _load_ollama_cache()
            if abs_path in _OLLAMA_CONTEXT_CACHE:
                return _OLLAMA_CONTEXT_CACHE[abs_path]
    except Exception:
        pass

    return None


def get_model_token_limit(model_name: str) -> int:
    """Get the maximum context window size (in tokens) for a model.

    Returns the known token limit for the model using a multi-tier fallback chain:
    1. Model registry (curated models with pricing/metadata)
    2. Hardcoded MODEL_TOKEN_LIMITS dictionary
    3. Ollama API query (for Ollama models)
    4. LiteLLM registry (community-maintained, auto-updating)
    5. Pattern-based intelligent defaults (for new model versions)
    6. Conservative 4K default

    For Ollama models, attempts to query the Ollama API for the actual
    context length. For LlamaCpp models (GGUF files), checks the cache for
    previously saved context sizes from model initialization.

    Args:
        model_name: Model identifier (e.g., "gpt-4o", "claude-3-5-sonnet", "qwen3:30b")
                   or path to GGUF file (e.g., "/path/to/model.gguf")

    Returns:
        Maximum number of tokens the model can handle in its context window.

    Example:
        >>> get_model_token_limit("gpt-4o")
        128000
        >>> get_model_token_limit("GPT-4O-2024-08-06")
        128000
        >>> get_model_token_limit("qwen3:30b")  # Queries Ollama API
        262144
        >>> get_model_token_limit("/path/to/model.gguf")  # Checks cache
        8192
        >>> get_model_token_limit("unknown-model")
        4096
    """
    # Normalize: lowercase, strip whitespace, normalize separators
    key = (model_name or "").strip().lower()
    key_normalized = key.replace(":", "-").replace("/", "-").replace("_", "-")

    # 1. Try model registry first (curated models with full metadata)
    try:
        from consoul.registry.registry import get_context_window

        registry_context = get_context_window(model_name)
        if registry_context:
            return registry_context
    except Exception:
        # Registry import failure - continue to other methods
        pass

    # 2. Try exact match (with normalized key) - FAST, no API call
    if key_normalized in MODEL_TOKEN_LIMITS:
        return MODEL_TOKEN_LIMITS[key_normalized]

    # 3. Try prefix match (e.g., "gpt-4o-2024-08-06" → "gpt-4o", "granite4:3b" → "granite4") - FAST
    for known_model, limit in MODEL_TOKEN_LIMITS.items():
        if key_normalized.startswith(known_model):
            return limit

    # 4. Fallback: For Ollama models with tags (contain ":"), try API query
    # This gives us the actual configured context for unmapped models
    if ":" in key:
        ollama_context = _get_ollama_context_length(model_name)
        if ollama_context:
            return ollama_context

    # For local models without tags, try API query as fallback
    if key in {"llama3", "llama3.1", "mistral", "phi", "qwen", "codellama"}:
        ollama_context = _get_ollama_context_length(model_name)
        if ollama_context:
            return ollama_context

    # Check if this looks like a GGUF file path (LlamaCpp model)
    # File paths typically contain "/" or "\" and end with .gguf
    if ("/" in model_name or "\\" in model_name) and model_name.lower().endswith(
        ".gguf"
    ):
        llamacpp_context = _get_llamacpp_context_length(model_name)
        if llamacpp_context:
            return llamacpp_context

    # 5. Try LiteLLM registry (community-maintained, auto-updates)
    try:
        from consoul.ai.litellm_registry import get_litellm_context_window

        litellm_context = get_litellm_context_window(model_name)
        if litellm_context:
            return litellm_context
    except Exception:
        # LiteLLM registry unavailable - continue to pattern matching
        pass

    # 6. Use pattern-based intelligent defaults before falling back to conservative limit
    # This handles new model releases without requiring code updates
    import logging
    import re

    logger = logging.getLogger(__name__)

    # Extract version numbers from Claude models (e.g., "claude-3-7-sonnet" -> 3.7)
    claude_match = re.match(r"claude[- ](\d+)[- ](\d+)", key_normalized)
    if claude_match:
        major = int(claude_match.group(1))
        minor = int(claude_match.group(2))
        # Claude 3.x and newer: 200K tokens (conservative default for all Claude 3+ models)
        if major >= 3:
            default_limit = 200_000
            logger.info(
                f"Unknown Claude model '{model_name}' detected as Claude {major}.{minor} - "
                f"using {default_limit:,} token default (standard for Claude 3+)"
            )
            return default_limit

    # GPT-4.x and GPT-5+ models: Use version-based defaults
    gpt_match = re.match(r"gpt[- ]([45])", key_normalized)
    if gpt_match:
        version = int(gpt_match.group(1))
        default_limit = 400_000 if version == 5 else 128_000  # GPT-5: 400K, GPT-4: 128K
        logger.info(
            f"Unknown GPT model '{model_name}' detected as GPT-{version} - "
            f"using {default_limit:,} token default"
        )
        return default_limit

    # Gemini 2.x models: Default to 1M
    if "gemini-2" in key_normalized or "gemini2" in key_normalized:
        default_limit = 1_000_000
        logger.info(
            f"Unknown Gemini model '{model_name}' detected as Gemini 2.x - "
            f"using {default_limit:,} token default"
        )
        return default_limit

    # Warn about truly unknown model using conservative default
    logger.warning(
        f"Unknown model '{model_name}' - using conservative {DEFAULT_TOKEN_LIMIT:,} token limit. "
        f"This may cause message trimming issues. Consider adding this model to MODEL_TOKEN_LIMITS "
        f"in consoul/ai/context.py for proper support."
    )

    # Return conservative default
    return DEFAULT_TOKEN_LIMIT


def _is_openai_model(model_name: str) -> bool:
    """Check if model is an OpenAI model (supports tiktoken).

    Heuristic detection for OpenAI chat/reasoning families that use tiktoken.
    Uses case-insensitive matching for robustness.

    Args:
        model_name: Model identifier

    Returns:
        True if model is from OpenAI (gpt-*, o1-*, o2-*, o3-*, o4-*, text-davinci-*)
    """
    key = (model_name or "").lower()
    openai_prefixes = ("gpt-", "o1-", "o2-", "o3-", "o4-", "text-davinci")
    return any(key.startswith(prefix) for prefix in openai_prefixes)


def _is_ollama_model(model_name: str) -> bool:
    """Check if model name matches Ollama model patterns.

    Detects common Ollama model naming patterns to determine if we should
    try using HuggingFace tokenizers for accurate token counting.

    Args:
        model_name: Model identifier

    Returns:
        True if model appears to be an Ollama model
    """
    key = (model_name or "").lower()

    # Common Ollama model prefixes and patterns
    ollama_patterns = (
        "llama",
        "granite",
        "qwen",
        "mistral",
        "mixtral",
        "phi",
        "codellama",
        "deepseek",
        "gemma",
        "vicuna",
        "orca",
        "starling",
        "solar",
        "yi",
    )

    return any(key.startswith(pattern) for pattern in ollama_patterns)


def _create_tiktoken_counter(model_name: str) -> Callable[[list[BaseMessage]], int]:
    """Create token counter using tiktoken for OpenAI models.

    Args:
        model_name: OpenAI model identifier

    Returns:
        Function that counts tokens in a list of messages

    Raises:
        ImportError: If tiktoken is not installed
    """
    try:
        import tiktoken
    except ImportError as e:
        raise ImportError(
            "tiktoken is required for OpenAI token counting. "
            "Install it with: pip install tiktoken"
        ) from e

    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        # Fallback to cl100k_base (used by most modern OpenAI models)
        encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(messages: list[BaseMessage]) -> int:
        """Count tokens using tiktoken encoding.

        Approximation based on OpenAI's token counting:
        - Each message has overhead: <im_start>, role, content, <im_end>
        - Roughly 4 tokens per message + content tokens
        """
        num_tokens = 0
        for message in messages:
            # Message overhead (role markers, etc.)
            num_tokens += 4
            # Content tokens - handle both string and complex content
            content = (
                message.content
                if isinstance(message.content, str)
                else str(message.content)
            )
            num_tokens += len(encoding.encode(content))
        # Add 2 for priming (assistant response start)
        num_tokens += 2
        return num_tokens

    return count_tokens


def _create_langchain_counter(
    model: BaseChatModel,
) -> Callable[[list[BaseMessage]], int]:
    """Create token counter using LangChain's model method.

    Uses the model's get_num_tokens_from_messages() method if available,
    otherwise falls back to character-based approximation.

    Args:
        model: LangChain chat model instance

    Returns:
        Function that counts tokens in a list of messages
    """

    def count_tokens(messages: list[BaseMessage]) -> int:
        """Count tokens using model's built-in counter or approximation."""
        try:
            # Try using model's token counter
            if hasattr(model, "get_num_tokens_from_messages"):
                result: int = model.get_num_tokens_from_messages(messages)
                return result
        except Exception:
            # Fallback to approximation if method fails
            pass

        # Character-based approximation: ~4 characters per token
        total_chars = sum(len(msg.content) for msg in messages)
        return total_chars // 4

    return count_tokens


def _create_approximate_counter() -> Callable[[list[BaseMessage]], int]:
    """Create character-based token counter (approximation).

    Uses the heuristic that 1 token ≈ 4 characters, which is reasonable
    for English text across most tokenizers.

    Returns:
        Function that approximates token count from character count
    """

    def count_tokens(messages: list[BaseMessage]) -> int:
        """Approximate tokens using character count."""
        total_chars = sum(len(msg.content) for msg in messages)
        # Rough approximation: 1 token ≈ 4 characters
        return total_chars // 4

    return count_tokens


def _create_huggingface_counter(
    model_name: str,
) -> Callable[[list[BaseMessage]], int]:
    """Create token counter using HuggingFace tokenizer for Ollama models.

    Uses the actual model tokenizer from HuggingFace for 100% accurate token
    counting without making slow HTTP requests to Ollama server.

    Args:
        model_name: Ollama model name (e.g., "granite4:3b", "llama3:8b")

    Returns:
        Function that counts tokens using HuggingFace tokenizer

    Raises:
        ImportError: If transformers package not installed
        ValueError: If model not found in mapping
        Exception: If tokenizer fails to load
    """
    try:
        from consoul.ai.tokenizers import create_huggingface_token_counter

        # Use lazy=True - tokenizer loads in background after UI appears
        # This makes startup instant while ensuring tokenizer is ready before first message
        return create_huggingface_token_counter(model_name, lazy=True)
    except ImportError:
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(
            f"transformers package not installed for {model_name}. "
            "Falling back to character approximation. "
            "Install with: pip install transformers or pip install consoul[huggingface-local]"
        )
        raise
    except ValueError as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(
            f"Model {model_name} not found in HuggingFace mapping: {e}. "
            "Falling back to character approximation."
        )
        raise
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(
            f"Failed to load HuggingFace tokenizer for {model_name}: {e}. "
            "Falling back to character approximation."
        )
        raise


def create_token_counter(
    model_name: str, model: BaseChatModel | None = None
) -> Callable[[list[BaseMessage]], int]:
    """Create appropriate token counter for the given model.

    Selects the best token counting method based on the model:
    - OpenAI models: Uses tiktoken for accurate counting
    - Ollama models: Tries HuggingFace tokenizer, falls back to approximation
    - Other models with LangChain support: Uses model's built-in counter
    - Unknown models: Uses character-based approximation

    Args:
        model_name: Model identifier (e.g., "gpt-4o", "claude-3-5-sonnet", "granite4:3b")
        model: Optional LangChain model instance (for provider-specific counting)

    Returns:
        Function that takes list[BaseMessage] and returns token count

    Example:
        >>> from langchain_core.messages import HumanMessage
        >>> counter = create_token_counter("gpt-4o")
        >>> tokens = counter([HumanMessage(content="Hello world")])
        >>> print(f"Tokens: {tokens}")
        Tokens: 8
    """
    import logging

    logger = logging.getLogger(__name__)

    # Use tiktoken for OpenAI models (most accurate)
    if _is_openai_model(model_name):
        return _create_tiktoken_counter(model_name)

    # For Ollama models, try HuggingFace tokenizer for accurate counting
    # Falls back to approximation if transformers not installed or model not mapped
    if _is_ollama_model(model_name):
        try:
            return _create_huggingface_counter(model_name)
        except (ImportError, ValueError, Exception):
            # Fallback to approximation on any error
            logger.debug(
                f"Using character approximation for {model_name} "
                "(HuggingFace tokenizer unavailable)"
            )
            return _create_approximate_counter()

    # For other local models (LlamaCpp, MLX), avoid using model's token counter as it can
    # cause blocking/hanging when loading models. Use approximation instead.
    if model is not None:
        model_class_name = model.__class__.__name__
        if model_class_name in (
            "ChatLlamaCpp",
            "LlamaCpp",
            "ChatOllama",
            "MLXChatWrapper",
        ):
            return _create_approximate_counter()
        return _create_langchain_counter(model)

    # Fallback to character approximation
    return _create_approximate_counter()


def count_message_tokens(
    messages: list[BaseMessage], model_name: str, model: BaseChatModel | None = None
) -> int:
    """Count total tokens in a list of messages.

    Convenience function that creates a token counter and counts tokens
    in a single call.

    Args:
        messages: List of LangChain BaseMessage objects
        model_name: Model identifier for token counting
        model: Optional LangChain model instance

    Returns:
        Total number of tokens in the messages

    Example:
        >>> from langchain_core.messages import HumanMessage, AIMessage
        >>> messages = [
        ...     HumanMessage(content="Hello!"),
        ...     AIMessage(content="Hi there!")
        ... ]
        >>> tokens = count_message_tokens(messages, "gpt-4o")
        >>> print(f"Total tokens: {tokens}")
        Total tokens: 14
    """
    counter = create_token_counter(model_name, model)
    return counter(messages)
