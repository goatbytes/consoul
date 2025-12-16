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


class TestFullTextSearch:
    """Tests for FTS5 full-text search functionality."""

    def test_search_basic_query(self, tmp_path):
        """Test basic single-term search."""
        db = ConversationDatabase(tmp_path / "test.db")
        session_id = db.create_conversation("gpt-4o")

        db.save_message(session_id, "user", "I found an authentication bug", 10)
        db.save_message(session_id, "assistant", "Let me help fix that bug", 10)
        db.save_message(session_id, "user", "The feature works great now", 10)

        results = db.search_messages("bug")

        assert len(results) == 2
        assert all("bug" in r["content"].lower() for r in results)

    def test_search_phrase_query(self, tmp_path):
        """Test phrase search with exact matching."""
        db = ConversationDatabase(tmp_path / "test.db")
        session_id = db.create_conversation("gpt-4o")

        db.save_message(session_id, "user", "token limit exceeded", 5)
        db.save_message(session_id, "user", "token limits are fine", 5)
        db.save_message(session_id, "user", "limit exceeded again", 5)

        # Exact phrase should match only first message
        results = db.search_messages('"token limit exceeded"')

        assert len(results) == 1
        assert results[0]["content"] == "token limit exceeded"

    def test_search_prefix_matching(self, tmp_path):
        """Test prefix search with wildcard."""
        db = ConversationDatabase(tmp_path / "test.db")
        session_id = db.create_conversation("gpt-4o")

        db.save_message(session_id, "user", "authentication failed", 5)
        db.save_message(session_id, "user", "authorize user access", 5)
        db.save_message(session_id, "user", "testing features", 5)

        results = db.search_messages("auth*")

        assert len(results) == 2
        contents = [r["content"] for r in results]
        assert any("authentication" in c for c in contents)
        assert any("authorize" in c for c in contents)

    def test_search_multiple_terms(self, tmp_path):
        """Test multi-term search (implicit AND)."""
        db = ConversationDatabase(tmp_path / "test.db")
        session_id = db.create_conversation("gpt-4o")

        db.save_message(session_id, "user", "API error occurred", 5)
        db.save_message(session_id, "user", "fixing the API", 5)
        db.save_message(session_id, "user", "error in database", 5)

        results = db.search_messages("API error")

        # Should match messages with both terms
        assert len(results) >= 1
        assert results[0]["content"] == "API error occurred"

    def test_search_with_model_filter(self, tmp_path):
        """Test filtering search results by model."""
        db = ConversationDatabase(tmp_path / "test.db")

        session_gpt = db.create_conversation("gpt-4o")
        session_claude = db.create_conversation("claude-3-5-sonnet")

        db.save_message(session_gpt, "user", "testing gpt model", 5)
        db.save_message(session_claude, "user", "testing claude model", 5)

        # Search with model filter
        results = db.search_messages("testing", model_filter="gpt-4o")

        assert len(results) == 1
        assert results[0]["model"] == "gpt-4o"

    def test_search_with_date_filter(self, tmp_path):
        """Test filtering search results by date."""
        db = ConversationDatabase(tmp_path / "test.db")

        session1 = db.create_conversation("gpt-4o")
        db.save_message(session1, "user", "message one", 5)

        # Create another conversation (will have later timestamp)
        session2 = db.create_conversation("gpt-4o")
        db.save_message(session2, "user", "message two", 5)

        # Get conversation metadata to extract dates
        import sqlite3

        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.execute(
                "SELECT created_at FROM conversations WHERE session_id = ?",
                (session1,),
            )
            date1 = cursor.fetchone()[0]

        # Search with date filter
        results = db.search_messages("message", after_date=date1)

        assert len(results) == 2  # Both after date1

    def test_search_with_limit(self, tmp_path):
        """Test limiting search results."""
        db = ConversationDatabase(tmp_path / "test.db")
        session_id = db.create_conversation("gpt-4o")

        for i in range(10):
            db.save_message(session_id, "user", f"test message {i}", 5)

        results = db.search_messages("test", limit=3)

        assert len(results) == 3

    def test_search_ranking(self, tmp_path):
        """Test BM25 relevance ranking."""
        db = ConversationDatabase(tmp_path / "test.db")
        session_id = db.create_conversation("gpt-4o")

        # Message with term repeated should rank higher
        db.save_message(session_id, "user", "bug bug bug found", 5)
        db.save_message(session_id, "user", "small bug here", 5)

        results = db.search_messages("bug")

        # First result should have higher (more negative) rank due to more matches
        assert len(results) == 2
        assert results[0]["rank"] < results[1]["rank"]

    def test_search_snippet_generation(self, tmp_path):
        """Test that search generates highlighted snippets."""
        db = ConversationDatabase(tmp_path / "test.db")
        session_id = db.create_conversation("gpt-4o")

        db.save_message(
            session_id,
            "user",
            "I found a critical authentication bug in the login system that needs fixing",
            20,
        )

        results = db.search_messages("authentication")

        assert len(results) == 1
        assert "<mark>" in results[0]["snippet"]
        assert "</mark>" in results[0]["snippet"]
        assert "authentication" in results[0]["snippet"].lower()

    def test_search_empty_results(self, tmp_path):
        """Test search with no matching results."""
        db = ConversationDatabase(tmp_path / "test.db")
        session_id = db.create_conversation("gpt-4o")

        db.save_message(session_id, "user", "hello world", 5)

        results = db.search_messages("nonexistent")

        assert len(results) == 0

    def test_search_unicode_content(self, tmp_path):
        """Test search with Unicode characters."""
        db = ConversationDatabase(tmp_path / "test.db")
        session_id = db.create_conversation("gpt-4o")

        db.save_message(session_id, "user", "Hello 你好 Привет مرحبا", 10)
        db.save_message(session_id, "user", "testing unicode 你好", 10)

        results = db.search_messages("你好")

        assert len(results) == 2

    def test_search_special_characters(self, tmp_path):
        """Test search with special characters."""
        db = ConversationDatabase(tmp_path / "test.db")
        session_id = db.create_conversation("gpt-4o")

        db.save_message(session_id, "user", "Error: file not found!", 5)
        db.save_message(session_id, "user", "Warning: timeout occurred", 5)

        results = db.search_messages("Error")

        assert len(results) == 1
        assert "Error" in results[0]["content"]

    def test_get_message_context_basic(self, tmp_path):
        """Test getting message context."""
        db = ConversationDatabase(tmp_path / "test.db")
        session_id = db.create_conversation("gpt-4o")

        msg_ids = []
        for i in range(5):
            msg_id = db.save_message(session_id, "user", f"Message {i}", 5)
            msg_ids.append(msg_id)

        # Get context around middle message
        context = db.get_message_context(msg_ids[2], context_size=1)

        # Should get 3 messages: msg[1], msg[2], msg[3]
        assert len(context) == 3
        assert context[1]["id"] == msg_ids[2]
        assert "Message 1" in context[0]["content"]
        assert "Message 3" in context[2]["content"]

    def test_get_message_context_edge_cases(self, tmp_path):
        """Test message context at conversation boundaries."""
        db = ConversationDatabase(tmp_path / "test.db")
        session_id = db.create_conversation("gpt-4o")

        msg_ids = []
        for i in range(3):
            msg_id = db.save_message(session_id, "user", f"Message {i}", 5)
            msg_ids.append(msg_id)

        # First message: should only get messages from start
        context = db.get_message_context(msg_ids[0], context_size=2)
        assert len(context) <= 3  # Max 3 messages available

        # Last message: should only get messages to end
        context = db.get_message_context(msg_ids[-1], context_size=2)
        assert len(context) <= 3

    def test_get_message_context_invalid_id(self, tmp_path):
        """Test getting context for non-existent message."""
        db = ConversationDatabase(tmp_path / "test.db")

        context = db.get_message_context(99999, context_size=2)

        assert len(context) == 0

    def test_get_message_context_with_non_contiguous_ids(self, tmp_path):
        """Test context retrieval when IDs are not contiguous (interleaved conversations)."""
        db = ConversationDatabase(tmp_path / "test.db")

        # Create two conversations and interleave messages to create non-contiguous IDs
        session1 = db.create_conversation("gpt-4o")
        session2 = db.create_conversation("claude-3-5-sonnet")

        # Interleave messages from both conversations to create non-contiguous IDs
        _ = db.save_message(session1, "user", "Session1 Message1", 5)
        _ = db.save_message(session2, "user", "Session2 Message1", 5)
        msg1_2 = db.save_message(session1, "user", "Session1 Message2", 5)
        _ = db.save_message(session2, "user", "Session2 Message2", 5)
        msg1_3 = db.save_message(session1, "user", "Session1 Message3", 5)
        _ = db.save_message(session2, "user", "Session2 Message3", 5)
        msg1_4 = db.save_message(session1, "user", "Session1 Message4", 5)
        _ = db.save_message(session1, "user", "Session1 Message5", 5)

        # Session1 has IDs: msg1_1, msg1_2, msg1_3, msg1_4, msg1_5 (non-contiguous!)
        # Session2 has IDs: msg2_1, msg2_2, msg2_3 (non-contiguous!)

        # Get context around msg1_3 (middle message in session1) with context_size=1
        context = db.get_message_context(msg1_3, context_size=1)

        # Should get exactly 3 messages: msg1_2, msg1_3, msg1_4
        assert len(context) == 3
        assert context[0]["id"] == msg1_2
        assert context[1]["id"] == msg1_3
        assert context[2]["id"] == msg1_4

        # Verify content is correct (no messages from session2)
        contents = [msg["content"] for msg in context]
        assert "Session1 Message2" in contents
        assert "Session1 Message3" in contents
        assert "Session1 Message4" in contents
        assert all("Session2" not in c for c in contents)

    def test_fts_triggers_on_update(self, tmp_path):
        """Test that FTS index updates when messages are updated."""
        db = ConversationDatabase(tmp_path / "test.db")
        session_id = db.create_conversation("gpt-4o")

        msg_id = db.save_message(session_id, "user", "original text", 5)

        # Update message content directly in database
        import sqlite3

        with sqlite3.connect(db.db_path) as conn:
            conn.execute(
                "UPDATE messages SET content = ? WHERE id = ?",
                ("updated text", msg_id),
            )

        # Search should find updated content
        results = db.search_messages("updated")
        assert len(results) == 1

        # Search should not find old content
        results = db.search_messages("original")
        assert len(results) == 0

    def test_fts_triggers_on_delete(self, tmp_path):
        """Test that FTS index updates when messages are deleted."""
        db = ConversationDatabase(tmp_path / "test.db")
        session_id = db.create_conversation("gpt-4o")

        db.save_message(session_id, "user", "searchable text", 5)

        # Delete conversation (CASCADE should delete messages and FTS entries)
        db.delete_conversation(session_id)

        # Search should return no results
        results = db.search_messages("searchable")
        assert len(results) == 0

    def test_search_across_multiple_conversations(self, tmp_path):
        """Test searching across different conversations."""
        db = ConversationDatabase(tmp_path / "test.db")

        session1 = db.create_conversation("gpt-4o")
        session2 = db.create_conversation("claude-3-5-sonnet")
        session3 = db.create_conversation("gpt-4o")

        db.save_message(session1, "user", "authentication issue", 5)
        db.save_message(session2, "user", "authentication problem", 5)
        db.save_message(session3, "user", "different topic", 5)

        results = db.search_messages("authentication")

        assert len(results) == 2
        session_ids = {r["session_id"] for r in results}
        assert session1 in session_ids
        assert session2 in session_ids


