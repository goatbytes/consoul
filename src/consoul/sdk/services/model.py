"""ModelService - AI model management and initialization.

Encapsulates model initialization, switching, and tool binding.
Provides SDK-layer interface for model operations without UI dependencies.

Extracted from TUI app.py to enable headless model management.

Example:
    >>> from consoul.sdk.services import ModelService
    >>> service = ModelService.from_config(config)
    >>> model = service.get_model()
    >>> info = service.get_current_model_info()
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel

    from consoul.config import ConsoulConfig
    from consoul.sdk.models import ModelCapabilities, ModelInfo, PricingInfo
    from consoul.sdk.services.tool import ToolService

logger = logging.getLogger(__name__)

__all__ = ["ModelService"]


class ModelService:
    """Service layer for AI model management.

    Encapsulates model initialization, switching, and tool binding.
    Provides clean interface for model operations without LangChain/provider details.

    Attributes:
        config: Consoul configuration
        tool_service: Optional ToolService for binding tools
        current_model_id: Current model identifier

    Example - Basic usage:
        >>> service = ModelService.from_config(config)
        >>> model = service.get_model()
        >>> info = service.get_current_model_info()

    Example - With tool binding:
        >>> service = ModelService.from_config(config, tool_service)
        >>> model = service.get_model()  # Returns model with tools bound

    Example - Model switching:
        >>> service.switch_model("gpt-4o")
        >>> new_model = service.get_model()
    """

    def __init__(
        self,
        model: BaseChatModel,
        config: ConsoulConfig,
        tool_service: ToolService | None = None,
    ) -> None:
        """Initialize model service.

        Args:
            model: Initialized chat model
            config: Consoul configuration
            tool_service: Optional tool service for binding tools
        """
        self._model = model
        self.config = config
        self.tool_service = tool_service
        self.current_model_id = config.current_model

    @classmethod
    def from_config(
        cls,
        config: ConsoulConfig,
        tool_service: ToolService | None = None,
    ) -> ModelService:
        """Create ModelService from configuration.

        Factory method that initializes model from config and binds tools if
        tool_service is provided.

        Extracted from ConsoulApp._initialize_ai_model() (app.py:365-380).

        Args:
            config: Consoul configuration with model settings
            tool_service: Optional tool service for binding tools

        Returns:
            Initialized ModelService ready for use

        Example:
            >>> from consoul.config import load_config
            >>> config = load_config()
            >>> service = ModelService.from_config(config)
        """
        from consoul.ai import get_chat_model

        # Initialize model from config
        model_config = config.get_current_model_config()
        model = get_chat_model(model_config, config=config)

        # Create service instance
        service = cls(model=model, config=config, tool_service=tool_service)

        # Bind tools if tool service provided
        if tool_service:
            service._bind_tools()

        logger.info(f"Initialized ModelService with model: {config.current_model}")
        return service

    def get_model(self) -> BaseChatModel:
        """Get current chat model.

        Returns:
            Current BaseChatModel instance (possibly with tools bound)

        Example:
            >>> model = service.get_model()
            >>> response = model.invoke("Hello!")
        """
        return self._model

    def switch_model(self, model_id: str, provider: str | None = None) -> BaseChatModel:
        """Switch to a different model.

        Reinitializes model with new ID and re-binds tools if applicable.

        Extracted from ConsoulApp._switch_provider_and_model() (app.py:4050-4149).

        Args:
            model_id: New model identifier (e.g., "gpt-4o")
            provider: Optional provider override (auto-detected if None)

        Returns:
            New BaseChatModel instance

        Raises:
            Exception: If model initialization fails

        Example:
            >>> service.switch_model("claude-3-5-sonnet-20241022")
            >>> model = service.get_model()
        """
        from consoul.ai import get_chat_model
        from consoul.config.models import Provider

        # Update config
        if provider:
            self.config.current_provider = Provider(provider)
        self.config.current_model = model_id
        self.current_model_id = model_id

        # Reinitialize model
        model_config = self.config.get_current_model_config()
        self._model = get_chat_model(model_config, config=self.config)

        # Re-bind tools if tool service exists
        if self.tool_service:
            self._bind_tools()

        logger.info(f"Switched to model: {model_id}")
        return self._model

    def _bind_tools(self) -> None:
        """Bind tools to current model.

        Extracted from ConsoulApp._bind_tools_to_model() (app.py:477-517).

        Internal method that binds enabled tools from ToolService to the model
        if it supports function calling.
        """
        if not self.tool_service:
            return

        from typing import cast

        from consoul.ai.providers import supports_tool_calling

        # Get enabled tools
        tool_metadata_list = self.tool_service.tool_registry.list_tools(
            enabled_only=True
        )

        if not tool_metadata_list:
            return

        # Check if model supports tool calling
        if not supports_tool_calling(self._model):
            logger.warning(
                f"Model {self.current_model_id} does not support tool calling. "
                "Tools are disabled for this model."
            )
            return

        # Bind tools
        tools = [meta.tool for meta in tool_metadata_list]
        self._model = cast("BaseChatModel", self._model.bind_tools(tools))
        logger.info(f"Bound {len(tools)} tools to model {self.current_model_id}")

    def list_ollama_models(
        self,
        include_context: bool = False,
        base_url: str = "http://localhost:11434",
    ) -> list[ModelInfo]:
        """List locally installed Ollama models.

        Efficient method to discover what's actually installed on the device.
        No catalog overhead - directly queries Ollama API.

        Args:
            include_context: Fetch detailed context length (slower, requires /api/show per model)
            base_url: Ollama service URL (default: http://localhost:11434)

        Returns:
            List of ModelInfo for installed Ollama models

        Example:
            >>> service = ModelService.from_config()
            >>> local_models = service.list_ollama_models()
            >>> for model in local_models:
            ...     print(f"{model.name} - {model.context_window}")
            llama3.2:latest - 128K
            qwen2.5-coder:7b - 32K

            >>> # Get detailed context info (slower)
            >>> detailed = service.list_ollama_models(include_context=True)
        """
        from consoul.sdk.models import ModelInfo

        try:
            from consoul.ai.providers import get_ollama_models, is_ollama_running

            if not is_ollama_running(base_url=base_url):
                logger.warning(f"Ollama service not running at {base_url}")
                return []

            models = []
            for model_info in get_ollama_models(
                base_url=base_url, include_context=include_context
            ):
                model_name = model_info.get("name", "")
                if not model_name:
                    continue

                # Format context length
                context_length = model_info.get("context_length")
                context_str = self._format_context_length(context_length)

                # Format size
                size_bytes = model_info.get("size", 0)
                size_gb = size_bytes / (1024**3) if size_bytes else 0
                description = f"Local Ollama model ({size_gb:.1f}GB)"

                # Detect vision support from model name
                supports_vision = self._detect_vision_from_name(model_name)

                models.append(
                    ModelInfo(
                        id=model_name,
                        name=model_name,
                        provider="ollama",
                        context_window=context_str,
                        description=description,
                        supports_vision=supports_vision,
                    )
                )

            logger.debug(f"Discovered {len(models)} Ollama models")
            return models

        except Exception as e:
            logger.warning(f"Failed to list Ollama models: {e}")
            return []

    def list_models(self, provider: str | None = None) -> list[ModelInfo]:
        """List available models including dynamically discovered local models.

        Args:
            provider: Filter by provider (None returns all)

        Returns:
            List of ModelInfo objects (static catalog + dynamic local models)

        Example:
            >>> all_models = service.list_models()
            >>> ollama_models = service.list_models(provider="ollama")  # Dynamic discovery
            >>> for model in ollama_models:
            ...     print(f"{model.name}: {model.description}")
        """
        from consoul.sdk.catalog import MODEL_CATALOG, get_models_by_provider

        # Get static catalog models
        if provider:
            static_models = get_models_by_provider(provider)
        else:
            static_models = MODEL_CATALOG.copy()

        # Add dynamic local models if provider matches or if showing all
        local_providers = {"ollama", "llamacpp", "mlx"}
        if provider in local_providers or provider is None:
            dynamic_models = self._discover_local_models(provider)
            static_models.extend(dynamic_models)

        return static_models

    def get_current_model_info(self) -> ModelInfo | None:
        """Get info for current model (tries catalog, then dynamic discovery).

        Returns:
            ModelInfo for current model, or None if not found

        Example:
            >>> info = service.get_current_model_info()
            >>> if info:
            ...     print(f"Context window: {info.context_window}")
        """
        from consoul.sdk.catalog import get_model_info

        # Try static catalog first
        info = get_model_info(self.current_model_id)
        if info:
            return info

        # Try dynamic discovery for local models
        provider = self._detect_provider(self.current_model_id)
        if provider in {"ollama", "llamacpp", "mlx"}:
            dynamic_models = self._discover_local_models(provider)
            return next(
                (m for m in dynamic_models if m.id == self.current_model_id), None
            )

        return None

    def supports_vision(self) -> bool:
        """Check if current model supports vision/images.

        Returns:
            True if model supports vision capabilities

        Example:
            >>> if service.supports_vision():
            ...     # Send image attachment
            ...     pass
        """
        info = self.get_current_model_info()
        if info:
            return info.supports_vision

        # Fallback: Check if model name indicates vision support
        return self._detect_vision_from_name(self.current_model_id)

    def supports_tools(self) -> bool:
        """Check if current model supports tool calling.

        Returns:
            True if model supports function calling

        Example:
            >>> if service.supports_tools():
            ...     # Enable tool execution
            ...     pass
        """
        from consoul.ai.providers import supports_tool_calling

        return supports_tool_calling(self._model)

    def _discover_local_models(self, provider: str | None = None) -> list[ModelInfo]:
        """Discover locally available models (Ollama/LlamaCpp/MLX).

        Args:
            provider: Specific local provider or None for all

        Returns:
            List of dynamically discovered ModelInfo objects
        """
        models = []

        # Discover Ollama models if Ollama is running
        if provider in (None, "ollama"):
            models.extend(self._discover_ollama_models())

        # Note: LlamaCpp and MLX discovery not yet implemented
        # These require filesystem scanning which is expensive
        # Will be added in follow-up work

        return models

    def _discover_ollama_models(self) -> list[ModelInfo]:
        """Discover models from running Ollama service.

        Returns:
            List of Ollama ModelInfo objects
        """
        from consoul.sdk.models import ModelInfo

        try:
            from consoul.ai.providers import get_ollama_models, is_ollama_running

            if not is_ollama_running():
                return []

            models = []
            for model_info in get_ollama_models(include_context=True):
                model_name = model_info.get("name", "")
                if not model_name:
                    continue

                # Format context length
                context_length = model_info.get("context_length")
                context_str = self._format_context_length(context_length)

                # Detect vision support from model name
                supports_vision = self._detect_vision_from_name(model_name)

                models.append(
                    ModelInfo(
                        id=model_name,
                        name=model_name,
                        provider="ollama",
                        context_window=context_str,
                        description="Local Ollama model",
                        supports_vision=supports_vision,
                    )
                )

            logger.debug(f"Discovered {len(models)} Ollama models")
            return models

        except Exception as e:
            logger.warning(f"Failed to discover Ollama models: {e}")
            return []

    def _format_context_length(self, context_length: int | None) -> str:
        """Format context length to human-readable string.

        Args:
            context_length: Context window size in tokens

        Returns:
            Formatted string (e.g., "128K", "1M")
        """
        if not context_length:
            return "?"

        if context_length >= 1_000_000:
            return f"{context_length // 1_000_000}M"
        elif context_length >= 1_000:
            return f"{context_length // 1_000}K"
        else:
            return str(context_length)

    def _detect_provider(self, model_id: str) -> str:
        """Detect provider from model ID.

        Args:
            model_id: Model identifier

        Returns:
            Provider name (best guess)
        """
        model_lower = model_id.lower()

        # Cloud providers (detectable from model name)
        if model_lower.startswith(("gpt-", "o1-", "o3-", "chatgpt-")):
            return "openai"
        elif model_lower.startswith("claude-"):
            return "anthropic"
        elif model_lower.startswith("gemini-"):
            return "google"
        elif "/" in model_id:  # HuggingFace format (org/model)
            return "huggingface"

        # Local providers (harder to detect, use config as fallback)
        return (
            self.config.current_provider.value
            if self.config.current_provider
            else "unknown"
        )

    def _detect_vision_from_name(self, model_name: str) -> bool:
        """Detect vision capability from model name.

        Args:
            model_name: Model name/ID

        Returns:
            True if model name indicates vision support
        """
        model_lower = model_name.lower()

        # Known vision model name patterns
        vision_indicators = [
            "vision",
            "llava",
            "bakllava",
            "minicpm-v",
            "cogvlm",
            "yi-vl",
            "moondream",
            "omnivision",
        ]

        return any(indicator in model_lower for indicator in vision_indicators)

    # Registry-based methods for comprehensive model metadata

    def list_available_models(
        self, provider: str | None = None, active_only: bool = True
    ) -> list[ModelInfo]:
        """List all available models from the registry.

        Fetches comprehensive model metadata from the centralized registry,
        which includes 1,114+ models from Helicone API plus 21 flagship models.

        Args:
            provider: Filter by provider ("openai", "anthropic", "google", etc.)
            active_only: Only return non-deprecated models (default: True)

        Returns:
            List of ModelInfo with enhanced metadata (pricing, capabilities)

        Example:
            >>> models = service.list_available_models(provider="anthropic")
            >>> for model in models:
            ...     print(f"{model.name}: {model.context_window}")
            Claude Opus 4.5: 200K
            Claude Sonnet 4.5: 200K
        """
        from consoul.registry import list_models as registry_list_models
        from consoul.sdk.models import ModelCapabilities, ModelInfo, PricingInfo

        # Get models from registry
        registry_models = registry_list_models(
            provider=provider, active_only=active_only
        )

        # Convert to SDK ModelInfo
        sdk_models = []
        for entry in registry_models:
            # Format context window
            ctx = entry.metadata.context_window
            if ctx >= 1_000_000:
                ctx_str = f"{ctx // 1_000_000}M"
            elif ctx >= 1_000:
                ctx_str = f"{ctx // 1_000}K"
            else:
                ctx_str = str(ctx)

            # Extract capabilities
            caps = ModelCapabilities(
                supports_vision="vision"
                in [c.value for c in entry.metadata.capabilities],
                supports_tools="tools"
                in [c.value for c in entry.metadata.capabilities],
                supports_reasoning="reasoning"
                in [c.value for c in entry.metadata.capabilities],
                supports_streaming="streaming"
                in [c.value for c in entry.metadata.capabilities],
                supports_json_mode="json_mode"
                in [c.value for c in entry.metadata.capabilities],
                supports_caching="caching"
                in [c.value for c in entry.metadata.capabilities],
                supports_batch="batch"
                in [c.value for c in entry.metadata.capabilities],
            )

            # Get default pricing
            pricing_info = None
            if "standard" in entry.pricing:
                tier = entry.pricing["standard"]
                pricing_info = PricingInfo(
                    input_price=tier.input_price,
                    output_price=tier.output_price,
                    cache_read=tier.cache_read,
                    cache_write_5m=tier.cache_write_5m,
                    cache_write_1h=tier.cache_write_1h,
                    thinking_price=tier.thinking_price,
                    tier="standard",
                    effective_date=tier.effective_date.isoformat(),
                    notes=tier.notes,
                )

            model_info = ModelInfo(
                id=entry.metadata.id,
                name=entry.metadata.name,
                provider=entry.metadata.provider,
                context_window=ctx_str,
                description=entry.metadata.description,
                supports_vision=caps.supports_vision,
                supports_tools=caps.supports_tools,
                max_output_tokens=entry.metadata.max_output_tokens,
                created=entry.metadata.created.isoformat(),
                pricing=pricing_info,
                capabilities=caps,
            )
            sdk_models.append(model_info)

        return sdk_models

    def get_model_pricing(
        self, model_id: str, tier: str = "standard"
    ) -> PricingInfo | None:
        """Get pricing information for a specific model.

        Args:
            model_id: Model identifier (e.g., "gpt-4o", "claude-sonnet-4-5-20250929")
            tier: Pricing tier ("standard", "flex", "batch", "priority")

        Returns:
            PricingInfo if model found, None otherwise

        Example:
            >>> pricing = service.get_model_pricing("gpt-4o", tier="flex")
            >>> if pricing:
            ...     print(f"Input: ${pricing.input_price}/MTok")
            ...     print(f"Output: ${pricing.output_price}/MTok")
        """
        from consoul.registry import get_pricing
        from consoul.sdk.models import PricingInfo

        pricing_tier = get_pricing(model_id, tier=tier)
        if not pricing_tier:
            return None

        return PricingInfo(
            input_price=pricing_tier.input_price,
            output_price=pricing_tier.output_price,
            cache_read=pricing_tier.cache_read,
            cache_write_5m=pricing_tier.cache_write_5m,
            cache_write_1h=pricing_tier.cache_write_1h,
            thinking_price=pricing_tier.thinking_price,
            tier=pricing_tier.tier,  # Use actual tier from registry
            effective_date=pricing_tier.effective_date.isoformat(),
            notes=pricing_tier.notes,
        )

    def get_model_capabilities(self, model_id: str) -> ModelCapabilities | None:
        """Get capability information for a specific model.

        Args:
            model_id: Model identifier

        Returns:
            ModelCapabilities if model found, None otherwise

        Example:
            >>> caps = service.get_model_capabilities("claude-sonnet-4-5-20250929")
            >>> if caps and caps.supports_vision and caps.supports_tools:
            ...     print("Model supports both vision and tools")
        """
        from consoul.registry import get_model
        from consoul.sdk.models import ModelCapabilities

        entry = get_model(model_id)
        if not entry:
            return None

        return ModelCapabilities(
            supports_vision="vision" in [c.value for c in entry.metadata.capabilities],
            supports_tools="tools" in [c.value for c in entry.metadata.capabilities],
            supports_reasoning="reasoning"
            in [c.value for c in entry.metadata.capabilities],
            supports_streaming="streaming"
            in [c.value for c in entry.metadata.capabilities],
            supports_json_mode="json_mode"
            in [c.value for c in entry.metadata.capabilities],
            supports_caching="caching"
            in [c.value for c in entry.metadata.capabilities],
            supports_batch="batch" in [c.value for c in entry.metadata.capabilities],
        )

    def get_model_metadata(self, model_id: str) -> ModelInfo | None:
        """Get complete metadata for a specific model.

        Combines all available information (metadata, pricing, capabilities)
        into a single ModelInfo object.

        Args:
            model_id: Model identifier

        Returns:
            ModelInfo if model found, None otherwise

        Example:
            >>> model = service.get_model_metadata("gpt-4o")
            >>> if model:
            ...     print(f"{model.name}")
            ...     print(f"Context: {model.context_window}")
            ...     if model.pricing:
            ...         print(f"Cost: ${model.pricing.input_price}/MTok")
        """
        from consoul.registry import get_model
        from consoul.sdk.models import ModelCapabilities, ModelInfo, PricingInfo

        entry = get_model(model_id)
        if not entry:
            return None

        # Format context window
        ctx = entry.metadata.context_window
        if ctx >= 1_000_000:
            ctx_str = f"{ctx // 1_000_000}M"
        elif ctx >= 1_000:
            ctx_str = f"{ctx // 1_000}K"
        else:
            ctx_str = str(ctx)

        # Extract capabilities
        caps = ModelCapabilities(
            supports_vision="vision" in [c.value for c in entry.metadata.capabilities],
            supports_tools="tools" in [c.value for c in entry.metadata.capabilities],
            supports_reasoning="reasoning"
            in [c.value for c in entry.metadata.capabilities],
            supports_streaming="streaming"
            in [c.value for c in entry.metadata.capabilities],
            supports_json_mode="json_mode"
            in [c.value for c in entry.metadata.capabilities],
            supports_caching="caching"
            in [c.value for c in entry.metadata.capabilities],
            supports_batch="batch" in [c.value for c in entry.metadata.capabilities],
        )

        # Get default pricing
        pricing_info = None
        if "standard" in entry.pricing:
            tier = entry.pricing["standard"]
            pricing_info = PricingInfo(
                input_price=tier.input_price,
                output_price=tier.output_price,
                cache_read=tier.cache_read,
                cache_write_5m=tier.cache_write_5m,
                cache_write_1h=tier.cache_write_1h,
                thinking_price=tier.thinking_price,
                tier="standard",
                effective_date=tier.effective_date.isoformat(),
                notes=tier.notes,
            )

        return ModelInfo(
            id=entry.metadata.id,
            name=entry.metadata.name,
            provider=entry.metadata.provider,
            context_window=ctx_str,
            description=entry.metadata.description,
            supports_vision=caps.supports_vision,
            supports_tools=caps.supports_tools,
            max_output_tokens=entry.metadata.max_output_tokens,
            created=entry.metadata.created.isoformat(),
            pricing=pricing_info,
            capabilities=caps,
        )
