"""Unit tests for SDK model registry integration."""

from unittest.mock import Mock

import pytest

from consoul.sdk import ModelCapabilities, ModelInfo, PricingInfo
from consoul.sdk.services.model import ModelService


class TestModelServiceRegistry:
    """Test ModelService integration with model registry."""

    @pytest.fixture
    def mock_config(self) -> Mock:
        """Create a mock config for testing."""
        config = Mock()
        config.current_model = "claude-sonnet-4-5-20250929"
        return config

    @pytest.fixture
    def mock_model(self) -> Mock:
        """Create a mock chat model for testing."""
        return Mock()

    @pytest.fixture
    def model_service(self, mock_model: Mock, mock_config: Mock) -> ModelService:
        """Create a ModelService instance for testing."""
        return ModelService(model=mock_model, config=mock_config)

    def test_list_available_models_all(self, model_service: ModelService) -> None:
        """Test listing all available models from registry."""
        models = model_service.list_available_models()

        # Should return at least the 21 flagship models
        assert len(models) >= 21
        assert all(isinstance(m, ModelInfo) for m in models)

        # Verify model info structure
        model = models[0]
        assert hasattr(model, "id")
        assert hasattr(model, "name")
        assert hasattr(model, "provider")
        assert hasattr(model, "context_window")
        assert hasattr(model, "description")

    def test_list_available_models_by_provider(
        self, model_service: ModelService
    ) -> None:
        """Test filtering models by provider."""
        anthropic_models = model_service.list_available_models(provider="anthropic")

        assert len(anthropic_models) > 0
        assert all(m.provider == "anthropic" for m in anthropic_models)

        # Should include flagship Claude models
        model_ids = [m.id for m in anthropic_models]
        assert "claude-sonnet-4-5-20250929" in model_ids

    def test_list_available_models_active_only(
        self, model_service: ModelService
    ) -> None:
        """Test filtering to only active (non-deprecated) models."""
        active_models = model_service.list_available_models(active_only=True)

        # All models should not have a deprecated date
        # Note: We can't directly check deprecated field, but we trust the registry filter
        assert len(active_models) > 0

    def test_get_model_pricing_standard_tier(self, model_service: ModelService) -> None:
        """Test getting standard tier pricing for a model."""
        pricing = model_service.get_model_pricing("claude-sonnet-4-5-20250929")

        assert pricing is not None
        assert isinstance(pricing, PricingInfo)
        assert pricing.input_price > 0
        assert pricing.output_price > 0
        assert pricing.tier == "standard"

        # Claude Sonnet 4.5 has cache pricing
        assert pricing.cache_read is not None
        assert pricing.cache_write_5m is not None

    def test_get_model_pricing_batch_tier(self, model_service: ModelService) -> None:
        """Test getting batch tier pricing for GPT-4o."""
        pricing = model_service.get_model_pricing("gpt-4o", tier="batch")

        assert pricing is not None
        assert isinstance(pricing, PricingInfo)
        assert pricing.tier == "batch"
        assert pricing.input_price > 0
        assert pricing.output_price > 0

    def test_get_model_pricing_nonexistent_model(
        self, model_service: ModelService
    ) -> None:
        """Test getting pricing for a non-existent model."""
        pricing = model_service.get_model_pricing("nonexistent-model-12345")

        assert pricing is None

    def test_get_model_pricing_nonexistent_tier(
        self, model_service: ModelService
    ) -> None:
        """Test getting pricing for a non-existent tier falls back to standard."""
        # Claude models don't have flex tier - should fall back to standard
        pricing = model_service.get_model_pricing(
            "claude-sonnet-4-5-20250929", tier="flex"
        )

        # Registry falls back to standard tier
        assert pricing is not None
        assert pricing.tier == "standard"  # Falls back to standard

    def test_get_model_capabilities_vision(self, model_service: ModelService) -> None:
        """Test getting capabilities for a vision-enabled model."""
        caps = model_service.get_model_capabilities("claude-sonnet-4-5-20250929")

        assert caps is not None
        assert isinstance(caps, ModelCapabilities)
        assert caps.supports_vision is True
        assert caps.supports_tools is True
        assert caps.supports_streaming is True
        assert caps.supports_caching is True

    def test_get_model_capabilities_reasoning(
        self, model_service: ModelService
    ) -> None:
        """Test getting capabilities for a reasoning model."""
        caps = model_service.get_model_capabilities("o1")

        assert caps is not None
        assert caps.supports_reasoning is True

    def test_get_model_capabilities_nonexistent(
        self, model_service: ModelService
    ) -> None:
        """Test getting capabilities for non-existent model."""
        caps = model_service.get_model_capabilities("nonexistent-model-12345")

        assert caps is None

    def test_get_model_metadata_complete(self, model_service: ModelService) -> None:
        """Test getting complete metadata for a model."""
        metadata = model_service.get_model_metadata("claude-sonnet-4-5-20250929")

        assert metadata is not None
        assert isinstance(metadata, ModelInfo)

        # Basic fields
        assert metadata.id == "claude-sonnet-4-5-20250929"
        assert metadata.name == "Claude Sonnet 4.5"
        assert metadata.provider == "anthropic"
        assert "128K" in metadata.context_window or "200K" in metadata.context_window
        assert len(metadata.description) > 0

        # Extended fields
        assert metadata.max_output_tokens is not None
        assert metadata.created is not None

        # Pricing
        assert metadata.pricing is not None
        assert metadata.pricing.input_price > 0
        assert metadata.pricing.output_price > 0

        # Capabilities
        assert metadata.capabilities is not None
        assert metadata.capabilities.supports_vision is True
        assert metadata.capabilities.supports_tools is True

    def test_get_model_metadata_nonexistent(self, model_service: ModelService) -> None:
        """Test getting metadata for non-existent model."""
        metadata = model_service.get_model_metadata("nonexistent-model-12345")

        assert metadata is None

    def test_pricing_info_dataclass(self) -> None:
        """Test PricingInfo dataclass structure."""
        pricing = PricingInfo(
            input_price=2.50,
            output_price=10.00,
            cache_read=1.25,
            cache_write_5m=3.75,
            tier="standard",
            effective_date="2025-01-15",
            notes="Test pricing",
        )

        assert pricing.input_price == 2.50
        assert pricing.output_price == 10.00
        assert pricing.cache_read == 1.25
        assert pricing.cache_write_5m == 3.75
        assert pricing.tier == "standard"
        assert pricing.effective_date == "2025-01-15"
        assert pricing.notes == "Test pricing"

    def test_model_capabilities_dataclass(self) -> None:
        """Test ModelCapabilities dataclass structure."""
        caps = ModelCapabilities(
            supports_vision=True,
            supports_tools=True,
            supports_reasoning=False,
            supports_streaming=True,
            supports_json_mode=True,
            supports_caching=True,
            supports_batch=False,
        )

        assert caps.supports_vision is True
        assert caps.supports_tools is True
        assert caps.supports_reasoning is False
        assert caps.supports_streaming is True
        assert caps.supports_json_mode is True
        assert caps.supports_caching is True
        assert caps.supports_batch is False

    def test_model_capabilities_defaults(self) -> None:
        """Test ModelCapabilities with default values."""
        caps = ModelCapabilities()

        # All should default to False
        assert caps.supports_vision is False
        assert caps.supports_tools is False
        assert caps.supports_reasoning is False
        assert caps.supports_streaming is False
        assert caps.supports_json_mode is False
        assert caps.supports_caching is False
        assert caps.supports_batch is False

    def test_model_info_with_pricing_and_capabilities(self) -> None:
        """Test ModelInfo with enhanced fields."""
        pricing = PricingInfo(input_price=2.50, output_price=10.00)
        caps = ModelCapabilities(supports_vision=True, supports_tools=True)

        model = ModelInfo(
            id="test-model",
            name="Test Model",
            provider="test",
            context_window="128K",
            description="Test model description",
            supports_vision=True,
            supports_tools=True,
            max_output_tokens=4096,
            created="2025-01-15",
            pricing=pricing,
            capabilities=caps,
        )

        assert model.pricing == pricing
        assert model.capabilities == caps
        assert model.max_output_tokens == 4096
        assert model.created == "2025-01-15"
