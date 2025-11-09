"""Tests for ConversationHistory persistence integration."""

from __future__ import annotations

from consoul.ai.history import ConversationHistory


class TestPersistenceBasics:
    """Tests for basic persistence functionality."""

    def test_persistence_disabled_by_default(self):
        """Test that persistence is disabled by default."""
        history = ConversationHistory("gpt-4o")

        assert history.persist is False
        assert history._db is None
        assert history.session_id is None

    def test_persistence_enabled_creates_session(self, tmp_path):
        """Test that enabling persistence creates a new session."""
        db_path = tmp_path / "test.db"
        history = ConversationHistory("gpt-4o", persist=True, db_path=db_path)

        assert history.persist is True
        assert history._db is not None
        assert history.session_id is not None
        assert isinstance(history.session_id, str)
        assert len(history.session_id) > 0

    def test_persistence_creates_database_file(self, tmp_path):
        """Test that database file is created."""
        db_path = tmp_path / "test.db"
        ConversationHistory("gpt-4o", persist=True, db_path=db_path)

        assert db_path.exists()


class TestPersistingMessages:
    """Tests for persisting messages to database."""

    def test_user_message_persisted(self, tmp_path):
        """Test that user messages are persisted."""
        db_path = tmp_path / "test.db"
        history = ConversationHistory("gpt-4o", persist=True, db_path=db_path)

        history.add_user_message("Hello!")

        # Verify message is in memory
        assert len(history) == 1

        # Verify message is in database
        messages = history._db.load_conversation(history.session_id)
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello!"

    def test_assistant_message_persisted(self, tmp_path):
        """Test that assistant messages are persisted."""
        db_path = tmp_path / "test.db"
        history = ConversationHistory("gpt-4o", persist=True, db_path=db_path)

        history.add_assistant_message("Hi there!")

        messages = history._db.load_conversation(history.session_id)
        assert len(messages) == 1
        assert messages[0]["role"] == "assistant"
        assert messages[0]["content"] == "Hi there!"

    def test_system_message_persisted(self, tmp_path):
        """Test that system messages are persisted."""
        db_path = tmp_path / "test.db"
        history = ConversationHistory("gpt-4o", persist=True, db_path=db_path)

        history.add_system_message("You are helpful.")

        messages = history._db.load_conversation(history.session_id)
        assert len(messages) == 1
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are helpful."

    def test_multiple_messages_persisted(self, tmp_path):
        """Test that multiple messages are persisted in order."""
        db_path = tmp_path / "test.db"
        history = ConversationHistory("gpt-4o", persist=True, db_path=db_path)

        history.add_system_message("You are helpful.")
        history.add_user_message("Hello!")
        history.add_assistant_message("Hi there!")

        messages = history._db.load_conversation(history.session_id)
        assert len(messages) == 3
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[2]["role"] == "assistant"

    def test_generic_add_message_persisted(self, tmp_path):
        """Test that add_message() persists correctly."""
        db_path = tmp_path / "test.db"
        history = ConversationHistory("gpt-4o", persist=True, db_path=db_path)

        history.add_message("user", "Hello!")
        history.add_message("assistant", "Hi!")

        messages = history._db.load_conversation(history.session_id)
        assert len(messages) == 2

    def test_token_counts_persisted(self, tmp_path):
        """Test that token counts are persisted with messages."""
        db_path = tmp_path / "test.db"
        history = ConversationHistory("gpt-4o", persist=True, db_path=db_path)

        history.add_user_message("Hello!")

        messages = history._db.load_conversation(history.session_id)
        assert messages[0]["tokens"] is not None
        assert messages[0]["tokens"] > 0


