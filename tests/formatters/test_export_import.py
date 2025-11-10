"""Tests for conversation export/import functionality."""

from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path

import pytest

from consoul.ai.database import ConversationDatabase
from consoul.formatters import (
    CSVFormatter,
    HTMLFormatter,
    JSONFormatter,
    MarkdownFormatter,
    get_formatter,
)


# Sample test data
@pytest.fixture
def sample_metadata():
    """Sample conversation metadata."""
    return {
        "session_id": "test-session-123",
        "model": "claude-3-5-sonnet-20241022",
        "created_at": "2025-11-09T10:00:00Z",
        "updated_at": "2025-11-09T10:15:00Z",
        "message_count": 3,
    }


@pytest.fixture
def sample_messages():
    """Sample conversation messages."""
    return [
        {
            "role": "system",
            "content": "You are a helpful assistant.",
            "timestamp": "2025-11-09T10:00:00Z",
            "tokens": 5,
        },
        {
            "role": "user",
            "content": "Hello! How are you?",
            "timestamp": "2025-11-09T10:05:00Z",
            "tokens": 6,
        },
        {
            "role": "assistant",
            "content": "I'm doing well, thank you! How can I help you today?",
            "timestamp": "2025-11-09T10:10:00Z",
            "tokens": 15,
        },
    ]


@pytest.fixture
def unicode_messages():
    """Messages with Unicode characters and emojis."""
    return [
        {
            "role": "user",
            "content": "Hello! 👋 How are you? 😊",
            "timestamp": "2025-11-09T10:00:00Z",
            "tokens": 8,
        },
        {
            "role": "assistant",
            "content": "你好! I'm great! 🎉 日本語も話せます。",
            "timestamp": "2025-11-09T10:05:00Z",
            "tokens": 12,
        },
    ]


class TestJSONFormatter:
    """Tests for JSON formatter."""

    def test_export_basic(self, sample_metadata, sample_messages):
        """Test basic JSON export."""
        formatter = JSONFormatter()
        output = formatter.export(sample_metadata, sample_messages)

        # Parse JSON
        data = json.loads(output)

        # Verify structure
        assert data["version"] == "1.0"
        assert "exported_at" in data
        assert data["conversation"]["session_id"] == "test-session-123"
        assert data["conversation"]["model"] == "claude-3-5-sonnet-20241022"
        assert data["conversation"]["message_count"] == 3
        assert len(data["messages"]) == 3

        # Verify messages
        assert data["messages"][0]["role"] == "system"
        assert data["messages"][0]["content"] == "You are a helpful assistant."
        assert data["messages"][0]["tokens"] == 5

    def test_export_unicode(self, sample_metadata, unicode_messages):
        """Test JSON export with Unicode characters."""
        formatter = JSONFormatter()
        output = formatter.export(sample_metadata, unicode_messages)

        data = json.loads(output)
        assert "👋" in data["messages"][0]["content"]
        assert "你好" in data["messages"][1]["content"]
        assert "日本語" in data["messages"][1]["content"]

    def test_export_to_file(self, sample_metadata, sample_messages):
        """Test exporting to file."""
        formatter = JSONFormatter()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_path = Path(f.name)

        try:
            formatter.export_to_file(sample_metadata, sample_messages, output_path)
            assert output_path.exists()

            data = json.loads(output_path.read_text())
            assert data["conversation"]["session_id"] == "test-session-123"
        finally:
            output_path.unlink(missing_ok=True)

    def test_file_extension(self):
        """Test file extension property."""
        formatter = JSONFormatter()
        assert formatter.file_extension == "json"

    def test_validate_valid_data(self, sample_metadata, sample_messages):
        """Test validation with valid data."""
        formatter = JSONFormatter()
        output = formatter.export(sample_metadata, sample_messages)
        data = json.loads(output)

        # Should not raise
        JSONFormatter.validate_import_data(data)

    def test_validate_missing_version(self):
        """Test validation with missing version."""
        data = {"conversation": {}, "messages": []}

        with pytest.raises(ValueError, match="Unsupported export version"):
            JSONFormatter.validate_import_data(data)

    def test_validate_wrong_version(self):
        """Test validation with wrong version."""
        data = {
            "version": "2.0",
            "exported_at": "2025-11-09T10:00:00Z",
            "conversation": {},
            "messages": [],
        }

        with pytest.raises(ValueError, match="Unsupported export version"):
            JSONFormatter.validate_import_data(data)

    def test_validate_missing_conversation_keys(self):
        """Test validation with missing conversation keys."""
        data = {
            "version": "1.0",
            "exported_at": "2025-11-09T10:00:00Z",
            "conversation": {"session_id": "test"},  # Missing other required keys
            "messages": [],
        }

        with pytest.raises(ValueError, match="Missing conversation keys"):
            JSONFormatter.validate_import_data(data)

    def test_validate_invalid_role(self):
        """Test validation with invalid message role."""
        data = {
            "version": "1.0",
            "exported_at": "2025-11-09T10:00:00Z",
            "conversation": {
                "session_id": "test",
                "model": "test-model",
                "created_at": "2025-11-09T10:00:00Z",
                "updated_at": "2025-11-09T10:00:00Z",
            },
            "messages": [
                {
                    "role": "invalid_role",
                    "content": "test",
                    "timestamp": "2025-11-09T10:00:00Z",
                }
            ],
        }

        with pytest.raises(ValueError, match="invalid role"):
            JSONFormatter.validate_import_data(data)


