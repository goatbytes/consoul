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
    from consoul.sdk.models import ModelInfo
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

    def list_models(self, provider: str | None = None) -> list[ModelInfo]:
        """List available models.

        Args:
            provider: Filter by provider (None returns all)

        Returns:
            List of ModelInfo objects

        Example:
            >>> all_models = service.list_models()
            >>> openai_models = service.list_models(provider="openai")
            >>> for model in openai_models:
            ...     print(f"{model.name}: {model.description}")
        """
        from consoul.sdk.catalog import MODEL_CATALOG, get_models_by_provider

        if provider:
            return get_models_by_provider(provider)
        return MODEL_CATALOG.copy()

    def get_current_model_info(self) -> ModelInfo | None:
        """Get info for current model.

        Returns:
            ModelInfo for current model, or None if not found

        Example:
            >>> info = service.get_current_model_info()
            >>> if info:
            ...     print(f"Context window: {info.context_window}")
        """
        from consoul.sdk.catalog import get_model_info

        return get_model_info(self.current_model_id)

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
        return info.supports_vision if info else False

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
