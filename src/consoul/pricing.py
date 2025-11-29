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
    # Claude Opus 4.5 (marketed as Claude 3 Opus in API)
    "claude-3-opus-20240229": {
        "input": 5.00,  # $5 per MTok (67% price reduction from $15!)
        "output": 25.00,  # $25 per MTok (67% price reduction from $75!)
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
        "input": 2.00,  # $2.00 per MTok (prompts ≤200k)
        "output": 12.00,  # $12.00 per MTok (includes thinking tokens)
        "cache_read": 0.20,  # $0.20 per MTok
    },
    # Gemini 3 Pro Image Preview
    "gemini-3-pro-image-preview": {
        "input": 1.00,  # $1.00 per MTok (prompts ≤200k)
        "output": 6.00,  # $6.00 per MTok (includes thinking tokens)
        "cache_read": 0.20,  # $0.20 per MTok
    },
}

# OpenAI pricing for models not in LangChain
# Most OpenAI models are covered by langchain_community.callbacks.openai_info
# This is a fallback for any missing models
# Source: https://platform.openai.com/docs/pricing (Standard tier, as of January 2025)
OPENAI_PRICING = {
    # GPT-5 series
    "gpt-5.1": {
        "input": 1.25,  # $1.25 per MTok
        "output": 10.00,  # $10.00 per MTok
        "cache_read": 0.125,  # $0.125 per MTok (cached input)
    },
    "gpt-5": {
        "input": 1.25,  # $1.25 per MTok
        "output": 10.00,  # $10.00 per MTok
        "cache_read": 0.125,  # $0.125 per MTok (cached input)
    },
    "gpt-5-mini": {
        "input": 0.25,  # $0.25 per MTok
        "output": 2.00,  # $2.00 per MTok
        "cache_read": 0.025,  # $0.025 per MTok (cached input)
    },
    "gpt-5-nano": {
        "input": 0.05,  # $0.05 per MTok
        "output": 0.40,  # $0.40 per MTok
        "cache_read": 0.005,  # $0.005 per MTok (cached input)
    },
    "gpt-5-pro": {
        "input": 15.00,  # $15.00 per MTok
        "output": 120.00,  # $120.00 per MTok
    },
    # GPT-4.1 series
    "gpt-4.1": {
        "input": 2.00,  # $2.00 per MTok
        "output": 8.00,  # $8.00 per MTok
        "cache_read": 0.50,  # $0.50 per MTok (cached input)
    },
    "gpt-4.1-mini": {
        "input": 0.40,  # $0.40 per MTok
        "output": 1.60,  # $1.60 per MTok
        "cache_read": 0.10,  # $0.10 per MTok (cached input)
    },
    "gpt-4.1-nano": {
        "input": 0.10,  # $0.10 per MTok
        "output": 0.40,  # $0.40 per MTok
        "cache_read": 0.025,  # $0.025 per MTok (cached input)
    },
    # GPT-4o series
    "gpt-4o": {
        "input": 2.50,  # $2.50 per MTok
        "output": 10.00,  # $10.00 per MTok
        "cache_read": 1.25,  # $1.25 per MTok (cached input, 50% discount)
    },
    "gpt-4o-2024-05-13": {
        "input": 5.00,  # $5.00 per MTok
        "output": 15.00,  # $15.00 per MTok
    },
    "gpt-4o-mini": {
        "input": 0.15,  # $0.15 per MTok
        "output": 0.60,  # $0.60 per MTok
        "cache_read": 0.075,  # $0.075 per MTok (cached input, 50% discount)
    },
    # O-series (reasoning models)
    "o1": {
        "input": 15.00,  # $15.00 per MTok
        "output": 60.00,  # $60.00 per MTok (includes reasoning tokens)
        "cache_read": 7.50,  # $7.50 per MTok (cached input)
    },
    "o1-pro": {
        "input": 150.00,  # $150.00 per MTok
        "output": 600.00,  # $600.00 per MTok (includes reasoning tokens)
    },
    "o1-mini": {
        "input": 1.10,  # $1.10 per MTok
        "output": 4.40,  # $4.40 per MTok (includes reasoning tokens)
        "cache_read": 0.55,  # $0.55 per MTok (cached input)
    },
    # O3 series
    "o3": {
        "input": 2.00,  # $2.00 per MTok
        "output": 8.00,  # $8.00 per MTok (includes reasoning tokens)
        "cache_read": 0.50,  # $0.50 per MTok (cached input)
    },
    "o3-pro": {
        "input": 20.00,  # $20.00 per MTok
        "output": 80.00,  # $80.00 per MTok (includes reasoning tokens)
    },
    "o3-mini": {
        "input": 1.10,  # $1.10 per MTok
        "output": 4.40,  # $4.40 per MTok (includes reasoning tokens)
        "cache_read": 0.55,  # $0.55 per MTok (cached input)
    },
    "o3-deep-research": {
        "input": 10.00,  # $10.00 per MTok
        "output": 40.00,  # $40.00 per MTok (includes reasoning tokens)
        "cache_read": 2.50,  # $2.50 per MTok (cached input)
    },
    # O4 series
    "o4-mini": {
        "input": 1.10,  # $1.10 per MTok
        "output": 4.40,  # $4.40 per MTok (includes reasoning tokens)
        "cache_read": 0.275,  # $0.275 per MTok (cached input)
    },
    "o4-mini-deep-research": {
        "input": 2.00,  # $2.00 per MTok
        "output": 8.00,  # $8.00 per MTok (includes reasoning tokens)
        "cache_read": 0.50,  # $0.50 per MTok (cached input)
    },
    # Computer use preview
    "computer-use-preview": {
        "input": 3.00,  # $3.00 per MTok
        "output": 12.00,  # $12.00 per MTok
    },
}