class TestMarkdownFormatter:
    """Tests for Markdown formatter."""

    def test_export_basic(self, sample_metadata, sample_messages):
        """Test basic Markdown export."""
        formatter = MarkdownFormatter()
        output = formatter.export(sample_metadata, sample_messages)

        # Check header
        assert "# Conversation: test-session-123" in output
        assert "**Model**: claude-3-5-sonnet-20241022" in output
        assert "**Messages**: 3" in output
        assert "**Total Tokens**: 26" in output

        # Check messages with emojis
        assert "## ⚙️ System" in output
        assert "## 👤 User" in output
        assert "## 🤖 Assistant" in output

        # Check content
        assert "You are a helpful assistant." in output
        assert "Hello! How are you?" in output

    def test_export_unicode(self, sample_metadata, unicode_messages):
        """Test Markdown export with Unicode."""
        formatter = MarkdownFormatter()
        output = formatter.export(sample_metadata, unicode_messages)

        assert "👋" in output
        assert "你好" in output
        assert "日本語" in output

    def test_file_extension(self):
        """Test file extension property."""
        formatter = MarkdownFormatter()
        assert formatter.file_extension == "md"


class TestHTMLFormatter:
    """Tests for HTML formatter."""

    def test_export_basic(self, sample_metadata, sample_messages):
        """Test basic HTML export."""
        formatter = HTMLFormatter()
        output = formatter.export(sample_metadata, sample_messages)

        # Check HTML structure
        assert "<!DOCTYPE html>" in output
        assert '<html lang="en">' in output
        assert "</html>" in output

        # Check metadata
        assert "test-session-123" in output
        assert "claude-3-5-sonnet-20241022" in output

        # Check messages
        assert "You are a helpful assistant." in output
        assert "Hello! How are you?" in output

        # Check CSS classes
        assert 'class="message system"' in output
        assert 'class="message user"' in output
        assert 'class="message assistant"' in output

    def test_export_html_escaping(self):
        """Test HTML special characters are escaped."""
        metadata = {
            "session_id": "test",
            "model": "test-model",
            "created_at": "2025-11-09T10:00:00Z",
            "updated_at": "2025-11-09T10:00:00Z",
            "message_count": 1,
        }
        messages = [
            {
                "role": "user",
                "content": "<script>alert('xss')</script>",
                "timestamp": "2025-11-09T10:00:00Z",
                "tokens": 5,
            }
        ]

        formatter = HTMLFormatter()
        output = formatter.export(metadata, messages)

        # Should be escaped
        assert "&lt;script&gt;" in output
        assert "<script>" not in output or output.count("<script>") == 0  # Only in CSS

    def test_export_unicode(self, sample_metadata, unicode_messages):
        """Test HTML export with Unicode."""
        formatter = HTMLFormatter()
        output = formatter.export(sample_metadata, unicode_messages)

        assert "👋" in output
        assert "你好" in output
        assert "日本語" in output

    def test_file_extension(self):
        """Test file extension property."""
        formatter = HTMLFormatter()
        assert formatter.file_extension == "html"


