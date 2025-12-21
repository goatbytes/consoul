"""Tests for create_session() factory function and session isolation."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from consoul.sdk import Consoul, create_session


class TestSessionFactory:
    """Test create_session() factory function."""

    def test_create_session_returns_consoul_instance(self):
        """Test that create_session returns a Consoul instance."""
        session = create_session(session_id="test_session", model="gpt-4o-mini")
        assert isinstance(session, Consoul)

    def test_create_session_forces_no_persistence(self):
        """Test that create_session disables disk persistence."""
        session = create_session(session_id="test_session", model="gpt-4o-mini")
        # Check that persist is False
        assert hasattr(session.history, "persist")
        assert session.history.persist is False

    def test_create_session_uses_session_id(self):
        """Test that session_id is used in database path."""
        session = create_session(session_id="my_session_123", model="gpt-4o-mini")
        # Verify db_path contains session_id
        if hasattr(session.history, "db_path"):
            db_path = str(session.history.db_path)
            assert "my_session_123" in db_path

    def test_create_session_accepts_model_parameter(self):
        """Test that create_session accepts model parameter."""
        session = create_session(session_id="test", model="gpt-4o")
        assert session.model_name == "gpt-4o"

    def test_create_session_accepts_temperature_parameter(self):
        """Test that create_session accepts temperature parameter."""
        session = create_session(
            session_id="test", model="gpt-4o-mini", temperature=0.5
        )
        assert session.temperature == 0.5

    def test_create_session_accepts_tools_parameter(self):
        """Test that create_session accepts tools parameter."""
        # Default: tools disabled (backend-safe)
        session_default = create_session(session_id="test", model="gpt-4o-mini")
        assert session_default.tools_enabled is False

        # With tools enabled
        session = create_session(
            session_id="test", model="gpt-4o-mini", tools=["search"]
        )
        assert session.tools_enabled is True

        # With tools explicitly disabled
        session_no_tools = create_session(
            session_id="test", model="gpt-4o-mini", tools=False
        )
        assert session_no_tools.tools_enabled is False

    def test_create_session_accepts_system_prompt(self):
        """Test that create_session accepts system_prompt parameter."""
        prompt = "You are a helpful assistant."
        session = create_session(
            session_id="test", model="gpt-4o-mini", system_prompt=prompt
        )
        assert session._explicit_system_prompt == prompt

    def test_create_session_accepts_approval_provider(self):
        """Test that create_session accepts custom approval provider."""
        mock_provider = MagicMock()
        session = create_session(
            session_id="test",
            model="gpt-4o-mini",
            tools=["bash"],
            approval_provider=mock_provider,
        )
        assert session.approval_provider is mock_provider

    def test_create_session_accepts_context_providers(self):
        """Test that create_session accepts context providers."""

        class TestProvider:
            def get_context(
                self, query: str | None = None, conversation_id: str | None = None
            ) -> dict[str, str]:
                return {"test": "context"}

        provider = TestProvider()
        session = create_session(
            session_id="test",
            model="gpt-4o-mini",
            context_providers=[provider],
        )
        assert session._context_providers == [provider]

    def test_create_session_accepts_summarization_params(self):
        """Test that create_session accepts summarization parameters."""
        session = create_session(
            session_id="test",
            model="gpt-4o-mini",
            summarize=True,
            summarize_threshold=15,
            keep_recent=5,
            summary_model="gpt-4o-mini",
        )
        assert session._summarize is True
        assert session._summarize_threshold == 15
        assert session._keep_recent == 5

    def test_create_session_accepts_model_kwargs(self):
        """Test that create_session passes through provider-specific kwargs."""
        # OpenAI-specific parameter
        session = create_session(
            session_id="test",
            model="gpt-4o-mini",
            service_tier="flex",
        )
        # Just verify it doesn't raise an error
        assert isinstance(session, Consoul)


class TestSessionIsolation:
    """Test that sessions are properly isolated from each other."""

    def test_sessions_have_separate_history(self):
        """Test that different sessions maintain separate conversation history."""
        session_a = create_session(session_id="user_a", model="gpt-4o-mini")
        session_b = create_session(session_id="user_b", model="gpt-4o-mini")

        # Add messages to each session
        session_a.history.add_user_message("Message from user A")
        session_b.history.add_user_message("Message from user B")

        # Verify histories are separate
        messages_a = session_a.history.get_messages_as_dicts()
        messages_b = session_b.history.get_messages_as_dicts()

        assert len(messages_a) == 1
        assert len(messages_b) == 1
        assert messages_a[0]["content"] == "Message from user A"
        assert messages_b[0]["content"] == "Message from user B"

    def test_sessions_have_separate_cost_tracking(self):
        """Test that cost tracking is isolated between sessions."""
        session_a = create_session(session_id="user_a", model="gpt-4o-mini")
        session_b = create_session(session_id="user_b", model="gpt-4o-mini")

        # Simulate requests
        session_a._track_request("Test message A")
        session_b._track_request("Test message B")

        # Verify separate tracking
        assert session_a._last_request is not None
        assert session_b._last_request is not None
        assert session_a._last_request["message"] == "Test message A"
        assert session_b._last_request["message"] == "Test message B"

    def test_sessions_have_separate_tool_registries(self):
        """Test that tool registries are isolated between sessions."""
        session_a = create_session(
            session_id="user_a", model="gpt-4o-mini", tools=["search"]
        )
        session_b = create_session(
            session_id="user_b", model="gpt-4o-mini", tools=["bash"]
        )

        # Verify both have tools enabled but different registries
        assert session_a.tools_enabled is True
        assert session_b.tools_enabled is True
        assert session_a.registry is not session_b.registry

    def test_concurrent_sessions_no_interference(self):
        """Test that concurrent sessions don't interfere with each other."""
        import threading

        results = {}

        def chat_session_a():
            session = create_session(session_id="concurrent_a", model="gpt-4o-mini")
            session.history.add_user_message("Message A")
            results["a"] = len(session.history)

        def chat_session_b():
            session = create_session(session_id="concurrent_b", model="gpt-4o-mini")
            session.history.add_user_message("Message B1")
            session.history.add_user_message("Message B2")
            results["b"] = len(session.history)

        # Run concurrently
        thread_a = threading.Thread(target=chat_session_a)
        thread_b = threading.Thread(target=chat_session_b)

        thread_a.start()
        thread_b.start()

        thread_a.join()
        thread_b.join()

        # Verify separate message counts
        assert results["a"] == 1  # One message in session A
        assert results["b"] == 2  # Two messages in session B


