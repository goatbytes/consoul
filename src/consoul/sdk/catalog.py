"""Model catalog - Available AI models and their capabilities.

This module provides the central catalog of supported AI models across all providers.
Used by ModelService to list available models and their capabilities.

Example:
    >>> from consoul.sdk.catalog import MODEL_CATALOG, get_model_info
    >>> model = get_model_info("gpt-4o")
    >>> if model and model.supports_vision:
    ...     print(f"{model.name} can process images")
"""

from __future__ import annotations

from consoul.sdk.models import ModelInfo

__all__ = [
    "MODEL_CATALOG",
    "get_all_providers",
    "get_model_info",
    "get_models_by_provider",
]

# Central model catalog - All supported AI models
MODEL_CATALOG: list[ModelInfo] = [
    # OpenAI GPT-5 Series (Latest Flagship)
    ModelInfo(
        "gpt-5",
        "GPT-5",
        "openai",
        "1M",
        "Flagship reasoning model",
        supports_vision=True,
    ),
    ModelInfo(
        "gpt-5-mini",
        "GPT-5 Mini",
        "openai",
        "1M",
        "Fast & affordable reasoning",
        supports_vision=True,
    ),
    ModelInfo(
        "gpt-5-nano",
        "GPT-5 Nano",
        "openai",
        "1M",
        "Fastest, most affordable",
        supports_vision=True,
    ),
    ModelInfo(
        "gpt-5-pro",
        "GPT-5 Pro",
        "openai",
        "1M",
        "Pro-tier flagship model",
        supports_vision=True,
    ),
    ModelInfo(
        "gpt-5.1",
        "GPT-5.1",
        "openai",
        "1M",
        "Latest GPT-5 series iteration",
        supports_vision=True,
    ),
    # OpenAI Codex Models (Specialized Coding)
    ModelInfo(
        "gpt-5-codex",
        "GPT-5 Codex",
        "openai",
        "1M",
        "Agentic coding optimized",
        supports_vision=True,
    ),
    ModelInfo(
        "gpt-5.1-codex",
        "GPT-5.1 Codex",
        "openai",
        "1M",
        "Latest codex iteration",
        supports_vision=True,
    ),
    ModelInfo(
        "gpt-5.1-codex-mini",
        "GPT-5.1 Codex Mini",
        "openai",
        "1M",
        "Efficient coding assistant",
        supports_vision=True,
    ),
    ModelInfo(
        "codex-mini-latest", "Codex Mini Latest", "openai", "128K", "Latest mini codex"
    ),
    # OpenAI Search API
    ModelInfo(
        "gpt-5-search-api",
        "GPT-5 Search API",
        "openai",
        "128K",
        "Web search integration",
        supports_vision=True,
    ),
    # OpenAI GPT-4.1 Series (1M context)
    ModelInfo(
        "gpt-4.1",
        "GPT-4.1",
        "openai",
        "1M",
        "Improved coding & long context",
        supports_vision=True,
    ),
    ModelInfo(
        "gpt-4.1-mini",
        "GPT-4.1 Mini",
        "openai",
        "1M",
        "Fast with 1M context",
        supports_vision=True,
    ),
    ModelInfo(
        "gpt-4.1-nano",
        "GPT-4.1 Nano",
        "openai",
        "1M",
        "Smallest GPT-4.1 variant",
        supports_vision=True,
    ),
    # OpenAI GPT-4o Series (Multimodal)
    ModelInfo(
        "gpt-4o",
        "GPT-4o",
        "openai",
        "128K",
        "Multimodal flagship",
        supports_vision=True,
    ),
    ModelInfo(
        "gpt-4o-mini",
        "GPT-4o Mini",
        "openai",
        "128K",
        "Cost-efficient multimodal",
        supports_vision=True,
    ),
    ModelInfo(
        "chatgpt-4o-latest",
        "ChatGPT 4o Latest",
        "openai",
        "128K",
        "ChatGPT 4o latest snapshot",
        supports_vision=True,
    ),
    ModelInfo(
        "gpt-4o-search-preview",
        "GPT-4o Search Preview",
        "openai",
        "128K",
        "Search preview (latest)",
        supports_vision=True,
    ),
    ModelInfo(
        "gpt-4o-search-preview-2025-03-11",
        "GPT-4o Search Preview (Dated)",
        "openai",
        "128K",
        "Search preview (dated)",
        supports_vision=True,
    ),
    # OpenAI GPT-4 Series (Legacy)
    ModelInfo("gpt-4", "GPT-4", "openai", "8K", "Original GPT-4", supports_vision=True),
    ModelInfo(
        "gpt-4-turbo",
        "GPT-4 Turbo",
        "openai",
        "128K",
        "GPT-4 with 128K context",
        supports_vision=True,
    ),
    # OpenAI GPT-3.5 Series (Legacy)
    ModelInfo("gpt-3.5-turbo", "GPT-3.5 Turbo", "openai", "16K", "Legacy fast model"),
    ModelInfo(
        "gpt-3.5-turbo-instruct",
        "GPT-3.5 Turbo Instruct",
        "openai",
        "4K",
        "Completion model (not chat)",
    ),
    # OpenAI o-Series (Deep Reasoning)
    ModelInfo("o1", "O1", "openai", "200K", "Reasoning model series 1"),
    ModelInfo("o1-pro", "O1 Pro", "openai", "128K", "Pro-tier reasoning"),
    ModelInfo("o3", "O3", "openai", "200K", "Advanced reasoning (preview)"),
    ModelInfo("o3-mini", "O3 Mini", "openai", "128K", "Efficient reasoning"),
    ModelInfo(
        "o4-mini",
        "O4 Mini",
        "openai",
        "128K",
        "Fast reasoning with vision",
        supports_vision=True,
    ),
    ModelInfo(
        "o4-mini-deep-research",
        "O4 Mini Deep Research",
        "openai",
        "128K",
        "Multi-step research",
        supports_vision=True,
    ),
    # OpenAI Realtime Models (Audio/Voice)
    ModelInfo(
        "gpt-realtime-mini",
        "GPT Realtime Mini",
        "openai",
        "128K",
        "Real-time voice (mini)",
    ),
    ModelInfo(
        "gpt-realtime", "GPT Realtime", "openai", "128K", "Real-time voice (full)"
    ),
    # Anthropic Claude 4.5 Models (Latest - Sep/Oct/Nov 2025)
    ModelInfo(
        "claude-opus-4-5-20251101",
        "Claude Opus 4.5",
        "anthropic",
        "200K",
        "Premium intelligence + performance",
        supports_vision=True,
    ),
    ModelInfo(
        "claude-sonnet-4-5-20250929",
        "Claude Sonnet 4.5",
        "anthropic",
        "200K",
        "Smartest for complex agents + coding",
        supports_vision=True,
    ),
    ModelInfo(
        "claude-haiku-4-5-20251001",
        "Claude Haiku 4.5",
        "anthropic",
        "200K",
        "Fastest near-frontier intelligence",
        supports_vision=True,
    ),
    # Anthropic Claude 4.x Models (Legacy)
    ModelInfo(
        "claude-opus-4-1-20250805",
        "Claude Opus 4.1",
        "anthropic",
        "200K",
        "Exceptional specialized reasoning",
        supports_vision=True,
    ),
    ModelInfo(
        "claude-opus-4-20250514",
        "Claude Opus 4",
        "anthropic",
        "200K",
        "Legacy model (use Opus 4.5)",
        supports_vision=True,
    ),
    ModelInfo(
        "claude-sonnet-4-20250514",
        "Claude Sonnet 4",
        "anthropic",
        "200K",
        "Legacy model (use Sonnet 4.5)",
        supports_vision=True,
    ),
    # Anthropic Claude 3.x Models (Legacy)
    ModelInfo(
        "claude-3-7-sonnet-20250219",
        "Claude 3.7 Sonnet",
        "anthropic",
        "200K",
        "Legacy model (use Sonnet 4.5)",
        supports_vision=True,
    ),
    ModelInfo(
        "claude-3-5-haiku-20241022",
        "Claude 3.5 Haiku",
        "anthropic",
        "200K",
        "Legacy model (use Haiku 4.5)",
        supports_vision=True,
    ),
    ModelInfo(
        "claude-3-haiku-20240307",
        "Claude 3 Haiku",
        "anthropic",
        "200K",
        "Legacy model (use Haiku 4.5)",
        supports_vision=True,
    ),
    ModelInfo(
        "claude-3-opus-20240229",
        "Claude 3 Opus",
        "anthropic",
        "200K",
        "Legacy model (use Opus 4.5)",
        supports_vision=True,
    ),
    # Google Gemini 2.5 Models (Latest - Stable)
    ModelInfo(
        "gemini-2.5-pro",
        "Gemini 2.5 Pro",
        "google",
        "1M",
        "Most powerful with thinking",
        supports_vision=True,
    ),
    ModelInfo(
        "gemini-2.5-flash",
        "Gemini 2.5 Flash",
        "google",
        "1M",
        "Fast multimodal",
        supports_vision=True,
    ),
    ModelInfo(
        "gemini-2.5-flash-lite",
        "Gemini 2.5 Flash Lite",
        "google",
        "1M",
        "Speed & cost optimized",
        supports_vision=True,
    ),
    ModelInfo(
        "gemini-2.5-flash-image",
        "Gemini 2.5 Flash Image",
        "google",
        "64K",
        "Native image generation",
        supports_vision=True,
    ),
    # Google Gemini 2.0 Models
    ModelInfo(
        "gemini-2.0-flash",
        "Gemini 2.0 Flash",
        "google",
        "1M",
        "Latest stable flash",
        supports_vision=True,
    ),
    # Google Gemini 3 Models (Preview)
    ModelInfo(
        "gemini-3-pro-preview",
        "Gemini 3 Pro Preview",
        "google",
        "1M",
        "Advanced reasoning with thinking",
        supports_vision=True,
    ),
    ModelInfo(
        "gemini-3-pro-image-preview",
        "Gemini 3 Pro Image Preview",
        "google",
        "1M",
        "Vision + reasoning with thinking",
        supports_vision=True,
    ),
    # Google Gemini 1.5 Models (Legacy)
    ModelInfo(
        "gemini-1.5-pro",
        "Gemini 1.5 Pro",
        "google",
        "2M",
        "Legacy 2M context",
        supports_vision=True,
    ),
    ModelInfo(
        "gemini-1.5-flash",
        "Gemini 1.5 Flash",
        "google",
        "1M",
        "Legacy flash model",
        supports_vision=True,
    ),
    # HuggingFace Models (Serverless Inference via Inference Providers)
    ModelInfo(
        "meta-llama/Llama-3.1-8B-Instruct",
        "Llama 3.1 8B Instruct",
        "huggingface",
        "128K",
        "Llama 3.1 8B (via Novita provider)",
    ),
    ModelInfo(
        "meta-llama/Llama-3.2-3B-Instruct",
        "Llama 3.2 3B Instruct",
        "huggingface",
        "128K",
        "Llama 3.2 3B (check provider availability)",
    ),
    ModelInfo(
        "mistralai/Mistral-7B-Instruct-v0.3",
        "Mistral 7B Instruct",
        "huggingface",
        "32K",
        "Mistral 7B (check provider availability)",
    ),
]