class TestCSVFormatter:
    """Tests for CSV formatter."""

    def test_export_basic(self, sample_metadata, sample_messages):
        """Test basic CSV export."""
        formatter = CSVFormatter()
        output = formatter.export(sample_metadata, sample_messages)

        # Parse CSV
        lines = output.strip().split("\n")
        reader = csv.DictReader(lines)
        rows = list(reader)

        assert len(rows) == 3

        # Check header
        assert rows[0].keys() == {
            "session_id",
            "model",
            "timestamp",
            "role",
            "content",
            "tokens",
        }

        # Check first row
        assert rows[0]["session_id"] == "test-session-123"
        assert rows[0]["model"] == "claude-3-5-sonnet-20241022"
        assert rows[0]["role"] == "system"
        assert rows[0]["content"] == "You are a helpful assistant."
        assert rows[0]["tokens"] == "5"

    def test_export_unicode(self, sample_metadata, unicode_messages):
        """Test CSV export with Unicode."""
        formatter = CSVFormatter()
        output = formatter.export(sample_metadata, unicode_messages)

        assert "👋" in output
        assert "你好" in output

    def test_file_extension(self):
        """Test file extension property."""
        formatter = CSVFormatter()
        assert formatter.file_extension == "csv"


class TestGetFormatter:
    """Tests for get_formatter function."""

    def test_get_json_formatter(self):
        """Test getting JSON formatter."""
        formatter = get_formatter("json")
        assert isinstance(formatter, JSONFormatter)

    def test_get_markdown_formatter(self):
        """Test getting Markdown formatter."""
        formatter = get_formatter("markdown")
        assert isinstance(formatter, MarkdownFormatter)

    def test_get_html_formatter(self):
        """Test getting HTML formatter."""
        formatter = get_formatter("html")
        assert isinstance(formatter, HTMLFormatter)

    def test_get_csv_formatter(self):
        """Test getting CSV formatter."""
        formatter = get_formatter("csv")
        assert isinstance(formatter, CSVFormatter)

    def test_case_insensitive(self):
        """Test format name is case insensitive."""
        assert isinstance(get_formatter("JSON"), JSONFormatter)
        assert isinstance(get_formatter("Markdown"), MarkdownFormatter)
        assert isinstance(get_formatter("HTML"), HTMLFormatter)
        assert isinstance(get_formatter("CSV"), CSVFormatter)

    def test_unsupported_format(self):
        """Test unsupported format raises error."""
        with pytest.raises(ValueError, match="Unsupported format"):
            get_formatter("invalid")


