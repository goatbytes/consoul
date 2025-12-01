"""Model pricing data for accurate cost calculations.

This module provides pricing information for AI models from various providers.
Pricing data is updated as of November 2024.

IMPORTANT: LangChain's pricing data for OpenAI models may be outdated. Our
OPENAI_PRICING dict takes priority and contains verified pricing from
https://openai.com/api/pricing/ (as of November 2024).

For other providers (Anthropic, Google), we maintain static pricing from
official sources.

Prices are in USD per million tokens (MTok).
"""

from __future__ import annotations

from typing import Any

# Anthropic Claude pricing (as of November 2024)
# Source: https://docs.anthropic.com/en/docs/about-claude/pricing
# Note: Anthropic now uses naming like "Claude Sonnet 4.5" but API still uses "claude-3-5-sonnet-*"
ANTHROPIC_PRICING = {
    # Claude Opus 4.5 (November 2025 release - 66% price drop!)
    "claude-opus-4-5-20251101": {
        "input": 5.00,  # $5 per MTok (down from $15)
        "output": 25.00,  # $25 per MTok (down from $75)
        "cache_write_5m": 6.25,  # $6.25 per MTok (5min TTL)
        "cache_write_1h": 10.00,  # $10.00 per MTok (1hr TTL)
        "cache_read": 0.50,  # $0.50 per MTok
    },
    # Claude Sonnet 4.5 (marketed as Claude 3.5 Sonnet in API)
    "claude-3-5-sonnet-20241022": {
        "input": 3.00,  # $3 per MTok
        "output": 15.00,  # $15 per MTok
        "cache_write_5m": 3.75,  # $3.75 per MTok (5min TTL)
        "cache_write_1h": 6.00,  # $6.00 per MTok (1hr TTL)
        "cache_read": 0.30,  # $0.30 per MTok (cache hits)
    },
    "claude-3-5-sonnet-20240620": {
        "input": 3.00,
        "output": 15.00,
        "cache_write_5m": 3.75,
        "cache_write_1h": 6.00,
        "cache_read": 0.30,
    },
    # Claude Haiku 4.5 (marketed as Claude 3.5 Haiku in API)
    "claude-3-5-haiku-20241022": {
        "input": 1.00,  # $1 per MTok
        "output": 5.00,  # $5 per MTok
        "cache_write_5m": 1.25,  # $1.25 per MTok (5min TTL)
        "cache_write_1h": 2.00,  # $2.00 per MTok (1hr TTL)
        "cache_read": 0.10,  # $0.10 per MTok
    },
    # Claude Opus 4.5 (legacy API name - same pricing as new version)
    "claude-3-opus-20240229": {
        "input": 5.00,  # $5 per MTok (67% price reduction from original $15!)
        "output": 25.00,  # $25 per MTok (67% price reduction from original $75!)
        "cache_write_5m": 6.25,  # $6.25 per MTok (5min TTL)
        "cache_write_1h": 10.00,  # $10.00 per MTok (1hr TTL)
        "cache_read": 0.50,  # $0.50 per MTok
    },
    # Claude Sonnet 4 (API: claude-3-sonnet)
    "claude-3-sonnet-20240229": {
        "input": 3.00,
        "output": 15.00,
        "cache_write_5m": 3.75,
        "cache_write_1h": 6.00,
        "cache_read": 0.30,
    },
    # Claude Haiku 3.5/3
    "claude-3-haiku-20240307": {
        "input": 0.80,  # $0.80 per MTok
        "output": 4.00,  # $4.00 per MTok
        "cache_write_5m": 1.00,  # $1.00 per MTok (5min TTL)
        "cache_write_1h": 1.60,  # $1.60 per MTok (1hr TTL)
        "cache_read": 0.08,  # $0.08 per MTok
    },
}

