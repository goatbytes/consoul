"""Model pricing data for accurate cost calculations.

This module provides pricing information for AI models from various providers.
Pricing data is updated as of November 2024.

For OpenAI models, we use LangChain's built-in pricing data when available.
For other providers (Anthropic, Google, etc.), we maintain static pricing.

Prices are in USD per million tokens (MTok).
"""

from __future__ import annotations

from typing import Any

# Anthropic Claude pricing (as of November 2024)
# Source: https://claude.com/pricing
ANTHROPIC_PRICING = {
    # Claude 3.5 Sonnet (latest)
    "claude-3-5-sonnet-20241022": {
        "input": 3.00,  # $3 per MTok
        "output": 15.00,  # $15 per MTok
        "cache_write": 3.75,  # $3.75 per MTok
        "cache_read": 0.30,  # $0.30 per MTok
    },
    "claude-3-5-sonnet-20240620": {
        "input": 3.00,
        "output": 15.00,
        "cache_write": 3.75,
        "cache_read": 0.30,
    },
    # Claude 3.5 Haiku
    "claude-3-5-haiku-20241022": {
        "input": 1.00,  # $1 per MTok
        "output": 5.00,  # $5 per MTok
        "cache_write": 1.25,  # $1.25 per MTok
        "cache_read": 0.10,  # $0.10 per MTok
    },
    # Claude 3 Opus
    "claude-3-opus-20240229": {
        "input": 15.00,  # $15 per MTok
        "output": 75.00,  # $75 per MTok
        "cache_write": 18.75,  # $18.75 per MTok
        "cache_read": 1.50,  # $1.50 per MTok
    },
    # Claude 3 Sonnet
    "claude-3-sonnet-20240229": {
        "input": 3.00,
        "output": 15.00,
        "cache_write": 3.75,
        "cache_read": 0.30,
    },
    # Claude 3 Haiku
    "claude-3-haiku-20240307": {
        "input": 0.25,  # $0.25 per MTok
        "output": 1.25,  # $1.25 per MTok
        "cache_write": 0.30,  # $0.30 per MTok
        "cache_read": 0.03,  # $0.03 per MTok
    },
}

# Google Gemini pricing (as of November 2024)
# Source: https://ai.google.dev/pricing
GOOGLE_PRICING = {
    # Gemini 2.0 Flash
    "gemini-2.0-flash-exp": {
        "input": 0.10,  # $0.10 per MTok (text/image/video)
        "output": 0.40,  # $0.40 per MTok
        "cache_read": 0.025,  # $0.025 per MTok
        "cache_storage": 1.00,  # $1.00 per MTok per hour
    },
    # Gemini 1.5 Pro
    "gemini-1.5-pro": {
        "input": 1.25,  # $1.25 per MTok (≤128K tokens)
        "output": 5.00,  # $5.00 per MTok
        "cache_read": 0.3125,  # $0.3125 per MTok
    },
    "gemini-1.5-pro-latest": {
        "input": 1.25,
        "output": 5.00,
        "cache_read": 0.3125,
    },
    # Gemini 1.5 Flash
    "gemini-1.5-flash": {
        "input": 0.075,  # $0.075 per MTok (≤128K tokens)
        "output": 0.30,  # $0.30 per MTok
        "cache_read": 0.01875,  # $0.01875 per MTok
    },
    "gemini-1.5-flash-latest": {
        "input": 0.075,
        "output": 0.30,
        "cache_read": 0.01875,
    },
}

# OpenAI pricing for models not in LangChain
# Most OpenAI models are covered by langchain_community.callbacks.openai_info
# This is a fallback for any missing models
OPENAI_PRICING = {
    "gpt-4o": {
        "input": 2.50,  # $2.50 per MTok
        "output": 10.00,  # $10.00 per MTok
        "cache_read": 1.25,  # $1.25 per MTok (cached input)
    },
    "gpt-4o-mini": {
        "input": 0.15,  # $0.15 per MTok
        "output": 0.60,  # $0.60 per MTok
        "cache_read": 0.075,  # $0.075 per MTok (cached input)
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