class TestResumingSessions:
    """Tests for resuming existing conversation sessions."""

    def test_resume_session_loads_messages(self, tmp_path):
        """Test that resuming a session loads existing messages."""
        db_path = tmp_path / "test.db"

        # Create first session
        history1 = ConversationHistory("gpt-4o", persist=True, db_path=db_path)
        history1.add_system_message("You are helpful.")
        history1.add_user_message("Hello!")
        history1.add_assistant_message("Hi there!")
        session_id = history1.session_id

        # Resume session in new instance
        history2 = ConversationHistory(
            "gpt-4o", persist=True, session_id=session_id, db_path=db_path
        )

        # Verify messages were loaded
        assert len(history2) == 3
        assert history2.messages[0].content == "You are helpful."
        assert history2.messages[1].content == "Hello!"
        assert history2.messages[2].content == "Hi there!"

    def test_resume_session_continues_conversation(self, tmp_path):
        """Test that resumed session can continue the conversation."""
        db_path = tmp_path / "test.db"

        # Create and save initial messages
        history1 = ConversationHistory("gpt-4o", persist=True, db_path=db_path)
        history1.add_user_message("Hello!")
        session_id = history1.session_id

        # Resume and add more messages
        history2 = ConversationHistory(
            "gpt-4o", persist=True, session_id=session_id, db_path=db_path
        )
        history2.add_assistant_message("Hi!")
        history2.add_user_message("How are you?")

        # Verify all messages are persisted
        messages = history2._db.load_conversation(session_id)
        assert len(messages) == 3
        assert messages[0]["content"] == "Hello!"
        assert messages[1]["content"] == "Hi!"
        assert messages[2]["content"] == "How are you?"

    def test_resume_nonexistent_session_falls_back(self, tmp_path):
        """Test that resuming non-existent session falls back gracefully."""
        db_path = tmp_path / "test.db"

        # Should not raise, but fall back to in-memory mode
        history = ConversationHistory(
            "gpt-4o",
            persist=True,
            session_id="nonexistent-session-123",
            db_path=db_path,
        )

        # Verify fallback occurred
        assert history.persist is False
        assert history._db is None

        # Still works in-memory
        history.add_user_message("Test")
        assert len(history) == 1

    def test_resume_empty_session(self, tmp_path):
        """Test resuming a session with no messages."""
        db_path = tmp_path / "test.db"

        # Create session without adding messages
        history1 = ConversationHistory("gpt-4o", persist=True, db_path=db_path)
        session_id = history1.session_id

        # Resume session
        history2 = ConversationHistory(
            "gpt-4o", persist=True, session_id=session_id, db_path=db_path
        )

        assert len(history2) == 0


class TestPersistenceIsolation:
    """Tests for session isolation and independence."""

    def test_different_sessions_isolated(self, tmp_path):
        """Test that different sessions don't interfere."""
        db_path = tmp_path / "test.db"

        # Create two sessions
        history1 = ConversationHistory("gpt-4o", persist=True, db_path=db_path)
        history1.add_user_message("Session 1")

        history2 = ConversationHistory("gpt-4o", persist=True, db_path=db_path)
        history2.add_user_message("Session 2")

        # Verify sessions are independent
        assert history1.session_id != history2.session_id

        # Verify messages are separate
        messages1 = history1._db.load_conversation(history1.session_id)
        messages2 = history2._db.load_conversation(history2.session_id)

        assert len(messages1) == 1
        assert len(messages2) == 1
        assert messages1[0]["content"] == "Session 1"
        assert messages2[0]["content"] == "Session 2"

    def test_persistence_doesnt_affect_inmemory(self, tmp_path):
        """Test that persistent sessions don't affect in-memory sessions."""
        db_path = tmp_path / "test.db"

        # Create persistent session
        persistent = ConversationHistory("gpt-4o", persist=True, db_path=db_path)
        persistent.add_user_message("Persistent")

        # Create in-memory session
        inmemory = ConversationHistory("gpt-4o", persist=False)
        inmemory.add_user_message("In-memory")

        # Verify both work independently
        assert len(persistent) == 1
        assert len(inmemory) == 1
        assert persistent.session_id is not None
        assert inmemory.session_id is None


