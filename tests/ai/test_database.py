"""Tests for SQLite conversation persistence."""

from __future__ import annotations

import sqlite3

import pytest

from consoul.ai.database import (
    ConversationDatabase,
    ConversationNotFoundError,
    DatabaseError,
)


class TestDatabaseInitialization:
    """Tests for database initialization and schema creation."""

    def test_create_database_default_path(self, tmp_path, monkeypatch):
        """Test database creation with default path."""
        # Mock home directory
        monkeypatch.setenv("HOME", str(tmp_path))

        db = ConversationDatabase()

        # Check database file was created
        expected_path = tmp_path / ".consoul" / "history.db"
        assert db.db_path == expected_path
        assert db.db_path.exists()

    def test_create_database_custom_path(self, tmp_path):
        """Test database creation with custom path."""
        db_path = tmp_path / "custom.db"
        db = ConversationDatabase(db_path)

        assert db.db_path == db_path
        assert db.db_path.exists()

    def test_schema_version_set(self, tmp_path):
        """Test that schema version is set correctly."""
        db_path = tmp_path / "test.db"
        ConversationDatabase(db_path)

        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT version FROM schema_version")
            version = cursor.fetchone()[0]
            assert version == ConversationDatabase.SCHEMA_VERSION

    def test_tables_created(self, tmp_path):
        """Test that all required tables are created."""
        db_path = tmp_path / "test.db"
        ConversationDatabase(db_path)

        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = [row[0] for row in cursor.fetchall()]

        assert "schema_version" in tables
        assert "conversations" in tables
        assert "messages" in tables

    def test_indexes_created(self, tmp_path):
        """Test that indexes are created for performance."""
        db_path = tmp_path / "test.db"
        ConversationDatabase(db_path)

        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'"
            )
            indexes = [row[0] for row in cursor.fetchall()]

        assert "idx_messages_conversation" in indexes
        assert "idx_conversations_session" in indexes
        assert "idx_conversations_updated" in indexes

    def test_wal_mode_enabled(self, tmp_path):
        """Test that WAL mode is enabled for better concurrent access."""
        db_path = tmp_path / "test.db"
        ConversationDatabase(db_path)

        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("PRAGMA journal_mode")
            mode = cursor.fetchone()[0]

        assert mode.lower() == "wal"


class TestConversationCreation:
    """Tests for creating conversations."""

    def test_create_conversation_auto_id(self, tmp_path):
        """Test creating conversation with auto-generated ID."""
        db = ConversationDatabase(tmp_path / "test.db")

        session_id = db.create_conversation("gpt-4o")

        assert isinstance(session_id, str)
        assert len(session_id) > 0

    def test_create_conversation_custom_id(self, tmp_path):
        """Test creating conversation with custom ID."""
        db = ConversationDatabase(tmp_path / "test.db")

        custom_id = "my-custom-session-123"
        session_id = db.create_conversation("gpt-4o", session_id=custom_id)

        assert session_id == custom_id

    def test_create_conversation_with_metadata(self, tmp_path):
        """Test creating conversation with metadata."""
        db = ConversationDatabase(tmp_path / "test.db")

        metadata = {"user": "alice", "tags": ["work", "important"]}
        session_id = db.create_conversation("gpt-4o", metadata=metadata)

        # Verify metadata was stored
        meta = db.get_conversation_metadata(session_id)
        assert meta["metadata"] == metadata

    def test_create_conversation_duplicate_id_fails(self, tmp_path):
        """Test that duplicate session IDs are rejected."""
        db = ConversationDatabase(tmp_path / "test.db")

        session_id = "duplicate-test"
        db.create_conversation("gpt-4o", session_id=session_id)

        with pytest.raises(DatabaseError, match="already exists"):
            db.create_conversation("gpt-4o", session_id=session_id)

    def test_create_conversation_stores_timestamp(self, tmp_path):
        """Test that created_at and updated_at are set."""
        db = ConversationDatabase(tmp_path / "test.db")

        session_id = db.create_conversation("gpt-4o")
        meta = db.get_conversation_metadata(session_id)

        assert meta["created_at"] is not None
        assert meta["updated_at"] is not None
        assert meta["created_at"] == meta["updated_at"]  # Initially same


