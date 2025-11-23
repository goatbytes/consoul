"""Tests for conversation branching functionality in ConversationDatabase."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from consoul.ai.database import (
    ConversationDatabase,
    ConversationNotFoundError,
)


class TestConversationBranching:
    """Test conversation branching functionality."""

    @pytest.fixture
    def db(self) -> ConversationDatabase:
        """Create a temporary test database."""
        # Use temporary file for testing
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        db = ConversationDatabase(db_path)
        yield db

        # Cleanup
        db_path.unlink(missing_ok=True)

    def test_branch_basic(self, db: ConversationDatabase) -> None:
        """Test basic conversation branching."""
        # Create conversation with messages
        session_id = db.create_conversation("gpt-4o")
        db.save_message(session_id, "user", "Hello", 5)
        msg2_id = db.save_message(session_id, "assistant", "Hi there", 6)
        db.save_message(session_id, "user", "How are you?", 7)

        # Branch at message 2 (assistant response)
        new_session_id = db.branch_conversation(session_id, msg2_id)

        # Verify new conversation was created
        assert new_session_id != session_id
        assert isinstance(new_session_id, str)

        # Verify new conversation has correct messages
        new_messages = db.load_conversation(new_session_id)
        assert len(new_messages) == 2  # msg1 and msg2 only
        assert new_messages[0]["content"] == "Hello"
        assert new_messages[1]["content"] == "Hi there"

        # Verify original conversation unchanged
        original_messages = db.load_conversation(session_id)
        assert len(original_messages) == 3

    def test_branch_preserves_model(self, db: ConversationDatabase) -> None:
        """Test that branching preserves the model."""
        import sqlite3

        # Create conversation
        session_id = db.create_conversation("claude-3-opus")
        msg_id = db.save_message(session_id, "user", "Test", 5)

        # Branch
        new_session_id = db.branch_conversation(session_id, msg_id)

        # Verify model is preserved
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.execute(
                "SELECT model FROM conversations WHERE session_id = ?",
                (new_session_id,),
            )
            row = cursor.fetchone()
            assert row is not None
            assert row[0] == "claude-3-opus"

    def test_branch_with_different_model(self, db: ConversationDatabase) -> None:
        """Test branching with a different model."""
        import sqlite3

        # Create conversation
        session_id = db.create_conversation("gpt-4o")
        msg_id = db.save_message(session_id, "user", "Test", 5)

        # Branch with different model
        new_session_id = db.branch_conversation(
            session_id, msg_id, new_model="claude-3-opus"
        )

        # Verify new model
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.execute(
                "SELECT model FROM conversations WHERE session_id = ?",
                (new_session_id,),
            )
            row = cursor.fetchone()
            assert row is not None
            assert row[0] == "claude-3-opus"

    def test_branch_metadata(self, db: ConversationDatabase) -> None:
        """Test that branch metadata is correctly stored."""
        import sqlite3

        # Create conversation with title
        metadata = {"title": "Original Conversation"}
        session_id = db.create_conversation("gpt-4o", metadata=metadata)
        msg_id = db.save_message(session_id, "user", "Test", 5)

        # Branch
        new_session_id = db.branch_conversation(session_id, msg_id)

        # Verify branch metadata
        with sqlite3.connect(db.db_path) as conn:
            cursor = conn.execute(
                "SELECT metadata FROM conversations WHERE session_id = ?",
                (new_session_id,),
            )
            row = cursor.fetchone()
            assert row is not None
            branch_metadata = json.loads(row[0])

            # Check branch tracking metadata
            assert "branched_from" in branch_metadata
            assert branch_metadata["branched_from"] == session_id
            assert "branch_message_id" in branch_metadata
            assert branch_metadata["branch_message_id"] == msg_id
            assert "branch_timestamp" in branch_metadata

            # Check title is derived from original
            assert "title" in branch_metadata
            assert "Branch from" in branch_metadata["title"]
            assert "Original Conversation" in branch_metadata["title"]

    def test_branch_with_tool_calls(self, db: ConversationDatabase) -> None:
        """Test that tool calls are copied correctly."""
        # Create conversation with tool call
        session_id = db.create_conversation("gpt-4o")
        msg_id = db.save_message(session_id, "assistant", "Using tool", 5)

        # Save tool call
        db.save_tool_call(
            message_id=msg_id,
            tool_name="bash_execute",
            arguments='{"command": "ls"}',
            status="success",
            result="file1.txt\nfile2.txt",
        )

        # Branch
        new_session_id = db.branch_conversation(session_id, msg_id)

        # Verify tool call was copied
        new_messages = db.load_conversation_full(new_session_id)
        assert len(new_messages) == 1
        assert len(new_messages[0]["tool_calls"]) == 1

        tool_call = new_messages[0]["tool_calls"][0]
        assert tool_call["tool_name"] == "bash_execute"
        assert tool_call["status"] == "success"
        assert "file1.txt" in tool_call["result"]

    def test_branch_with_attachments(self, db: ConversationDatabase) -> None:
        """Test that attachments are copied correctly."""
        # Create conversation with attachment
        session_id = db.create_conversation("gpt-4o")
        msg_id = db.save_message(session_id, "user", "See attachment", 5)

        # Save attachment
        db.save_attachment(
            message_id=msg_id,
            file_path="/path/to/file.txt",
            file_type="text",
            mime_type="text/plain",
            file_size=1024,
        )

        # Branch
        new_session_id = db.branch_conversation(session_id, msg_id)

        # Verify attachment was copied
        new_messages = db.load_conversation_full(new_session_id)
        assert len(new_messages) == 1
        assert len(new_messages[0]["attachments"]) == 1

        attachment = new_messages[0]["attachments"][0]
        assert attachment["file_path"] == "/path/to/file.txt"
        assert attachment["file_type"] == "text"
        assert attachment["mime_type"] == "text/plain"

    def test_branch_at_first_message(self, db: ConversationDatabase) -> None:
        """Test branching at the first message."""
        # Create conversation
        session_id = db.create_conversation("gpt-4o")
        msg1_id = db.save_message(session_id, "user", "First", 5)
        db.save_message(session_id, "assistant", "Second", 6)

        # Branch at first message
        new_session_id = db.branch_conversation(session_id, msg1_id)

        # Verify only first message copied
        new_messages = db.load_conversation(new_session_id)
        assert len(new_messages) == 1
        assert new_messages[0]["content"] == "First"

    def test_branch_at_last_message(self, db: ConversationDatabase) -> None:
        """Test branching at the last message."""
        # Create conversation
        session_id = db.create_conversation("gpt-4o")
        db.save_message(session_id, "user", "First", 5)
        db.save_message(session_id, "assistant", "Second", 6)
        msg3_id = db.save_message(session_id, "user", "Third", 7)

        # Branch at last message
        new_session_id = db.branch_conversation(session_id, msg3_id)

        # Verify all messages copied
        new_messages = db.load_conversation(new_session_id)
        assert len(new_messages) == 3

    def test_branch_nonexistent_conversation(self, db: ConversationDatabase) -> None:
        """Test branching from non-existent conversation raises error."""
        with pytest.raises(ConversationNotFoundError, match="not found"):
            db.branch_conversation("nonexistent-session-id", 1)

    def test_branch_with_high_message_id(self, db: ConversationDatabase) -> None:
        """Test branching with message ID higher than exists copies all messages."""
        # Create conversation
        session_id = db.create_conversation("gpt-4o")
        db.save_message(session_id, "user", "First", 5)
        msg2_id = db.save_message(session_id, "assistant", "Second", 6)

        # Branch at message ID higher than exists - should copy all messages
        new_session_id = db.branch_conversation(session_id, msg2_id + 1000)

        # Verify all messages were copied
        new_messages = db.load_conversation(new_session_id)
        assert len(new_messages) == 2
        assert new_messages[0]["content"] == "First"
        assert new_messages[1]["content"] == "Second"

    def test_branch_message_order_preserved(self, db: ConversationDatabase) -> None:
        """Test that message order is preserved when branching."""
        # Create conversation with many messages
        session_id = db.create_conversation("gpt-4o")
        msg_ids = []
        for i in range(5):
            msg_id = db.save_message(session_id, "user", f"Message {i}", 5)
            msg_ids.append(msg_id)

        # Branch at middle message
        new_session_id = db.branch_conversation(session_id, msg_ids[2])

        # Verify order
        new_messages = db.load_conversation(new_session_id)
        assert len(new_messages) == 3
        for i, msg in enumerate(new_messages):
            assert msg["content"] == f"Message {i}"

    def test_branch_multiple_times(self, db: ConversationDatabase) -> None:
        """Test that a conversation can be branched multiple times."""
        # Create original conversation
        session_id = db.create_conversation("gpt-4o")
        msg1_id = db.save_message(session_id, "user", "First", 5)
        msg2_id = db.save_message(session_id, "assistant", "Second", 6)

        # Create first branch
        branch1_id = db.branch_conversation(session_id, msg1_id)

        # Create second branch
        branch2_id = db.branch_conversation(session_id, msg2_id)

        # Verify all three conversations exist and are different
        assert session_id != branch1_id
        assert session_id != branch2_id
        assert branch1_id != branch2_id

        # Verify correct message counts
        assert len(db.load_conversation(session_id)) == 2
        assert len(db.load_conversation(branch1_id)) == 1
        assert len(db.load_conversation(branch2_id)) == 2

    def test_branch_preserves_timestamps(self, db: ConversationDatabase) -> None:
        """Test that message timestamps are preserved when branching."""
        # Create conversation
        session_id = db.create_conversation("gpt-4o")
        msg_id = db.save_message(session_id, "user", "Test", 5)

        # Get original timestamp
        original_messages = db.load_conversation(session_id)
        original_timestamp = original_messages[0]["timestamp"]

        # Branch
        new_session_id = db.branch_conversation(session_id, msg_id)

        # Verify timestamp preserved
        new_messages = db.load_conversation(new_session_id)
        assert new_messages[0]["timestamp"] == original_timestamp