class TestPersistenceEdgeCases:
    """Tests for edge cases and error handling."""

    def test_persistence_with_special_characters(self, tmp_path):
        """Test persisting messages with special characters."""
        db_path = tmp_path / "test.db"
        history = ConversationHistory("gpt-4o", persist=True, db_path=db_path)

        special_content = "Hello! 你好 مرحبا 🎉\n\nNew line\t\ttab"
        history.add_user_message(special_content)

        # Resume and verify
        history2 = ConversationHistory(
            "gpt-4o", persist=True, session_id=history.session_id, db_path=db_path
        )

        assert history2.messages[0].content == special_content

    def test_persistence_with_long_content(self, tmp_path):
        """Test persisting very long messages."""
        db_path = tmp_path / "test.db"
        history = ConversationHistory("gpt-4o", persist=True, db_path=db_path)

        long_content = "A" * 10000
        history.add_user_message(long_content)

        # Resume and verify
        history2 = ConversationHistory(
            "gpt-4o", persist=True, session_id=history.session_id, db_path=db_path
        )

        assert history2.messages[0].content == long_content

    def test_persistence_with_custom_db_path(self, tmp_path):
        """Test using custom database path."""
        custom_path = tmp_path / "custom_dir" / "my_history.db"

        history = ConversationHistory("gpt-4o", persist=True, db_path=custom_path)
        history.add_user_message("Test")

        assert custom_path.exists()
        assert len(history) == 1

    def test_persistence_fallback_on_db_error(self, tmp_path, monkeypatch):
        """Test graceful fallback to in-memory mode on database errors."""
        # Use invalid path to trigger error
        invalid_path = "/dev/null/invalid/path.db"

        # Should not raise, but fall back to in-memory
        history = ConversationHistory("gpt-4o", persist=True, db_path=invalid_path)

        # Verify fallback occurred
        assert history.persist is False  # Disabled after error
        assert history._db is None

        # But normal operations should still work
        history.add_user_message("Hello!")
        assert len(history) == 1

    def test_persistence_failure_doesnt_crash_add(self, tmp_path, monkeypatch):
        """Test that persistence failures don't crash message operations."""
        db_path = tmp_path / "test.db"
        history = ConversationHistory("gpt-4o", persist=True, db_path=db_path)

        # Break the database connection
        history._db = None

        # Should not crash, just log warning
        history.add_user_message("Test")

        # Message should still be in memory
        assert len(history) == 1


class TestPersistenceIntegrationWithTrimming:
    """Tests for persistence combined with message trimming."""

    def test_resumed_session_can_be_trimmed(self, tmp_path):
        """Test that resumed sessions work with message trimming."""
        db_path = tmp_path / "test.db"

        # Create session with many long messages to trigger trimming
        history1 = ConversationHistory(
            "gpt-4o", max_tokens=5000, persist=True, db_path=db_path
        )
        # Use longer messages to consume more tokens
        long_message = "This is a longer message " * 20  # ~100+ tokens each
        for i in range(10):
            history1.add_user_message(f"{long_message} {i}")
            history1.add_assistant_message(f"{long_message} response {i}")
        session_id = history1.session_id

        # Resume and trim with smaller limit
        history2 = ConversationHistory(
            "gpt-4o",
            max_tokens=5000,
            persist=True,
            session_id=session_id,
            db_path=db_path,
        )

        # With 20 long messages, reserve most tokens to force trimming
        trimmed = history2.get_trimmed_messages(reserve_tokens=4500)

        # Should have trimmed some messages
        # (20 messages of ~100 tokens each = ~2000 tokens, but only 500 available)
        assert len(trimmed) < len(history2.messages)
        # But should have kept at least 2 messages (to maintain conversation)
        assert len(trimmed) >= 2

    def test_persistence_preserves_all_messages_for_later_access(self, tmp_path):
        """Test that all messages are preserved in DB even if trimmed in memory."""
        db_path = tmp_path / "test.db"

        history = ConversationHistory(
            "gpt-4o", max_tokens=500, persist=True, db_path=db_path
        )

        # Add many messages
        for i in range(20):
            history.add_user_message(f"Message {i}")

        # Get trimmed view
        trimmed = history.get_trimmed_messages(reserve_tokens=400)

        # Trimmed view should be smaller
        assert len(trimmed) < 20

        # But all messages should still be in database
        db_messages = history._db.load_conversation(history.session_id)
        assert len(db_messages) == 20