def get_models_by_provider(provider: str) -> list[ModelInfo]:
    """Get all models for a specific provider.

    Args:
        provider: Provider name ("openai", "anthropic", "google", "huggingface", "ollama")

    Returns:
        List of ModelInfo objects for the specified provider

    Example:
        >>> openai_models = get_models_by_provider("openai")
        >>> print(f"Found {len(openai_models)} OpenAI models")
    """
    return [m for m in MODEL_CATALOG if m.provider.lower() == provider.lower()]


def get_model_info(model_id: str) -> ModelInfo | None:
    """Get model info by ID.

    Args:
        model_id: Model identifier (e.g., "gpt-4o", "claude-3-5-sonnet-20241022")

    Returns:
        ModelInfo if found, None otherwise

    Example:
        >>> model = get_model_info("gpt-4o")
        >>> if model:
        ...     print(f"{model.name}: {model.description}")
    """
    return next((m for m in MODEL_CATALOG if m.id == model_id), None)


def get_all_providers() -> list[str]:
    """Get unique list of providers.

    Returns:
        Sorted list of provider names

    Example:
        >>> providers = get_all_providers()
        >>> print(", ".join(providers))
        anthropic, google, huggingface, openai
    """
    return sorted({m.provider for m in MODEL_CATALOG})