class TestMultiConversation:
    """Tests for multi-conversation export/import."""

    def test_export_multiple_conversations(self):
        """Test exporting multiple conversations."""
        metadata1 = {
            "session_id": "session-1",
            "model": "model-1",
            "created_at": "2025-11-09T10:00:00Z",
            "updated_at": "2025-11-09T10:10:00Z",
            "message_count": 2,
        }
        messages1 = [
            {
                "role": "user",
                "content": "Hello 1",
                "timestamp": "2025-11-09T10:00:00Z",
                "tokens": 2,
            },
            {
                "role": "assistant",
                "content": "Response 1",
                "timestamp": "2025-11-09T10:05:00Z",
                "tokens": 3,
            },
        ]

        metadata2 = {
            "session_id": "session-2",
            "model": "model-2",
            "created_at": "2025-11-09T11:00:00Z",
            "updated_at": "2025-11-09T11:10:00Z",
            "message_count": 2,
        }
        messages2 = [
            {
                "role": "user",
                "content": "Hello 2",
                "timestamp": "2025-11-09T11:00:00Z",
                "tokens": 2,
            },
            {
                "role": "assistant",
                "content": "Response 2",
                "timestamp": "2025-11-09T11:05:00Z",
                "tokens": 3,
            },
        ]

        # Export multiple conversations
        conversations_data = [(metadata1, messages1), (metadata2, messages2)]
        output = JSONFormatter.export_multiple(conversations_data)

        # Parse and verify
        data = json.loads(output)
        assert data["version"] == "1.0-multi"
        assert data["conversation_count"] == 2
        assert len(data["conversations"]) == 2

        # Verify first conversation
        conv1 = data["conversations"][0]
        assert conv1["conversation"]["session_id"] == "session-1"
        assert len(conv1["messages"]) == 2

        # Verify second conversation
        conv2 = data["conversations"][1]
        assert conv2["conversation"]["session_id"] == "session-2"
        assert len(conv2["messages"]) == 2

    def test_validate_multi_conversation_format(self):
        """Test validation of multi-conversation format."""
        # Create valid multi-conversation data
        conversations_data = [
            (
                {
                    "session_id": "s1",
                    "model": "m1",
                    "created_at": "2025-11-09T10:00:00Z",
                    "updated_at": "2025-11-09T10:00:00Z",
                    "message_count": 1,
                },
                [
                    {
                        "role": "user",
                        "content": "test",
                        "timestamp": "2025-11-09T10:00:00Z",
                        "tokens": 1,
                    }
                ],
            )
        ]

        output = JSONFormatter.export_multiple(conversations_data)
        data = json.loads(output)

        # Should validate successfully
        JSONFormatter.validate_import_data(data)

    def test_validate_multi_conversation_invalid(self):
        """Test validation rejects invalid multi-conversation format."""
        data = {
            "version": "1.0-multi",
            "exported_at": "2025-11-09T10:00:00Z",
            "conversation_count": 1,
            "conversations": [
                {
                    "conversation": {
                        "session_id": "test"
                        # Missing required fields
                    },
                    "messages": [],
                }
            ],
        }

        with pytest.raises(ValueError, match="Missing conversation keys"):
            JSONFormatter.validate_import_data(data)


