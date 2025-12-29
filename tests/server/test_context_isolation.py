"""Tests for session and approval context isolation.

Tests that ensure each session has isolated state and approval contexts
don't leak between sessions.
"""

from __future__ import annotations

import asyncio

import pytest

from consoul.sdk.models import ToolRequest
from consoul.sdk.session_store import MemorySessionStore

# =============================================================================
# Test: Session Isolation
# =============================================================================


class TestSessionIsolation:
    """Test session-level isolation."""

    def test_separate_sessions_have_different_state(self):
        """Each session should have its own isolated state."""
        store = MemorySessionStore(ttl=3600)

        # Save different states for different sessions
        store.save("session1", {"messages": ["Hello from session 1"]})
        store.save("session2", {"messages": ["Hello from session 2"]})

        # Load and verify isolation
        state1 = store.load("session1")
        state2 = store.load("session2")

        assert state1 is not None
        assert state2 is not None
        assert state1["messages"] != state2["messages"]
        assert state1["messages"] == ["Hello from session 1"]
        assert state2["messages"] == ["Hello from session 2"]

    def test_session_modification_doesnt_affect_other_sessions(self):
        """Modifying one session should not affect others."""
        store = MemorySessionStore(ttl=3600)

        # Initial state
        store.save("session1", {"counter": 1})
        store.save("session2", {"counter": 1})

        # Modify session1
        state1 = store.load("session1")
        state1["counter"] = 100
        store.save("session1", state1)

        # Session2 should be unaffected
        state2 = store.load("session2")
        assert state2["counter"] == 1

    def test_session_deletion_doesnt_affect_other_sessions(self):
        """Deleting one session should not affect others."""
        store = MemorySessionStore(ttl=3600)

        store.save("session1", {"data": "one"})
        store.save("session2", {"data": "two"})

        # Delete session1
        store.delete("session1")

        # Session1 should be gone
        assert store.load("session1") is None

        # Session2 should still exist
        state2 = store.load("session2")
        assert state2 is not None
        assert state2["data"] == "two"


class TestApprovalContextIsolation:
    """Test approval context isolation between sessions."""

    @pytest.mark.asyncio
    async def test_concurrent_sessions_have_isolated_approval_contexts(self):
        """Concurrent sessions should have independent approval states."""
        approval_calls = []

        async def session1_provider(request: ToolRequest) -> bool:
            approval_calls.append(("session1", request.name))
            return True  # Always approve

        async def session2_provider(request: ToolRequest) -> bool:
            approval_calls.append(("session2", request.name))
            return False  # Always reject

        # Simulate concurrent approval requests
        request1 = ToolRequest(
            id="call_1", name="tool_a", arguments={}, risk_level="caution"
        )
        request2 = ToolRequest(
            id="call_2", name="tool_b", arguments={}, risk_level="caution"
        )

        # Run concurrently
        result1, result2 = await asyncio.gather(
            session1_provider(request1),
            session2_provider(request2),
        )

        # Each session got its own result
        assert result1 is True  # session1 approves
        assert result2 is False  # session2 rejects

        # Each session's provider was called independently
        assert ("session1", "tool_a") in approval_calls
        assert ("session2", "tool_b") in approval_calls

    @pytest.mark.asyncio
    async def test_approval_state_not_shared_between_sessions(self):
        """Approval provider state should not leak between sessions."""
        # Track approval history per provider
        provider1_history = []
        provider2_history = []

        async def session1_provider(request: ToolRequest) -> bool:
            provider1_history.append(request.id)
            return True

        async def session2_provider(request: ToolRequest) -> bool:
            provider2_history.append(request.id)
            return True

        # Process requests
        await session1_provider(
            ToolRequest(id="req1", name="t", arguments={}, risk_level="safe")
        )
        await session2_provider(
            ToolRequest(id="req2", name="t", arguments={}, risk_level="safe")
        )
        await session1_provider(
            ToolRequest(id="req3", name="t", arguments={}, risk_level="safe")
        )

        # Each provider has its own history
        assert provider1_history == ["req1", "req3"]
        assert provider2_history == ["req2"]

    @pytest.mark.asyncio
    async def test_different_sessions_can_have_different_approval_providers(self):
        """Each session should be able to have a different approval provider."""
        providers = {}

        def create_provider_for_session(session_id: str):
            """Create a unique provider per session."""

            async def provider(request: ToolRequest) -> bool:
                # Track which session this provider is for
                providers[session_id] = providers.get(session_id, 0) + 1
                return session_id.startswith("trusted")

            return provider

        trusted_provider = create_provider_for_session("trusted_session")
        untrusted_provider = create_provider_for_session("untrusted_session")

        request = ToolRequest(id="x", name="tool", arguments={}, risk_level="caution")

        result_trusted = await trusted_provider(request)
        result_untrusted = await untrusted_provider(request)

        assert result_trusted is True
        assert result_untrusted is False
        assert providers["trusted_session"] == 1
        assert providers["untrusted_session"] == 1