class TestRetentionCleanup:
    """Tests for conversation retention and cleanup functionality."""

    def test_delete_conversations_older_than(self, tmp_path):
        """Test deleting conversations older than specified days."""
        import sqlite3
        from datetime import datetime, timedelta, timezone

        db = ConversationDatabase(tmp_path / "test.db")

        # Create conversations with different ages
        session_recent = db.create_conversation("gpt-4o")
        session_old = db.create_conversation("gpt-4o")

        # Add messages to both
        db.save_message(session_recent, "user", "Recent message", 5)
        db.save_message(session_old, "user", "Old message", 5)

        # Manually update the old conversation's timestamp to 31 days ago
        # (must be done after save_message since it updates updated_at)
        old_timestamp = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
        with sqlite3.connect(db.db_path) as conn:
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE session_id = ?",
                (old_timestamp, session_old),
            )

        # Delete conversations older than 30 days
        deleted_count = db.delete_conversations_older_than(30)

        assert deleted_count == 1

        # Recent conversation should still exist
        conversations = db.list_conversations()
        assert len(conversations) == 1
        assert conversations[0]["session_id"] == session_recent

    def test_delete_conversations_older_than_no_matches(self, tmp_path):
        """Test deletion when no conversations match the age criteria."""
        db = ConversationDatabase(tmp_path / "test.db")

        # Create recent conversations
        db.create_conversation("gpt-4o")
        db.create_conversation("claude-3-5-sonnet")

        # Try to delete conversations older than 30 days (none exist)
        deleted_count = db.delete_conversations_older_than(30)

        assert deleted_count == 0

        # Both conversations should still exist
        conversations = db.list_conversations()
        assert len(conversations) == 2

    def test_delete_conversations_older_than_cascades(self, tmp_path):
        """Test that deleting old conversations also deletes their messages."""
        import sqlite3
        from datetime import datetime, timedelta, timezone

        db = ConversationDatabase(tmp_path / "test.db")

        # Create old conversation
        session_old = db.create_conversation("gpt-4o")
        db.save_message(session_old, "user", "Old message 1", 5)
        db.save_message(session_old, "assistant", "Old message 2", 5)

        # Make it old (must be done after save_message since it updates updated_at)
        old_timestamp = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
        with sqlite3.connect(db.db_path) as conn:
            conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE session_id = ?",
                (old_timestamp, session_old),
            )

        # Delete old conversations
        deleted_count = db.delete_conversations_older_than(30)
        assert deleted_count == 1

        # Messages should also be deleted (CASCADE)
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM messages WHERE conversation_id = ?",
                (session_old,),
            )
            message_count = cursor.fetchone()[0]
            assert message_count == 0