# Google Gemini pricing (as of November 2024)
# Source: https://ai.google.dev/gemini-api/docs/pricing
# Note: Prices vary by context size (<=200k vs >200k tokens)
# We use base pricing (<=200k tokens) here
GOOGLE_PRICING = {
    # Gemini 2.5 Pro
    "gemini-2.5-pro": {
        "input": 1.25,  # $1.25 per MTok (prompts ≤200k)
        "output": 10.00,  # $10.00 per MTok
        "cache_read": 0.12,  # $0.12 per MTok - Updated from scrape
    },
    # Gemini 2.5 Flash
    "gemini-2.5-flash": {
        "input": 0.62,  # $0.62 per MTok (prompts ≤200k) - Updated from scrape
        "output": 5.00,  # $5.00 per MTok
        "cache_read": 0.12,  # $0.12 per MTok
    },
    # Gemini 2.5 Flash-Lite
    "gemini-2.5-flash-lite": {
        "input": 0.15,  # $0.15 per MTok (text/image/video)
        "output": 1.25,  # $1.25 per MTok
        "cache_read": 0.03,  # $0.03 per MTok
    },
    # Gemini 2.0 Flash (Free tier for up to 10 RPM)
    "gemini-2.0-flash": {
        "input": 0.30,  # $0.30 per MTok (text/image/video)
        "output": 2.50,  # $2.50 per MTok
        "cache_read": 0.03,  # $0.03 per MTok
    },
    # Gemini 2.0 Flash-Lite
    "gemini-2.0-flash-lite": {
        "input": 0.15,  # $0.15 per MTok (text/image/video)
        "output": 1.25,  # $1.25 per MTok
        "cache_read": 0.03,  # $0.03 per MTok
    },
    # Gemini 3 Pro Preview (Thinking model)
    "gemini-3-pro-preview": {
        "input": 2.00,  # $2.00 per MTok (prompts ≤200k), $4.00 for >200k
        "output": 12.00,  # $12.00 per MTok (prompts ≤200k), $18.00 for >200k (includes thinking tokens)
        "cache_read": 0.20,  # $0.20 per MTok (prompts ≤200k), $0.40 for >200k
        # Note: Storage pricing: $4.50 per 1M tokens per hour (not implemented)
    },
    # Gemini 3 Pro Image Preview
    "gemini-3-pro-image-preview": {
        "input": 1.00,  # $1.00 per MTok (prompts ≤200k)
        "output": 6.00,  # $6.00 per MTok (includes thinking tokens)
        "cache_read": 0.20,  # $0.20 per MTok
    },
}