class TestMessageOperations:
    """Tests for saving and loading messages."""

    def test_save_message(self, tmp_path):
        """Test saving a message to conversation."""
        db = ConversationDatabase(tmp_path / "test.db")
        session_id = db.create_conversation("gpt-4o")

        db.save_message(session_id, "user", "Hello!", 5)

        messages = db.load_conversation(session_id)
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello!"
        assert messages[0]["tokens"] == 5

    def test_save_message_without_tokens(self, tmp_path):
        """Test saving message without token count."""
        db = ConversationDatabase(tmp_path / "test.db")
        session_id = db.create_conversation("gpt-4o")

        db.save_message(session_id, "user", "Hello!")

        messages = db.load_conversation(session_id)
        assert len(messages) == 1
        assert messages[0]["tokens"] is None

    def test_save_multiple_messages(self, tmp_path):
        """Test saving multiple messages in order."""
        db = ConversationDatabase(tmp_path / "test.db")
        session_id = db.create_conversation("gpt-4o")

        db.save_message(session_id, "system", "You are helpful", 4)
        db.save_message(session_id, "user", "Hello!", 2)
        db.save_message(session_id, "assistant", "Hi there!", 3)

        messages = db.load_conversation(session_id)
        assert len(messages) == 3
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[2]["role"] == "assistant"

    def test_save_message_updates_conversation_timestamp(self, tmp_path):
        """Test that saving message updates conversation updated_at."""
        db = ConversationDatabase(tmp_path / "test.db")
        session_id = db.create_conversation("gpt-4o")

        meta_before = db.get_conversation_metadata(session_id)
        db.save_message(session_id, "user", "Hello!", 5)
        meta_after = db.get_conversation_metadata(session_id)

        assert meta_after["updated_at"] >= meta_before["updated_at"]

    def test_save_message_nonexistent_conversation_fails(self, tmp_path):
        """Test that saving to non-existent conversation fails."""
        db = ConversationDatabase(tmp_path / "test.db")

        with pytest.raises(ConversationNotFoundError):
            db.save_message("nonexistent-session", "user", "Hello!", 5)

    def test_save_message_with_special_characters(self, tmp_path):
        """Test saving messages with special characters."""
        db = ConversationDatabase(tmp_path / "test.db")
        session_id = db.create_conversation("gpt-4o")

        special_content = "Hello! 你好 مرحبا 🎉\n\nNew line\t\ttab"
        db.save_message(session_id, "user", special_content, 10)

        messages = db.load_conversation(session_id)
        assert messages[0]["content"] == special_content

    def test_save_message_with_long_content(self, tmp_path):
        """Test saving very long message content."""
        db = ConversationDatabase(tmp_path / "test.db")
        session_id = db.create_conversation("gpt-4o")

        long_content = "A" * 100000  # 100K characters
        db.save_message(session_id, "user", long_content, 25000)

        messages = db.load_conversation(session_id)
        assert messages[0]["content"] == long_content


class TestLoadingConversations:
    """Tests for loading conversation data."""

    def test_load_conversation_empty(self, tmp_path):
        """Test loading conversation with no messages."""
        db = ConversationDatabase(tmp_path / "test.db")
        session_id = db.create_conversation("gpt-4o")

        messages = db.load_conversation(session_id)

        assert messages == []

    def test_load_conversation_nonexistent_fails(self, tmp_path):
        """Test loading non-existent conversation fails."""
        db = ConversationDatabase(tmp_path / "test.db")

        with pytest.raises(ConversationNotFoundError):
            db.load_conversation("nonexistent-session")

    def test_load_conversation_preserves_order(self, tmp_path):
        """Test that messages are loaded in correct order."""
        db = ConversationDatabase(tmp_path / "test.db")
        session_id = db.create_conversation("gpt-4o")

        messages_to_save = [
            ("user", "Message 1"),
            ("assistant", "Message 2"),
            ("user", "Message 3"),
        ]
        for role, content in messages_to_save:
            db.save_message(session_id, role, content, 5)

        messages = db.load_conversation(session_id)
        assert len(messages) == 3
        for i, (role, content) in enumerate(messages_to_save):
            assert messages[i]["role"] == role
            assert messages[i]["content"] == content