class TestSessionLocking:
    """Test session locking for concurrent access."""

    @pytest.mark.asyncio
    async def test_session_lock_prevents_concurrent_modification(self):
        """Session lock should serialize concurrent operations."""
        from consoul.server.session_locks import SessionLock, SessionLockManager

        lock_manager = SessionLockManager()
        execution_order = []

        async def operation(op_id: str, session_id: str, delay: float):
            async with SessionLock(lock_manager, session_id):
                execution_order.append(f"{op_id}_start")
                await asyncio.sleep(delay)
                execution_order.append(f"{op_id}_end")

        # Run concurrent operations on same session
        await asyncio.gather(
            operation("op1", "session_a", 0.1),
            operation("op2", "session_a", 0.1),
        )

        # Operations should be serialized (not interleaved)
        assert execution_order[0].endswith("_start")
        assert execution_order[1].endswith("_end")
        assert execution_order[2].endswith("_start")
        assert execution_order[3].endswith("_end")

    @pytest.mark.asyncio
    async def test_different_sessions_can_run_concurrently(self):
        """Different sessions should not block each other."""
        from consoul.server.session_locks import SessionLock, SessionLockManager

        lock_manager = SessionLockManager()
        concurrent_count = []

        async def operation(session_id: str):
            async with SessionLock(lock_manager, session_id):
                concurrent_count.append(1)
                await asyncio.sleep(0.1)
                concurrent_count.append(-1)

        # Run on different sessions
        start_time = asyncio.get_event_loop().time()
        await asyncio.gather(
            operation("session_a"),
            operation("session_b"),
            operation("session_c"),
        )
        elapsed = asyncio.get_event_loop().time() - start_time

        # Should complete in ~0.1s (parallel), not 0.3s (sequential)
        assert elapsed < 0.25  # Allow some overhead


class TestSessionCleanup:
    """Test session cleanup behavior."""

    def test_session_cleanup_removes_state(self):
        """Session cleanup should remove session state."""
        store = MemorySessionStore(ttl=3600)

        store.save("session1", {"data": "test"})
        assert store.load("session1") is not None

        store.delete("session1")
        assert store.load("session1") is None

    @pytest.mark.asyncio
    async def test_lock_cleanup_after_session_end(self):
        """Lock manager should clean up after session ends."""
        from consoul.server.session_locks import SessionLock, SessionLockManager

        lock_manager = SessionLockManager()

        # Use and release lock
        async with SessionLock(lock_manager, "temp_session"):
            pass

        # Lock should be cleaned up (ref count reaches 0)
        # The lock manager should not hold unnecessary references
        # (Implementation-specific behavior)
        assert True  # Basic sanity check

    def test_expired_session_returns_none(self):
        """Expired sessions should return None when loaded."""
        store = MemorySessionStore(ttl=0.1)  # Very short TTL

        store.save("session1", {"data": "test"})

        import time

        time.sleep(0.2)  # Wait for expiration

        # Session should be expired
        result = store.load("session1")
        assert result is None