# OpenAI pricing with tier-specific data
# Source: https://platform.openai.com/docs/pricing (as of January 2025)
# Structure: model_name -> { tier -> { input, output, cache_read } }
# Available tiers: "standard" (default), "flex", "batch", "priority"
OPENAI_PRICING = {
    # GPT-5 series
    "gpt-5.1": {
        "standard": {"input": 1.25, "output": 10.00, "cache_read": 0.125},
        "flex": {"input": 0.625, "output": 5.00, "cache_read": 0.0625},
        "batch": {"input": 0.625, "output": 5.00, "cache_read": 0.0625},
        "priority": {"input": 2.50, "output": 20.00, "cache_read": 0.25},
    },
    "gpt-5": {
        "standard": {"input": 1.25, "output": 10.00, "cache_read": 0.125},
        "flex": {"input": 0.625, "output": 5.00, "cache_read": 0.0625},
        "batch": {"input": 0.625, "output": 5.00, "cache_read": 0.0625},
        "priority": {"input": 2.50, "output": 20.00, "cache_read": 0.25},
    },
    "gpt-5-mini": {
        "standard": {"input": 0.25, "output": 2.00, "cache_read": 0.025},
        "flex": {"input": 0.125, "output": 1.00, "cache_read": 0.0125},
        "batch": {"input": 0.125, "output": 1.00, "cache_read": 0.0125},
        "priority": {"input": 0.45, "output": 3.60, "cache_read": 0.045},
    },
    "gpt-5-nano": {
        "standard": {"input": 0.05, "output": 0.40, "cache_read": 0.005},
        "flex": {"input": 0.025, "output": 0.20, "cache_read": 0.0025},
        "batch": {"input": 0.025, "output": 0.20, "cache_read": 0.0025},
    },
    "gpt-5-pro": {
        "standard": {"input": 15.00, "output": 120.00},
        "batch": {"input": 7.50, "output": 60.00},
    },
    # GPT-4.1 series
    "gpt-4.1": {
        "standard": {"input": 2.00, "output": 8.00, "cache_read": 0.50},
        "batch": {"input": 1.00, "output": 4.00},
        "priority": {"input": 3.50, "output": 14.00, "cache_read": 0.875},
    },
    "gpt-4.1-mini": {
        "standard": {"input": 0.40, "output": 1.60, "cache_read": 0.10},
        "batch": {"input": 0.20, "output": 0.80},
        "priority": {"input": 0.70, "output": 2.80, "cache_read": 0.175},
    },
    "gpt-4.1-nano": {
        "standard": {"input": 0.10, "output": 0.40, "cache_read": 0.025},
        "batch": {"input": 0.05, "output": 0.20},
        "priority": {"input": 0.20, "output": 0.80, "cache_read": 0.05},
    },
    # GPT-4o series
    "gpt-4o": {
        "standard": {"input": 2.50, "output": 10.00, "cache_read": 1.25},
        "batch": {"input": 1.25, "output": 5.00},
        "priority": {"input": 4.25, "output": 17.00, "cache_read": 2.125},
    },
    "gpt-4o-2024-05-13": {
        "standard": {"input": 5.00, "output": 15.00},
        "batch": {"input": 2.50, "output": 7.50},
        "priority": {"input": 8.75, "output": 26.25},
    },
    "gpt-4o-mini": {
        "standard": {"input": 0.15, "output": 0.60, "cache_read": 0.075},
        "batch": {"input": 0.075, "output": 0.30},
        "priority": {"input": 0.25, "output": 1.00, "cache_read": 0.125},
    },
    # O-series (reasoning models)
    "o1": {
        "standard": {"input": 15.00, "output": 60.00, "cache_read": 7.50},
        "batch": {"input": 7.50, "output": 30.00},
    },
    "o1-pro": {
        "standard": {"input": 150.00, "output": 600.00},
        "batch": {"input": 75.00, "output": 300.00},
    },
    "o1-mini": {
        "standard": {"input": 1.10, "output": 4.40, "cache_read": 0.55},
        "batch": {"input": 0.55, "output": 2.20},
    },
    # O3 series
    "o3": {
        "standard": {"input": 2.00, "output": 8.00, "cache_read": 0.50},
        "flex": {"input": 1.00, "output": 4.00, "cache_read": 0.25},
        "batch": {"input": 1.00, "output": 4.00},
        "priority": {"input": 3.50, "output": 14.00, "cache_read": 0.875},
    },
    "o3-pro": {
        "standard": {"input": 20.00, "output": 80.00},
        "batch": {"input": 10.00, "output": 40.00},
    },
    "o3-mini": {
        "standard": {"input": 1.10, "output": 4.40, "cache_read": 0.55},
        "batch": {"input": 0.55, "output": 2.20},
    },
    "o3-deep-research": {
        "standard": {"input": 10.00, "output": 40.00, "cache_read": 2.50},
        "batch": {"input": 5.00, "output": 20.00},
    },
    # O4 series
    "o4-mini": {
        "standard": {"input": 1.10, "output": 4.40, "cache_read": 0.275},
        "flex": {"input": 0.55, "output": 2.20, "cache_read": 0.138},
        "batch": {"input": 0.55, "output": 2.20},
        "priority": {"input": 2.00, "output": 8.00, "cache_read": 0.50},
    },
    "o4-mini-deep-research": {
        "standard": {"input": 2.00, "output": 8.00, "cache_read": 0.50},
        "batch": {"input": 1.00, "output": 4.00},
    },
    # Computer use preview
    "computer-use-preview": {
        "standard": {"input": 3.00, "output": 12.00},
        "batch": {"input": 1.50, "output": 6.00},
    },
}

# Ollama models are free (local inference)
OLLAMA_PRICING = {
    "_default": {
        "input": 0.0,
        "output": 0.0,
    }
}