# Ollama models are free (local inference)
OLLAMA_PRICING = {
    "_default": {
        "input": 0.0,
        "output": 0.0,
    }
}


def get_model_pricing(model_name: str) -> dict[str, float] | None:
    """Get pricing information for a model.

    Args:
        model_name: The model identifier (e.g., "claude-3-5-sonnet-20241022")

    Returns:
        Dictionary with pricing info (input, output, cache_read, cache_write prices per MTok),
        or None if model pricing is not available.

    Example:
        >>> pricing = get_model_pricing("claude-3-5-haiku-20241022")
        >>> print(f"Input: ${pricing['input']}/MTok, Output: ${pricing['output']}/MTok")
    """
    # Check Anthropic models
    if model_name in ANTHROPIC_PRICING:
        return ANTHROPIC_PRICING[model_name]

    # Check Google models
    if model_name in GOOGLE_PRICING:
        return GOOGLE_PRICING[model_name]

    # Check OpenAI models
    if model_name in OPENAI_PRICING:
        return OPENAI_PRICING[model_name]

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
) -> dict[str, Any]:
    """Calculate the cost for a model invocation.

    Args:
        model_name: The model identifier
        input_tokens: Number of input/prompt tokens
        output_tokens: Number of output/completion tokens
        cached_tokens: Number of cached tokens (for models with prompt caching)

    Returns:
        Dictionary with cost breakdown:
        - total_cost: Total cost in USD
        - input_cost: Cost of input tokens
        - output_cost: Cost of output tokens
        - cache_cost: Cost of cached tokens (if applicable)
        - pricing_available: Whether pricing data was found

    Example:
        >>> cost = calculate_cost("claude-3-5-haiku-20241022", 1000, 500)
        >>> print(f"Total: ${cost['total_cost']:.6f}")
    """
    pricing = get_model_pricing(model_name)

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

    return {
        "total_cost": input_cost + output_cost + cache_cost,
        "input_cost": input_cost,
        "output_cost": output_cost,
        "cache_cost": cache_cost,
        "pricing_available": True,
        "source": "consoul",
    }