class TestListingConversations:
    """Tests for listing conversations."""

    def test_list_conversations_empty(self, tmp_path):
        """Test listing when no conversations exist."""
        db = ConversationDatabase(tmp_path / "test.db")

        conversations = db.list_conversations()

        assert conversations == []

    def test_list_conversations_single(self, tmp_path):
        """Test listing single conversation."""
        db = ConversationDatabase(tmp_path / "test.db")
        session_id = db.create_conversation("gpt-4o")

        conversations = db.list_conversations()

        assert len(conversations) == 1
        assert conversations[0]["session_id"] == session_id
        assert conversations[0]["model"] == "gpt-4o"
        assert conversations[0]["message_count"] == 0

    def test_list_conversations_with_messages(self, tmp_path):
        """Test that message count is included."""
        db = ConversationDatabase(tmp_path / "test.db")
        session_id = db.create_conversation("gpt-4o")
        db.save_message(session_id, "user", "Hello!", 5)
        db.save_message(session_id, "assistant", "Hi!", 3)

        conversations = db.list_conversations()

        assert len(conversations) == 1
        assert conversations[0]["message_count"] == 2

    def test_list_conversations_ordered_by_updated(self, tmp_path):
        """Test that conversations are ordered by updated_at DESC."""
        db = ConversationDatabase(tmp_path / "test.db")

        session1 = db.create_conversation("gpt-4o")
        session2 = db.create_conversation("claude-3-5-sonnet")

        # Update session1 (should move it to top)
        db.save_message(session1, "user", "Hello!", 5)

        conversations = db.list_conversations()

        assert conversations[0]["session_id"] == session1
        assert conversations[1]["session_id"] == session2

    def test_list_conversations_limit(self, tmp_path):
        """Test limiting number of conversations returned."""
        db = ConversationDatabase(tmp_path / "test.db")

        # Create 5 conversations
        for i in range(5):
            db.create_conversation(f"model-{i}")

        conversations = db.list_conversations(limit=3)

        assert len(conversations) == 3

    def test_list_conversations_offset(self, tmp_path):
        """Test offset pagination."""
        db = ConversationDatabase(tmp_path / "test.db")

        # Create 5 conversations
        sessions = []
        for i in range(5):
            sessions.append(db.create_conversation(f"model-{i}"))

        # Get first 2
        page1 = db.list_conversations(limit=2, offset=0)
        # Get next 2
        page2 = db.list_conversations(limit=2, offset=2)

        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0]["session_id"] != page2[0]["session_id"]


class TestConversationMetadata:
    """Tests for getting conversation metadata."""

    def test_get_conversation_metadata(self, tmp_path):
        """Test getting metadata for conversation."""
        db = ConversationDatabase(tmp_path / "test.db")
        metadata = {"user": "alice"}
        session_id = db.create_conversation("gpt-4o", metadata=metadata)

        meta = db.get_conversation_metadata(session_id)

        assert meta["session_id"] == session_id
        assert meta["model"] == "gpt-4o"
        assert meta["metadata"] == metadata
        assert "created_at" in meta
        assert "updated_at" in meta
        assert "message_count" in meta

    def test_get_conversation_metadata_nonexistent_fails(self, tmp_path):
        """Test getting metadata for non-existent conversation fails."""
        db = ConversationDatabase(tmp_path / "test.db")

        with pytest.raises(ConversationNotFoundError):
            db.get_conversation_metadata("nonexistent-session")


