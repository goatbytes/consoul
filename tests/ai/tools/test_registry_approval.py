"""Tests for ToolRegistry approval integration."""

import pytest
from langchain_core.tools import tool

from consoul.ai.tools import RiskLevel, ToolRegistry
from consoul.config.models import ToolConfig

# Import mock providers from test_approval
from tests.ai.tools.test_approval import (
    MockApproveProvider,
    MockDenyProvider,
    MockRaisingProvider,
)

pytestmark = pytest.mark.asyncio


@pytest.fixture
def sample_tool():
    """Create a sample tool for testing."""

    @tool
    def test_tool(x: int) -> int:
        """Test tool"""
        return x * 2

    return test_tool


class TestRegistryApprovalIntegration:
    """Test ToolRegistry with approval providers."""

    async def test_registry_with_approve_provider(self, sample_tool):
        """Test registry uses approval provider."""
        provider = MockApproveProvider()
        config = ToolConfig(enabled=True)
        registry = ToolRegistry(config, approval_provider=provider)

        registry.register(sample_tool, risk_level=RiskLevel.SAFE)

        response = await registry.request_tool_approval(
            "test_tool",
            {"x": 5},
            tool_call_id="call_1",
        )

        assert response.approved is True

    async def test_registry_with_deny_provider(self, sample_tool):
        """Test registry handles denial."""
        provider = MockDenyProvider()
        config = ToolConfig(enabled=True)
        registry = ToolRegistry(config, approval_provider=provider)

        registry.register(sample_tool)

        response = await registry.request_tool_approval(
            "test_tool",
            {"x": 5},
            tool_call_id="call_1",
        )

        assert response.approved is False
        assert response.reason is not None

    async def test_approval_caching_once_per_session(self, sample_tool):
        """Test once_per_session mode caches approvals."""
        provider = MockApproveProvider()
        config = ToolConfig(enabled=True, approval_mode="once_per_session")
        registry = ToolRegistry(config, approval_provider=provider)
        registry.register(sample_tool)

        # First request: should call provider
        response1 = await registry.request_tool_approval(
            "test_tool",
            {"x": 5},
            tool_call_id="call_1",
        )
        assert response1.approved is True

        # Second request: should use cache
        response2 = await registry.request_tool_approval(
            "test_tool",
            {"x": 10},
            tool_call_id="call_2",
        )
        assert response2.approved is True
        assert "Cached" in response2.reason

    async def test_provider_error_returns_denial(self, sample_tool):
        """Test provider exceptions are handled as denial."""
        provider = MockRaisingProvider()
        config = ToolConfig(enabled=True)
        registry = ToolRegistry(config, approval_provider=provider)
        registry.register(sample_tool)

        response = await registry.request_tool_approval(
            "test_tool",
            {"x": 5},
            tool_call_id="call_1",
        )

        assert response.approved is False
        assert "error" in response.reason.lower()

    async def test_request_with_context(self, sample_tool):
        """Test approval request includes context."""
        provider = MockApproveProvider()
        config = ToolConfig(enabled=True)
        registry = ToolRegistry(config, approval_provider=provider)
        registry.register(sample_tool)

        response = await registry.request_tool_approval(
            "test_tool",
            {"x": 5},
            tool_call_id="call_1",
            context={"user": "test_user"},
        )

        assert response.approved is True

    async def test_approval_for_dangerous_tool(self, sample_tool):
        """Test approval request for dangerous tool."""
        provider = MockApproveProvider()
        config = ToolConfig(enabled=True)
        registry = ToolRegistry(config, approval_provider=provider)

        # Register as dangerous
        registry.register(sample_tool, risk_level=RiskLevel.DANGEROUS)

        response = await registry.request_tool_approval(
            "test_tool",
            {"x": 5},
            tool_call_id="call_1",
        )

        assert response.approved is True

    async def test_approval_for_nonexistent_tool(self):
        """Test approval for non-existent tool raises error."""
        from consoul.ai.tools.exceptions import ToolNotFoundError

        provider = MockApproveProvider()
        config = ToolConfig(enabled=True)
        registry = ToolRegistry(config, approval_provider=provider)

        with pytest.raises(ToolNotFoundError):
            await registry.request_tool_approval(
                "nonexistent",
                {},
                tool_call_id="call_1",
            )


class TestRegistryWithoutProvider:
    """Test ToolRegistry without approval provider."""

    def test_registry_without_provider_raises_error(self):
        """Test registry without provider and TUI raises error."""
        config = ToolConfig(enabled=True)

        # Should raise RuntimeError when no provider and TUI not available
        with pytest.raises(RuntimeError, match="No approval provider"):
            ToolRegistry(config)
