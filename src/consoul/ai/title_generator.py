"""Automatic conversation title generation using LLMs.

This module provides functionality to automatically generate short, descriptive
titles for conversations using any LangChain-compatible LLM provider.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel

    from consoul.config import ConsoulConfig

__all__ = ["TitleGenerator", "auto_detect_title_config"]

logger = logging.getLogger(__name__)


class TitleGenerator:
    """Generate conversation titles using LLM.

    Supports any LangChain-compatible model provider (OpenAI, Anthropic,
    Google, Ollama, etc.) for generating concise conversation titles.

    Attributes:
        provider: LLM provider name
        model_name: Model identifier
        prompt_template: Template string with {user_message} and {assistant_message}
        max_tokens: Maximum tokens for generated title
        temperature: Generation temperature
        model: Initialized LangChain model instance
    """

    def __init__(
        self,
        provider: str,
        model_name: str,
        prompt_template: str,
        max_tokens: int = 20,
        temperature: float = 0.7,
        api_key: str | None = None,
        config: ConsoulConfig | None = None,
    ) -> None:
        """Initialize title generator.

        Args:
            provider: Provider name (openai, anthropic, google, ollama)
            model_name: Model identifier
            prompt_template: Template with {user_message} and {assistant_message}
            max_tokens: Maximum tokens for title
            temperature: Generation temperature
            api_key: Optional API key override
            config: Optional Consoul config for shared settings
        """
        self.provider = provider
        self.model_name = model_name
        self.prompt_template = prompt_template
        self.max_tokens = max_tokens
        self.temperature = temperature

        # Initialize model
        self.model = self._create_model(api_key, config)

    def _create_model(
        self, api_key: str | None, config: ConsoulConfig | None
    ) -> BaseChatModel:
        """Create LangChain model instance.

        Args:
            api_key: Optional API key override
            config: Optional Consoul config

        Returns:
            Initialized BaseChatModel instance
        """
        from pydantic import SecretStr

        from consoul.ai import get_chat_model
        from consoul.config.models import (
            AnthropicModelConfig,
            GoogleModelConfig,
            ModelConfig,
            OllamaModelConfig,
            OpenAIModelConfig,
        )

        # Build model config based on provider
        provider_lower = self.provider.lower()
        model_config: ModelConfig
        if provider_lower == "openai":
            model_config = OpenAIModelConfig(
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        elif provider_lower == "anthropic":
            model_config = AnthropicModelConfig(
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        elif provider_lower == "google":
            model_config = GoogleModelConfig(
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        elif provider_lower == "ollama":
            model_config = OllamaModelConfig(
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        else:
            # Fallback to OpenAI
            model_config = OpenAIModelConfig(
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )

        # Convert api_key to SecretStr if provided
        secret_key = SecretStr(api_key) if api_key else None

        return get_chat_model(model_config, api_key=secret_key, config=config)

    async def generate_title(self, user_message: str, assistant_message: str) -> str:
        """Generate title from first conversation exchange.

        Args:
            user_message: First user message
            assistant_message: First assistant response

        Returns:
            Generated title string (typically 2-8 words)
        """
        # Format prompt with message content
        # Limit length to avoid context issues
        prompt = self.prompt_template.format(
            user_message=user_message[:500], assistant_message=assistant_message[:500]
        )

        # Generate title asynchronously
        response = await self.model.ainvoke(prompt)

        # Extract and clean title
        title = str(response.content).strip()

        # Remove quotes if present
        if title.startswith('"') and title.endswith('"'):
            title = title[1:-1]
        if title.startswith("'") and title.endswith("'"):
            title = title[1:-1]

        # Truncate if too long
        if len(title) > 100:
            title = title[:97] + "..."

        return title


def auto_detect_title_config(config: ConsoulConfig | None = None) -> dict | None:  # type: ignore[type-arg]
    """Auto-detect best available model for title generation.

    Preference order:
    1. Ollama (free, local, fast) - if running and has suitable model
    2. Main chat model - if using cheap model
    3. None - disable feature

    Args:
        config: Optional Consoul config

    Returns:
        Dict with "provider" and "model" keys, or None if no suitable model found
    """
    from consoul.ai.providers import is_ollama_running, select_best_ollama_model

    # Try Ollama first (free and local)
    if is_ollama_running():
        model = select_best_ollama_model()
        if model:
            return {
                "provider": "ollama",
                "model": model,
            }

    # Check if user's main model is cheap enough to reuse
    if config:
        try:
            profile = config.get_active_profile()
            provider = profile.model.provider
            model = profile.model.model

            # Reuse main model if it's a cheap one
            cheap_models = [
                "gpt-4o-mini",
                "gpt-3.5-turbo",
                "claude-3-haiku",
                "gemini-1.5-flash",
            ]

            if any(cheap in model for cheap in cheap_models):
                return {
                    "provider": provider,
                    "model": model,
                }
        except Exception:
            pass

    # No suitable model found
    return None