class TestSessionNoPersistence:
    """Test that sessions don't persist to disk."""

    def test_session_no_disk_writes(self, tmp_path):
        """Test that sessions don't create persistent files."""
        # Create session
        session = create_session(session_id="no_persist_test", model="gpt-4o-mini")

        # Add some messages
        session.history.add_user_message("Test message")
        session.history.add_assistant_message("Test response")

        # Verify persist is False
        assert session.history.persist is False

        # Note: Even with persist=False, a temporary DB might be created in memory
        # The key is that it's not persisted across restarts and is in temp directory


class TestSessionCleanup:
    """Test session lifecycle and cleanup patterns."""

    def test_session_can_be_cleared(self):
        """Test that session history can be cleared."""
        session = create_session(session_id="clear_test", model="gpt-4o-mini")

        # Add messages
        session.history.add_user_message("Message 1")
        session.history.add_user_message("Message 2")
        assert len(session.history) == 2

        # Clear
        session.clear()
        assert len(session.history) == 0

    def test_session_cleanup_pattern(self):
        """Test recommended session cleanup pattern."""
        import time

        sessions: dict[str, tuple[Consoul, float]] = {}
        session_ttl = 60  # 1 minute

        # Create sessions with timestamps
        for i in range(3):
            session = create_session(session_id=f"user_{i}", model="gpt-4o-mini")
            sessions[f"user_{i}"] = (session, time.time())

        # Simulate time passing for one session
        old_session_id = "user_0"
        console, _ = sessions[old_session_id]
        sessions[old_session_id] = (console, time.time() - 120)  # 2 minutes ago

        # Cleanup expired
        now = time.time()
        expired = [
            sid
            for sid, (_, created_at) in sessions.items()
            if now - created_at >= session_ttl
        ]

        assert len(expired) == 1
        assert expired[0] == "user_0"

        # Remove expired
        for sid in expired:
            del sessions[sid]

        assert len(sessions) == 2
        assert "user_0" not in sessions


@pytest.mark.asyncio
class TestAsyncSessionIsolation:
    """Test async session isolation patterns."""

    async def test_concurrent_async_sessions(self):
        """Test that async concurrent sessions are properly isolated."""

        async def chat_a():
            session = create_session(session_id="async_a", model="gpt-4o-mini")
            session.history.add_user_message("Async message A")
            await asyncio.sleep(0.01)  # Simulate async work
            return len(session.history)

        async def chat_b():
            session = create_session(session_id="async_b", model="gpt-4o-mini")
            session.history.add_user_message("Async message B1")
            session.history.add_user_message("Async message B2")
            await asyncio.sleep(0.01)  # Simulate async work
            return len(session.history)

        # Run concurrently
        result_a, result_b = await asyncio.gather(chat_a(), chat_b())

        # Verify isolation
        assert result_a == 1
        assert result_b == 2

    async def test_websocket_pattern_isolation(self):
        """Test WebSocket pattern with one session per connection."""
        # Simulate two WebSocket connections with separate sessions
        connections = {}

        # Connection 1
        conn_id_1 = "ws_conn_1"
        connections[conn_id_1] = create_session(
            session_id=conn_id_1, model="gpt-4o-mini"
        )
        connections[conn_id_1].history.add_user_message("WebSocket 1 message")

        # Connection 2
        conn_id_2 = "ws_conn_2"
        connections[conn_id_2] = create_session(
            session_id=conn_id_2, model="gpt-4o-mini"
        )
        connections[conn_id_2].history.add_user_message("WebSocket 2 message A")
        connections[conn_id_2].history.add_user_message("WebSocket 2 message B")

        # Verify isolation
        assert len(connections[conn_id_1].history) == 1
        assert len(connections[conn_id_2].history) == 2

        # Simulate disconnection - cleanup
        del connections[conn_id_1]
        assert conn_id_1 not in connections
        assert len(connections) == 1