class TestRoundTrip:
    """Tests for export → import round-trip."""

    def test_round_trip(self):
        """Test exporting and importing conversation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            export_path = Path(tmpdir) / "export.json"

            # Create database and add conversation
            db = ConversationDatabase(str(db_path))
            session_id = db.create_conversation("test-model")

            db.save_message(session_id, "system", "You are a helpful assistant.", 5)
            db.save_message(session_id, "user", "Hello!", 2)
            db.save_message(session_id, "assistant", "Hi there!", 3)

            # Export
            meta = db.get_conversation_metadata(session_id)
            messages = db.load_conversation(session_id)

            formatter = JSONFormatter()
            formatter.export_to_file(meta, messages, export_path)

            # Import to new database
            db2_path = Path(tmpdir) / "test2.db"
            db2 = ConversationDatabase(str(db2_path))

            import_data = json.loads(export_path.read_text())
            JSONFormatter.validate_import_data(import_data)

            conv = import_data["conversation"]
            db2.create_conversation(model=conv["model"], session_id=conv["session_id"])

            for msg in import_data["messages"]:
                db2.save_message(
                    conv["session_id"], msg["role"], msg["content"], msg.get("tokens")
                )

            # Verify imported data matches original
            imported_meta = db2.get_conversation_metadata(session_id)
            imported_messages = db2.load_conversation(session_id)

            assert imported_meta["model"] == meta["model"]
            assert imported_meta["message_count"] == meta["message_count"]
            assert len(imported_messages) == len(messages)

            for orig, imported in zip(messages, imported_messages, strict=True):
                assert imported["role"] == orig["role"]
                assert imported["content"] == orig["content"]
                assert imported["tokens"] == orig["tokens"]

    def test_round_trip_multi_conversation(self):
        """Test exporting and importing multiple conversations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            export_path = Path(tmpdir) / "export-multi.json"

            # Create database and add multiple conversations
            db = ConversationDatabase(str(db_path))

            session_id1 = db.create_conversation("model-1")
            db.save_message(session_id1, "user", "Hello 1", 2)
            db.save_message(session_id1, "assistant", "Response 1", 3)

            session_id2 = db.create_conversation("model-2")
            db.save_message(session_id2, "user", "Hello 2", 2)
            db.save_message(session_id2, "assistant", "Response 2", 3)

            # Export all conversations
            conversations = db.list_conversations()
            conversations_data = []
            for conv in conversations:
                meta = db.get_conversation_metadata(conv["session_id"])
                messages = db.load_conversation(conv["session_id"])
                conversations_data.append((meta, messages))

            export_output = JSONFormatter.export_multiple(conversations_data)
            export_path.write_text(export_output, encoding="utf-8")

            # Import to new database
            db2_path = Path(tmpdir) / "test2.db"
            db2 = ConversationDatabase(str(db2_path))

            import_data = json.loads(export_path.read_text())
            JSONFormatter.validate_import_data(import_data)

            assert import_data["version"] == "1.0-multi"
            assert import_data["conversation_count"] == 2

            # Import all conversations
            for conv_data in import_data["conversations"]:
                conv = conv_data["conversation"]
                db2.create_conversation(
                    model=conv["model"], session_id=conv["session_id"]
                )

                for msg in conv_data["messages"]:
                    db2.save_message(
                        conv["session_id"],
                        msg["role"],
                        msg["content"],
                        msg.get("tokens"),
                    )

            # Verify both conversations were imported
            imported_convs = db2.list_conversations()
            assert len(imported_convs) == 2

            # Verify first conversation
            meta1 = db2.get_conversation_metadata(session_id1)
            messages1 = db2.load_conversation(session_id1)
            assert meta1["model"] == "model-1"
            assert len(messages1) == 2

            # Verify second conversation
            meta2 = db2.get_conversation_metadata(session_id2)
            messages2 = db2.load_conversation(session_id2)
            assert meta2["model"] == "model-2"
            assert len(messages2) == 2


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_conversation(self):
        """Test exporting conversation with no messages."""
        metadata = {
            "session_id": "empty",
            "model": "test-model",
            "created_at": "2025-11-09T10:00:00Z",
            "updated_at": "2025-11-09T10:00:00Z",
            "message_count": 0,
        }
        messages = []

        # JSON
        json_formatter = JSONFormatter()
        json_output = json_formatter.export(metadata, messages)
        data = json.loads(json_output)
        assert len(data["messages"]) == 0

        # Markdown
        md_formatter = MarkdownFormatter()
        md_output = md_formatter.export(metadata, messages)
        assert "empty" in md_output

        # HTML
        html_formatter = HTMLFormatter()
        html_output = html_formatter.export(metadata, messages)
        assert "empty" in html_output

        # CSV
        csv_formatter = CSVFormatter()
        csv_output = csv_formatter.export(metadata, messages)
        # Should only have header
        assert csv_output.count("\n") == 1  # Just header line

    def test_large_conversation(self):
        """Test exporting large conversation."""
        metadata = {
            "session_id": "large",
            "model": "test-model",
            "created_at": "2025-11-09T10:00:00Z",
            "updated_at": "2025-11-09T10:00:00Z",
            "message_count": 1000,
        }

        # Generate 1000 messages
        messages = [
            {
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Message {i}",
                "timestamp": f"2025-11-09T10:{i % 60:02d}:00Z",
                "tokens": 3,
            }
            for i in range(1000)
        ]

        # Test all formatters handle large data
        json_formatter = JSONFormatter()
        json_output = json_formatter.export(metadata, messages)
        data = json.loads(json_output)
        assert len(data["messages"]) == 1000

        md_formatter = MarkdownFormatter()
        md_output = md_formatter.export(metadata, messages)
        assert "Message 999" in md_output

        csv_formatter = CSVFormatter()
        csv_output = csv_formatter.export(metadata, messages)
        assert csv_output.count("\n") == 1001  # Header + 1000 rows
