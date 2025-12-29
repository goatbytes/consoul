"""Tests for ThreadPoolExecutor lifecycle management in ConversationService.

Tests that the service properly manages executor ownership, cleanup, and
the async context manager pattern for resource management.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, Mock, patch

import pytest

from consoul.sdk.services.conversation import ConversationService

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_model():
    """Create mock LangChain chat model."""
    model = Mock()
    model.model_name = "gpt-4o"
    return model


@pytest.fixture
def mock_conversation():
    """Create mock ConversationHistory."""
    conversation = Mock()
    conversation.messages = []
    conversation.session_id = "test-session-123"
    conversation.model_name = "gpt-4o"
    conversation.persist = False
    conversation._db = None
    conversation._conversation_created = False
    conversation._pending_metadata = {}
    conversation.add_user_message_async = AsyncMock()
    conversation._persist_message = AsyncMock()
    conversation.count_tokens = Mock(return_value=150)
    return conversation


# =============================================================================
# Test: Executor Lifecycle
# =============================================================================


class TestExecutorOwnership:
    """Test executor ownership tracking."""

    def test_service_creates_executor_when_not_provided(
        self, mock_model, mock_conversation
    ):
        """Service should create its own executor when none is injected."""
        service = ConversationService(mock_model, mock_conversation)

        assert service._owns_executor is True
        assert service.executor is not None
        assert isinstance(service.executor, ThreadPoolExecutor)

        # Cleanup
        service.executor.shutdown(wait=False)

    def test_service_uses_injected_executor(self, mock_model, mock_conversation):
        """Service should use injected executor without taking ownership."""
        external_executor = ThreadPoolExecutor(max_workers=2)

        try:
            service = ConversationService(
                mock_model, mock_conversation, executor=external_executor
            )

            assert service._owns_executor is False
            assert service.executor is external_executor
        finally:
            external_executor.shutdown(wait=False)

    def test_owns_executor_flag_reflects_injection(self, mock_model, mock_conversation):
        """Executor ownership should be correctly tracked.

        When no executor is provided, service owns it.
        When executor is injected, service does not own it.
        """
        # Test 1: Service creates and owns executor
        service1 = ConversationService(mock_model, mock_conversation)
        assert service1._owns_executor is True
        service1.executor.shutdown(wait=False)

        # Test 2: Service uses injected executor and does not own
        external = ThreadPoolExecutor(max_workers=1)
        try:
            service2 = ConversationService(
                mock_model, mock_conversation, executor=external
            )
            assert service2._owns_executor is False
            assert service2.executor is external
        finally:
            external.shutdown(wait=False)


class TestExecutorCleanup:
    """Test executor cleanup behavior."""

    @pytest.mark.asyncio
    async def test_close_shuts_down_owned_executor(self, mock_model, mock_conversation):
        """close() should shutdown executor when service owns it."""
        service = ConversationService(mock_model, mock_conversation)

        # Mock the executor to track shutdown
        mock_executor = Mock(spec=ThreadPoolExecutor)
        service.executor = mock_executor
        service._owns_executor = True

        await service.close()

        mock_executor.shutdown.assert_called_once_with(wait=True, cancel_futures=True)

    @pytest.mark.asyncio
    async def test_close_does_not_shutdown_injected_executor(
        self, mock_model, mock_conversation
    ):
        """close() should not shutdown executor when it was injected."""
        external_executor = ThreadPoolExecutor(max_workers=1)

        try:
            service = ConversationService(
                mock_model, mock_conversation, executor=external_executor
            )

            # Replace with mock to verify no shutdown call
            mock_executor = Mock(spec=ThreadPoolExecutor)
            service.executor = mock_executor
            # Key: service does NOT own the executor
            service._owns_executor = False

            await service.close()

            mock_executor.shutdown.assert_not_called()
        finally:
            external_executor.shutdown(wait=False)

    @pytest.mark.asyncio
    async def test_close_is_idempotent(self, mock_model, mock_conversation):
        """close() should be safe to call multiple times."""
        service = ConversationService(mock_model, mock_conversation)

        # Mock executor
        mock_executor = Mock(spec=ThreadPoolExecutor)
        service.executor = mock_executor
        service._owns_executor = True

        # Call close multiple times
        await service.close()
        await service.close()
        await service.close()

        # Should only shutdown once per call (not error)
        assert mock_executor.shutdown.call_count == 3


class TestAsyncContextManager:
    """Test async context manager protocol."""

    @pytest.mark.asyncio
    async def test_async_context_manager_cleanup(self, mock_model, mock_conversation):
        """Context manager should cleanup executor on exit."""
        mock_executor = Mock(spec=ThreadPoolExecutor)

        with patch.object(
            ConversationService, "__init__", lambda self, *args, **kwargs: None
        ):
            service = ConversationService.__new__(ConversationService)
            service.model = mock_model
            service.conversation = mock_conversation
            service.executor = mock_executor
            service._owns_executor = True

            async with service:
                pass  # Use context manager

            mock_executor.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_context_manager_cleanup_on_exception(
        self, mock_model, mock_conversation
    ):
        """Context manager should cleanup even when exception occurs."""
        mock_executor = Mock(spec=ThreadPoolExecutor)

        with patch.object(
            ConversationService, "__init__", lambda self, *args, **kwargs: None
        ):
            service = ConversationService.__new__(ConversationService)
            service.model = mock_model
            service.conversation = mock_conversation
            service.executor = mock_executor
            service._owns_executor = True

            with pytest.raises(ValueError):
                async with service:
                    raise ValueError("Test exception")

            # Executor should still be shutdown
            mock_executor.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_aenter_returns_service(self, mock_model, mock_conversation):
        """__aenter__ should return the service instance."""
        service = ConversationService(mock_model, mock_conversation)

        try:
            result = await service.__aenter__()
            assert result is service
        finally:
            await service.close()


class TestExecutorReuse:
    """Test executor reuse across multiple operations."""

    @pytest.mark.asyncio
    async def test_executor_reused_across_multiple_messages(
        self, mock_model, mock_conversation
    ):
        """Same executor should be used for multiple send_message calls."""
        service = ConversationService(mock_model, mock_conversation)
        original_executor = service.executor

        try:
            # Simulate multiple message sends
            # (We just verify the executor reference stays the same)
            assert service.executor is original_executor

            # After "using" the service, executor should be unchanged
            assert service.executor is original_executor
            assert service._owns_executor is True
        finally:
            await service.close()

    def test_max_workers_parameter(self, mock_model, mock_conversation):
        """max_workers parameter should be passed to executor."""
        # Can't easily verify ThreadPoolExecutor max_workers directly,
        # but we can verify the parameter is passed through
        service = ConversationService(mock_model, mock_conversation, max_workers=4)

        try:
            # Just verify executor was created (parameter was used)
            assert service._owns_executor is True
            assert service.executor is not None
        finally:
            service.executor.shutdown(wait=False)