class TestDeletingConversations:
    """Tests for deleting conversations."""

    def test_delete_conversation(self, tmp_path):
        """Test deleting a conversation."""
        db = ConversationDatabase(tmp_path / "test.db")
        session_id = db.create_conversation("gpt-4o")
        db.save_message(session_id, "user", "Hello!", 5)

        db.delete_conversation(session_id)

        # Verify conversation is gone
        with pytest.raises(ConversationNotFoundError):
            db.load_conversation(session_id)

        # Verify messages are also deleted (CASCADE)
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE conversation_id = ?",
                (session_id,),
            )
            count = cursor.fetchone()[0]
            assert count == 0

    def test_delete_conversation_nonexistent_fails(self, tmp_path):
        """Test deleting non-existent conversation fails."""
        db = ConversationDatabase(tmp_path / "test.db")

        with pytest.raises(ConversationNotFoundError):
            db.delete_conversation("nonexistent-session")

    def test_clear_all_conversations(self, tmp_path):
        """Test clearing all conversations."""
        db = ConversationDatabase(tmp_path / "test.db")

        # Create multiple conversations
        for i in range(5):
            session_id = db.create_conversation(f"model-{i}")
            db.save_message(session_id, "user", f"Message {i}", 5)

        count = db.clear_all_conversations()

        assert count == 5
        assert db.list_conversations() == []

        # Verify all messages are also deleted
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM messages")
            message_count = cursor.fetchone()[0]
            assert message_count == 0


class TestDatabaseStats:
    """Tests for database statistics."""

    def test_get_stats_empty_database(self, tmp_path):
        """Test stats for empty database."""
        db = ConversationDatabase(tmp_path / "test.db")

        stats = db.get_stats()

        assert stats["total_conversations"] == 0
        assert stats["total_messages"] == 0
        assert stats["db_size_bytes"] > 0  # File exists
        assert stats["oldest_conversation"] is None
        assert stats["newest_conversation"] is None

    def test_get_stats_with_data(self, tmp_path):
        """Test stats with conversations and messages."""
        db = ConversationDatabase(tmp_path / "test.db")

        # Create 3 conversations with messages
        for i in range(3):
            session_id = db.create_conversation(f"model-{i}")
            for j in range(2):
                db.save_message(session_id, "user", f"Message {j}", 5)

        stats = db.get_stats()

        assert stats["total_conversations"] == 3
        assert stats["total_messages"] == 6  # 3 conversations * 2 messages
        assert stats["db_size_bytes"] > 0
        assert stats["oldest_conversation"] is not None
        assert stats["newest_conversation"] is not None


class TestContextManager:
    """Tests for context manager support."""

    def test_context_manager(self, tmp_path):
        """Test using database as context manager."""
        db_path = tmp_path / "test.db"

        with ConversationDatabase(db_path) as db:
            session_id = db.create_conversation("gpt-4o")
            db.save_message(session_id, "user", "Hello!", 5)

        # Verify data persisted after context exit
        db2 = ConversationDatabase(db_path)
        messages = db2.load_conversation(session_id)
        assert len(messages) == 1


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_invalid_db_path_creates_parent_dirs(self, tmp_path):
        """Test that parent directories are created if needed."""
        db_path = tmp_path / "deep" / "nested" / "path" / "test.db"

        ConversationDatabase(db_path)

        assert db_path.exists()
        assert db_path.parent.exists()

    def test_concurrent_writes(self, tmp_path):
        """Test that WAL mode allows concurrent writes."""
        db_path = tmp_path / "test.db"
        db1 = ConversationDatabase(db_path)
        db2 = ConversationDatabase(db_path)

        # Both can write to different conversations
        session1 = db1.create_conversation("gpt-4o")
        session2 = db2.create_conversation("claude-3-5-sonnet")

        db1.save_message(session1, "user", "Hello from db1", 5)
        db2.save_message(session2, "user", "Hello from db2", 5)

        # Both messages should be saved
        assert len(db1.load_conversation(session1)) == 1
        assert len(db2.load_conversation(session2)) == 1