def get_model_pricing(
    model_name: str, service_tier: str | None = None
) -> dict[str, float] | None:
    """Get pricing information for a model.

    Args:
        model_name: The model identifier (e.g., "claude-3-5-sonnet-20241022")
        service_tier: OpenAI service tier ("auto", "default", "flex", "batch", "priority").
                     Only applies to OpenAI models. Defaults to "standard" pricing.

    Returns:
        Dictionary with pricing info (input, output, cache_read prices per MTok),
        or None if model pricing is not available.

    Example:
        >>> pricing = get_model_pricing("claude-3-5-haiku-20241022")
        >>> print(f"Input: ${pricing['input']}/MTok, Output: ${pricing['output']}/MTok")
        >>> # OpenAI with flex tier (50% cheaper)
        >>> flex_pricing = get_model_pricing("gpt-4o", service_tier="flex")
    """
    # Check Anthropic models
    if model_name in ANTHROPIC_PRICING:
        return ANTHROPIC_PRICING[model_name]

    # Check Google models
    if model_name in GOOGLE_PRICING:
        return GOOGLE_PRICING[model_name]

    # Check OpenAI models
    if model_name in OPENAI_PRICING:
        model_tiers = OPENAI_PRICING[model_name]

        # Normalize service_tier: "auto" and "default" map to "standard"
        tier = (
            service_tier
            if service_tier in ("flex", "batch", "priority")
            else "standard"
        )

        # Get tier-specific pricing, fallback to standard if tier not available
        if tier in model_tiers:
            return model_tiers[tier].copy()
        elif "standard" in model_tiers:
            return model_tiers["standard"].copy()
        else:
            # Fallback to first available tier if standard not available
            return next(iter(model_tiers.values())).copy()

    # Check if it's an Ollama model (usually no provider prefix or "ollama/" prefix)
    if "/" not in model_name or model_name.startswith("ollama/"):
        return OLLAMA_PRICING["_default"]

    # Unknown model
    return None


def calculate_cost(
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
    service_tier: str | None = None,
) -> dict[str, Any]:
    """Calculate the cost for a model invocation.

    Args:
        model_name: The model identifier
        input_tokens: Number of input/prompt tokens
        output_tokens: Number of output/completion tokens
        cached_tokens: Number of cached tokens (for models with prompt caching)
        service_tier: OpenAI service tier ("auto", "default", "flex", "batch", "priority").
                     Only applies to OpenAI models. Defaults to "default" (standard pricing).

    Returns:
        Dictionary with cost breakdown:
        - total_cost: Total cost in USD
        - input_cost: Cost of input tokens
        - output_cost: Cost of output tokens
        - cache_cost: Cost of cached tokens (if applicable)
        - pricing_available: Whether pricing data was found
        - service_tier: The service tier used (for OpenAI models)

    Example:
        >>> cost = calculate_cost("claude-3-5-haiku-20241022", 1000, 500)
        >>> print(f"Total: ${cost['total_cost']:.6f}")
        >>> # OpenAI with flex tier (50% cheaper)
        >>> flex_cost = calculate_cost("gpt-4o", 1000, 500, service_tier="flex")
    """
    pricing = get_model_pricing(model_name, service_tier=service_tier)

    if pricing is None:
        # Try using LangChain for OpenAI models
        try:
            from langchain_community.callbacks.openai_info import (
                TokenType,
                get_openai_token_cost_for_model,
            )

            input_cost = get_openai_token_cost_for_model(
                model_name, input_tokens, token_type=TokenType.PROMPT
            )
            output_cost = get_openai_token_cost_for_model(
                model_name, output_tokens, token_type=TokenType.COMPLETION
            )

            return {
                "total_cost": input_cost + output_cost,
                "input_cost": input_cost,
                "output_cost": output_cost,
                "cache_cost": 0.0,
                "pricing_available": True,
                "source": "langchain",
            }
        except (ImportError, ValueError):
            # LangChain not available or model not found
            return {
                "total_cost": 0.0,
                "input_cost": 0.0,
                "output_cost": 0.0,
                "cache_cost": 0.0,
                "pricing_available": False,
                "source": "unavailable",
            }

    # Calculate costs (prices are per million tokens)
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]

    # Handle cached tokens if present
    cache_cost = 0.0
    if cached_tokens > 0 and "cache_read" in pricing:
        cache_cost = (cached_tokens / 1_000_000) * pricing["cache_read"]

    result = {
        "total_cost": input_cost + output_cost + cache_cost,
        "input_cost": input_cost,
        "output_cost": output_cost,
        "cache_cost": cache_cost,
        "pricing_available": True,
        "source": "consoul",
    }

    # Add service_tier to result if provided (for OpenAI models)
    if service_tier and model_name in OPENAI_PRICING:
        result["service_tier"] = service_tier

    return result
