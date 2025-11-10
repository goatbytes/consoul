"""Tests for ConversationList widget."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import pytest

from consoul.ai.database import ConversationDatabase
from consoul.tui.widgets.conversation_list import ConversationList

if TYPE_CHECKING:
    from pathlib import Path


class TestConversationListInitialization:
    """Test ConversationList initialization and setup."""

    def test_initialization(self, tmp_path: Path) -> None:
        """Test widget initializes with database."""
        db_path = tmp_path / "test.db"
        db = ConversationDatabase(db_path)

        widget = ConversationList(db=db)

        assert widget.db is db
        assert widget.loaded_count == 0
        assert widget.conversation_count == 0
        assert widget.selected_id is None
        assert widget._is_searching is False

    @pytest.mark.asyncio
    async def test_mount_initializes_table(self, tmp_path: Path) -> None:
        """Test on_mount sets up table columns."""
        db_path = tmp_path / "test.db"
        db = ConversationDatabase(db_path)

        widget = ConversationList(db=db)

        # Mount the widget
        async with widget.app.run_test():
            await widget.on_mount()

            assert widget.border_title == "Conversations (0)"
            assert len(widget.table.columns) == 2


class TestConversationListLoading:
    """Test conversation loading functionality."""

    @pytest.mark.asyncio
    async def test_initial_load(self, tmp_path: Path) -> None:
        """Test initial conversation load."""
        db_path = tmp_path / "test.db"
        db = ConversationDatabase(db_path)

        # Create test conversations
        for i in range(100):
            session_id = db.create_conversation(model="gpt-4o")
            db.save_message(session_id, "user", f"Test message {i}", 5)

        widget = ConversationList(db=db)

        async with widget.app.run_test():
            await widget.on_mount()

            # Should load initial 50
            assert widget.loaded_count == 50
            assert widget.table.row_count == 50
            assert widget.conversation_count == 50

    @pytest.mark.asyncio
    async def test_lazy_loading(self, tmp_path: Path) -> None:
        """Test lazy loading on scroll."""
        db_path = tmp_path / "test.db"
        db = ConversationDatabase(db_path)

        # Create 100 conversations
        for i in range(100):
            session_id = db.create_conversation(model="gpt-4o")
            db.save_message(session_id, "user", f"Message {i}", 5)

        widget = ConversationList(db=db)

        async with widget.app.run_test():
            await widget.on_mount()

            # Initial load
            assert widget.loaded_count == 50

            # Trigger lazy load
            widget.load_conversations(limit=50)

            # Should have loaded all 100
            assert widget.loaded_count == 100
            assert widget.table.row_count == 100

    @pytest.mark.asyncio
    async def test_empty_database(self, tmp_path: Path) -> None:
        """Test widget handles empty database gracefully."""
        db_path = tmp_path / "test.db"
        db = ConversationDatabase(db_path)

        widget = ConversationList(db=db)

        async with widget.app.run_test():
            await widget.on_mount()

            assert widget.loaded_count == 0
            assert widget.table.row_count == 0
            assert widget.border_title == "Conversations (0)"

    @pytest.mark.asyncio
    async def test_single_conversation(self, tmp_path: Path) -> None:
        """Test widget with single conversation."""
        db_path = tmp_path / "test.db"
        db = ConversationDatabase(db_path)

        session_id = db.create_conversation(model="gpt-4o")
        db.save_message(session_id, "user", "Hello world", 5)

        widget = ConversationList(db=db)

        async with widget.app.run_test():
            await widget.on_mount()

            assert widget.loaded_count == 1
            assert widget.table.row_count == 1
            assert widget.border_title == "Conversations (1)"


class TestConversationListSearch:
    """Test FTS5 search functionality."""

    @pytest.mark.asyncio
    async def test_search_with_results(self, tmp_path: Path) -> None:
        """Test FTS5 search returns matching conversations."""
        db_path = tmp_path / "test.db"
        db = ConversationDatabase(db_path)

        # Create conversations with different content
        session1 = db.create_conversation(model="gpt-4o")
        db.save_message(session1, "user", "Python tutorial for beginners", 5)

        session2 = db.create_conversation(model="gpt-4o")
        db.save_message(session2, "user", "JavaScript guide", 5)

        session3 = db.create_conversation(model="gpt-4o")
        db.save_message(session3, "user", "Advanced Python techniques", 5)

        widget = ConversationList(db=db)

        async with widget.app.run_test():
            await widget.on_mount()

            # Initial state: 3 conversations
            assert widget.table.row_count == 3

            # Search for "Python"
            await widget.search("Python")

            # Should only show 2 Python-related conversations
            assert widget.table.row_count == 2
            assert widget.conversation_count == 2
            assert widget._is_searching is True

    @pytest.mark.asyncio
    async def test_search_no_results(self, tmp_path: Path) -> None:
        """Test search with no matching conversations."""
        db_path = tmp_path / "test.db"
        db = ConversationDatabase(db_path)

        session = db.create_conversation(model="gpt-4o")
        db.save_message(session, "user", "Hello world", 5)

        widget = ConversationList(db=db)

        async with widget.app.run_test():
            await widget.on_mount()

            # Search for non-existent term
            await widget.search("nonexistent")

            assert widget.table.row_count == 0
            assert widget.conversation_count == 0

    @pytest.mark.asyncio
    async def test_clear_search(self, tmp_path: Path) -> None:
        """Test clearing search reloads all conversations."""
        db_path = tmp_path / "test.db"
        db = ConversationDatabase(db_path)

        # Create conversations
        for i in range(10):
            session = db.create_conversation(model="gpt-4o")
            content = "Python" if i < 5 else "JavaScript"
            db.save_message(session, "user", f"{content} topic {i}", 5)

        widget = ConversationList(db=db)

        async with widget.app.run_test():
            await widget.on_mount()

            # Initial: 10 conversations
            assert widget.table.row_count == 10

            # Search narrows down
            await widget.search("Python")
            assert widget.table.row_count == 5

            # Clear search with empty string
            await widget.search("")
            assert widget.table.row_count == 10
            assert widget._is_searching is False


class TestConversationListSelection:
    """Test conversation selection functionality."""

    @pytest.mark.asyncio
    async def test_row_selection(self, tmp_path: Path) -> None:
        """Test selecting a conversation row."""
        db_path = tmp_path / "test.db"
        db = ConversationDatabase(db_path)

        session_id = db.create_conversation(model="gpt-4o")
        db.save_message(session_id, "user", "Test message", 5)

        widget = ConversationList(db=db)

        message_posted = False
        selected_id = None

        def on_selected(event: ConversationList.ConversationSelected) -> None:
            nonlocal message_posted, selected_id
            message_posted = True
            selected_id = event.conversation_id

        async with widget.app.run_test():
            widget.on(ConversationList.ConversationSelected, on_selected)

            await widget.on_mount()

            # Simulate row selection
            from textual.widgets import DataTable

            row_key = widget.table.get_row_at(0)[0]  # Get first row key
            event = DataTable.RowSelected(widget.table, row_key, 0)
            widget.on_data_table_row_selected(event)

            assert message_posted
            assert selected_id == session_id
            assert widget.selected_id == session_id


class TestConversationListTitleGeneration:
    """Test conversation title generation logic."""

    @pytest.mark.asyncio
    async def test_title_from_first_user_message(self, tmp_path: Path) -> None:
        """Test title extracted from first user message."""
        db_path = tmp_path / "test.db"
        db = ConversationDatabase(db_path)

        session_id = db.create_conversation(model="gpt-4o")
        db.save_message(session_id, "user", "This is the title message", 5)
        db.save_message(session_id, "assistant", "Response", 5)

        widget = ConversationList(db=db)

        async with widget.app.run_test():
            await widget.on_mount()

            # Get the conversation from database
            conversations = db.list_conversations(limit=1)
            conv = conversations[0]

            title = widget._get_conversation_title(conv)
            assert title == "This is the title message"

    @pytest.mark.asyncio
    async def test_title_truncation(self, tmp_path: Path) -> None:
        """Test long titles are truncated."""
        db_path = tmp_path / "test.db"
        db = ConversationDatabase(db_path)

        long_message = "A" * 100  # Very long message
        session_id = db.create_conversation(model="gpt-4o")
        db.save_message(session_id, "user", long_message, 5)

        widget = ConversationList(db=db)

        async with widget.app.run_test():
            await widget.on_mount()

            conversations = db.list_conversations(limit=1)
            conv = conversations[0]

            title = widget._get_conversation_title(conv)
            assert len(title) <= 50
            assert title.endswith("...")

    @pytest.mark.asyncio
    async def test_title_multiline_uses_first_line(self, tmp_path: Path) -> None:
        """Test multiline message uses only first line for title."""
        db_path = tmp_path / "test.db"
        db = ConversationDatabase(db_path)

        multiline_message = "First line\nSecond line\nThird line"
        session_id = db.create_conversation(model="gpt-4o")
        db.save_message(session_id, "user", multiline_message, 5)

        widget = ConversationList(db=db)

        async with widget.app.run_test():
            await widget.on_mount()

            conversations = db.list_conversations(limit=1)
            conv = conversations[0]

            title = widget._get_conversation_title(conv)
            assert title == "First line"

    @pytest.mark.asyncio
    async def test_untitled_when_no_user_messages(self, tmp_path: Path) -> None:
        """Test 'Untitled' for conversations without user messages."""
        db_path = tmp_path / "test.db"
        db = ConversationDatabase(db_path)

        session_id = db.create_conversation(model="gpt-4o")
        db.save_message(session_id, "system", "System prompt", 5)

        widget = ConversationList(db=db)

        async with widget.app.run_test():
            await widget.on_mount()

            conversations = db.list_conversations(limit=1)
            conv = conversations[0]

            title = widget._get_conversation_title(conv)
            assert title == "Untitled Conversation"


class TestConversationListPerformance:
    """Test performance with large datasets."""

    @pytest.mark.asyncio
    async def test_large_dataset_load_performance(self, tmp_path: Path) -> None:
        """Test loading performance with 2000+ conversations."""
        db_path = tmp_path / "test.db"
        db = ConversationDatabase(db_path)

        # Create 2000 conversations
        for i in range(2000):
            session_id = db.create_conversation(model="gpt-4o")
            db.save_message(session_id, "user", f"Message {i}", 5)

        widget = ConversationList(db=db)

        async with widget.app.run_test():
            start = time.time()
            await widget.on_mount()
            elapsed = time.time() - start

            # Should load initial 50 quickly (< 500ms)
            assert elapsed < 0.5

            # Verify virtualization - only loaded 50
            assert widget.loaded_count == 50
            assert widget.table.row_count == 50

    @pytest.mark.asyncio
    async def test_search_performance(self, tmp_path: Path) -> None:
        """Test search performance with large dataset."""
        db_path = tmp_path / "test.db"
        db = ConversationDatabase(db_path)

        # Create 1000 conversations with searchable content
        for i in range(1000):
            session_id = db.create_conversation(model="gpt-4o")
            content = f"Python tutorial {i}" if i % 2 == 0 else f"JavaScript guide {i}"
            db.save_message(session_id, "user", content, 5)

        widget = ConversationList(db=db)

        async with widget.app.run_test():
            await widget.on_mount()

            # Search should be fast with FTS5
            start = time.time()
            await widget.search("Python")
            elapsed = time.time() - start

            # FTS5 search should be fast (< 200ms)
            assert elapsed < 0.2

            # Should return ~500 matches
            assert widget.table.row_count == 500
