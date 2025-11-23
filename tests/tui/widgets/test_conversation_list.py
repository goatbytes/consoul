"""Tests for ConversationList widget."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import pytest
from textual.app import App, ComposeResult

from consoul.ai.database import ConversationDatabase
from consoul.tui.widgets.conversation_list import ConversationList

if TYPE_CHECKING:
    from pathlib import Path


class ConversationListTestApp(App[None]):
    """Test app for ConversationList widget."""

    def __init__(self, widget: ConversationList) -> None:
        """Initialize test app with a ConversationList.

        Args:
            widget: ConversationList widget to test
        """
        super().__init__()
        self.widget = widget

    def compose(self) -> ComposeResult:
        """Compose test app with ConversationList."""
        yield self.widget


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


class TestConversationDeletion:
    """Test conversation deletion functionality."""

    @pytest.mark.asyncio
    async def test_delete_conversation_modal_created(self, tmp_path: Path) -> None:
        """Test that delete modal is created with correct parameters."""
        from consoul.tui.widgets.conversation_list import DeleteConversationModal

        modal = DeleteConversationModal(
            conversation_id="test-id", conversation_title="Test Conversation"
        )

        assert modal.conversation_id == "test-id"
        assert modal.conversation_title == "Test Conversation"

    @pytest.mark.asyncio
    async def test_delete_conversation_updates_db(self, tmp_path: Path) -> None:
        """Test that deleting conversation removes it from database."""
        db_path = tmp_path / "test.db"
        db = ConversationDatabase(db_path)

        # Create test conversation
        session_id = db.create_conversation(model="gpt-4o")
        db.save_message(session_id, "user", "Test message", 5)

        widget = ConversationList(db=db)
        app = ConversationListTestApp(widget)

        async with app.run_test():
            # Manually load conversations to avoid worker timeout
            await widget.load_conversations()

            # Verify conversation exists
            assert widget.table.row_count == 1
            conversations = db.list_conversations(limit=10)
            assert len(conversations) == 1

            # Simulate deletion
            result = (session_id, True)  # confirmed
            await widget._handle_delete(result)

            # Verify removed from UI and database
            assert widget.table.row_count == 0
            conversations = db.list_conversations(limit=10)
            assert len(conversations) == 0

    @pytest.mark.asyncio
    async def test_delete_conversation_posts_message(self, tmp_path: Path) -> None:
        """Test that deleting conversation posts ConversationDeleted message."""
        db_path = tmp_path / "test.db"
        db = ConversationDatabase(db_path)

        # Create test conversation
        session_id = db.create_conversation(model="gpt-4o")
        db.save_message(session_id, "user", "Test message", 5)
        widget = ConversationList(db=db)

        # Manually add conversation to table (same as test_delete_conversation_updates_db pattern)
        async def manually_setup():
            """Setup widget without on_mount worker."""
            widget.table.add_column("Title", key="title")
            widget.table.show_header = False
            await widget.load_conversations()
            widget.conversation_count = widget.table.row_count

        app = ConversationListTestApp(widget)

        async with app.run_test():
            # Cancel the on_mount worker and manually setup
            widget.workers.cancel_all()
            await manually_setup()

            # Track posted messages
            posted_messages = []
            original_post_message = widget.post_message

            def capture_message(msg):
                posted_messages.append(msg)
                # Still call original to maintain functionality
                original_post_message(msg)

            widget.post_message = capture_message

            # Simulate deletion of active conversation
            widget.selected_id = session_id
            result = (session_id, True)
            await widget._handle_delete(result)

            # Verify ConversationDeleted message was posted
            assert len(posted_messages) == 1
            assert hasattr(posted_messages[0], "conversation_id")
            assert posted_messages[0].conversation_id == session_id
            assert posted_messages[0].was_active is True

    @pytest.mark.asyncio
    async def test_delete_cancelled_does_nothing(self, tmp_path: Path) -> None:
        """Test that cancelling deletion doesn't delete conversation."""
        db_path = tmp_path / "test.db"
        db = ConversationDatabase(db_path)

        # Create test conversation
        session_id = db.create_conversation(model="gpt-4o")
        db.save_message(session_id, "user", "Test message", 5)
        widget = ConversationList(db=db)
        app = ConversationListTestApp(widget)

        async with app.run_test():
            # Clear table and manually load to avoid duplicate key from on_mount worker
            widget.table.clear()
            widget.loaded_count = 0
            await widget.load_conversations()

            # Simulate cancellation
            result = (session_id, False)  # not confirmed
            await widget._handle_delete(result)

            # Verify conversation still exists
            assert widget.table.row_count == 1
            conversations = db.list_conversations(limit=10)
            assert len(conversations) == 1

    @pytest.mark.asyncio
    async def test_delete_none_result_does_nothing(self, tmp_path: Path) -> None:
        """Test that None result (modal dismissed) doesn't delete."""
        db_path = tmp_path / "test.db"
        db = ConversationDatabase(db_path)

        # Create test conversation
        session_id = db.create_conversation(model="gpt-4o")
        db.save_message(session_id, "user", "Test message", 5)
        widget = ConversationList(db=db)
        app = ConversationListTestApp(widget)

        async with app.run_test():
            # Manually load conversations to avoid worker timeout
            await widget.load_conversations()

            # Simulate modal dismissal
            result = None
            await widget._handle_delete(result)

            # Verify conversation still exists
            assert widget.table.row_count == 1

    @pytest.mark.asyncio
    async def test_delete_handles_error_gracefully(self, tmp_path: Path) -> None:
        """Test that deletion errors are handled gracefully."""
        db_path = tmp_path / "test.db"
        db = ConversationDatabase(db_path)

        widget = ConversationList(db=db)
        app = ConversationListTestApp(widget)

        async with app.run_test():
            # Track notifications
            notifications = []

            def capture_notify(*args, **kwargs):
                notifications.append({"args": args, "kwargs": kwargs})

            app.notify = capture_notify

            # Try to delete non-existent conversation
            result = ("non-existent-id", True)
            await widget._handle_delete(result)

            # Verify error notification was shown
            assert len(notifications) == 1
            assert "Failed to delete" in str(notifications[0])
