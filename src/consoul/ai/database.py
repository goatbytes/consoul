"""SQLite persistence for conversation history.

This module provides low-level SQLite operations for storing and retrieving
conversation history. It manages the database schema, handles migrations,
and provides CRUD operations for conversations and messages.

Features:
    - Schema versioning for future migrations
    - Session-based conversation isolation
    - Message persistence with token counts
    - Conversation metadata and statistics
    - Graceful error handling with fallback support

Example:
    >>> db = ConversationDatabase()
    >>> session_id = db.create_conversation("gpt-4o")
    >>> db.save_message(session_id, "user", "Hello!", 5)
    >>> db.save_message(session_id, "assistant", "Hi there!", 6)
    >>> messages = db.load_conversation(session_id)
    >>> len(messages)
    2
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


class DatabaseError(Exception):
    """Base exception for database operations."""

    pass


class ConversationNotFoundError(DatabaseError):
    """Raised when a conversation session is not found."""

    pass


class ConversationDatabase:
    """SQLite persistence layer for conversation history.

    Manages conversations and messages in a SQLite database with support for
    session isolation, metadata tracking, and efficient querying.

    Attributes:
        db_path: Path to the SQLite database file
        schema_version: Current database schema version

    Example:
        >>> db = ConversationDatabase("~/.consoul/history.db")
        >>> session_id = db.create_conversation("gpt-4o")
        >>> db.save_message(session_id, "user", "Hello!", 5)
        >>> conversations = db.list_conversations(limit=10)
    """

    SCHEMA_VERSION = 2  # Schema v2: Added message_type, tool_calls, attachments tables

    def __init__(self, db_path: Path | str = "~/.consoul/history.db"):
        """Initialize database connection and schema.

        Args:
            db_path: Path to SQLite database file (default: ~/.consoul/history.db)

        Raises:
            DatabaseError: If database initialization fails
        """
        self.db_path = Path(db_path).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            self._init_schema()
        except Exception as e:
            raise DatabaseError(f"Failed to initialize database: {e}") from e

    def _init_schema(self) -> None:
        """Initialize database schema with versioning.

        Creates tables if they don't exist and sets up indexes for performance.
        Uses WAL mode for better concurrent access.
        """
        with sqlite3.connect(self.db_path) as conn:
            # Enable foreign keys (required for CASCADE)
            conn.execute("PRAGMA foreign_keys=ON")
            # Enable WAL mode for better concurrent access
            conn.execute("PRAGMA journal_mode=WAL")

            # Create schema
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY
                );

                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    session_id TEXT UNIQUE NOT NULL,
                    model TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT DEFAULT '{}',
                    summary TEXT DEFAULT NULL
                );

                -- Enhanced messages table with type discrimination
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    message_type TEXT NOT NULL DEFAULT 'user',
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tokens INTEGER,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(session_id)
                        ON DELETE CASCADE
                );

                -- Tool calls table (linked to message)
                CREATE TABLE IF NOT EXISTS tool_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER NOT NULL,
                    tool_name TEXT NOT NULL,
                    arguments TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    result TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (message_id) REFERENCES messages(id)
                        ON DELETE CASCADE
                );

                -- Attachments table (linked to message)
                CREATE TABLE IF NOT EXISTS attachments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id INTEGER NOT NULL,
                    file_path TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    file_size INTEGER,
                    FOREIGN KEY (message_id) REFERENCES messages(id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_messages_conversation
                    ON messages(conversation_id);
                CREATE INDEX IF NOT EXISTS idx_messages_type
                    ON messages(message_type);
                CREATE INDEX IF NOT EXISTS idx_tool_calls_message
                    ON tool_calls(message_id);
                CREATE INDEX IF NOT EXISTS idx_attachments_message
                    ON attachments(message_id);
                CREATE INDEX IF NOT EXISTS idx_conversations_session
                    ON conversations(session_id);
                CREATE INDEX IF NOT EXISTS idx_conversations_updated
                    ON conversations(updated_at DESC);

                -- FTS5 virtual table for full-text search
                CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                    message_id UNINDEXED,
                    conversation_id UNINDEXED,
                    role,
                    content,
                    timestamp UNINDEXED,
                    tokenize = 'porter unicode61'
                );

                -- Triggers to keep FTS index in sync with messages table
                CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
                    INSERT INTO messages_fts(message_id, conversation_id, role, content, timestamp)
                    VALUES (new.id, new.conversation_id, new.role, new.content, new.timestamp);
                END;

                CREATE TRIGGER IF NOT EXISTS messages_ad AFTER DELETE ON messages BEGIN
                    DELETE FROM messages_fts WHERE message_id = old.id;
                END;

                CREATE TRIGGER IF NOT EXISTS messages_au AFTER UPDATE ON messages BEGIN
                    UPDATE messages_fts
                    SET role = new.role, content = new.content
                    WHERE message_id = old.id;
                END;
            """)

            # Set schema version
            cursor = conn.execute("SELECT version FROM schema_version")
            result = cursor.fetchone()

            if result is None:
                # Fresh database, set version
                conn.execute(
                    "INSERT INTO schema_version (version) VALUES (?)",
                    (self.SCHEMA_VERSION,),
                )

    def create_conversation(
        self,
        model: str,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Create a new conversation session.

        Args:
            model: Model name (e.g., "gpt-4o", "claude-3-5-sonnet")
            session_id: Optional custom session ID (default: auto-generated UUID)
            metadata: Optional metadata dict to store with conversation

        Returns:
            Session ID for the new conversation

        Raises:
            DatabaseError: If conversation creation fails

        Example:
            >>> db = ConversationDatabase()
            >>> session_id = db.create_conversation("gpt-4o")
            >>> isinstance(session_id, str)
            True
        """
        session_id = session_id or str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        metadata_json = json.dumps(metadata or {})

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO conversations (id, session_id, model, created_at, updated_at, metadata) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (session_id, session_id, model, now, now, metadata_json),
                )
            return session_id
        except sqlite3.IntegrityError as e:
            raise DatabaseError(f"Session ID already exists: {session_id}") from e
        except Exception as e:
            raise DatabaseError(f"Failed to create conversation: {e}") from e

    def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tokens: int | None = None,
        message_type: str | None = None,
    ) -> int:
        """Save a message to a conversation.

        Args:
            session_id: Conversation session ID
            role: Message role ("system", "user", "assistant")
            content: Message content
            tokens: Optional token count for this message
            message_type: Message type for UI reconstruction
                         ("user", "assistant", "system", "tool_call", "tool_result")
                         Defaults to role if not specified.

        Returns:
            The ID of the inserted message

        Raises:
            ConversationNotFoundError: If session_id doesn't exist
            DatabaseError: If save operation fails

        Example:
            >>> db = ConversationDatabase()
            >>> session_id = db.create_conversation("gpt-4o")
            >>> msg_id = db.save_message(session_id, "user", "Hello!", 5)
            >>> msg_id > 0
            True
        """
        now = datetime.utcnow().isoformat()
        # Default message_type to role if not specified
        msg_type = message_type or role

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if conversation exists
                cursor = conn.execute(
                    "SELECT id FROM conversations WHERE session_id = ?", (session_id,)
                )
                if cursor.fetchone() is None:
                    raise ConversationNotFoundError(
                        f"Conversation not found: {session_id}"
                    )

                # Insert message with message_type
                cursor = conn.execute(
                    "INSERT INTO messages (conversation_id, message_type, role, content, tokens, timestamp) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (session_id, msg_type, role, content, tokens, now),
                )
                message_id = cursor.lastrowid
                if message_id is None:
                    raise DatabaseError("Failed to get inserted message ID")

                # Update conversation updated_at
                conn.execute(
                    "UPDATE conversations SET updated_at = ? WHERE session_id = ?",
                    (now, session_id),
                )

                return message_id
        except ConversationNotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to save message: {e}") from e

    def save_tool_call(
        self,
        message_id: int,
        tool_name: str,
        arguments: dict[str, Any],
        status: str = "pending",
        result: str | None = None,
    ) -> int:
        """Save a tool call linked to a message.

        Args:
            message_id: ID of the parent message
            tool_name: Name of the tool being called
            arguments: Tool arguments as a dictionary
            status: Execution status (pending, executing, success, error, denied)
            result: Optional result text

        Returns:
            The ID of the inserted tool call

        Raises:
            DatabaseError: If save operation fails
        """
        now = datetime.utcnow().isoformat()

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "INSERT INTO tool_calls (message_id, tool_name, arguments, status, result, timestamp) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (message_id, tool_name, json.dumps(arguments), status, result, now),
                )
                tool_call_id = cursor.lastrowid
                if tool_call_id is None:
                    raise DatabaseError("Failed to get inserted tool call ID")
                return tool_call_id
        except Exception as e:
            raise DatabaseError(f"Failed to save tool call: {e}") from e

    def update_tool_call(
        self,
        tool_call_id: int,
        status: str,
        result: str | None = None,
    ) -> None:
        """Update a tool call's status and result.

        Args:
            tool_call_id: ID of the tool call to update
            status: New execution status
            result: Optional result text
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE tool_calls SET status = ?, result = ? WHERE id = ?",
                    (status, result, tool_call_id),
                )
        except Exception as e:
            raise DatabaseError(f"Failed to update tool call: {e}") from e

    def save_attachment(
        self,
        message_id: int,
        file_path: str,
        file_type: str,
        mime_type: str,
        file_size: int | None = None,
    ) -> int:
        """Save an attachment linked to a message.

        Args:
            message_id: ID of the parent message
            file_path: Path to the attached file
            file_type: Type classification (image, code, document, data, unknown)
            mime_type: MIME type of the file
            file_size: Optional file size in bytes

        Returns:
            The ID of the inserted attachment

        Raises:
            DatabaseError: If save operation fails
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "INSERT INTO attachments (message_id, file_path, file_type, mime_type, file_size) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (message_id, file_path, file_type, mime_type, file_size),
                )
                attachment_id = cursor.lastrowid
                if attachment_id is None:
                    raise DatabaseError("Failed to get inserted attachment ID")
                return attachment_id
        except Exception as e:
            raise DatabaseError(f"Failed to save attachment: {e}") from e

    def load_conversation(self, session_id: str) -> list[dict[str, Any]]:
        """Load all messages for a conversation.

        Args:
            session_id: Conversation session ID

        Returns:
            List of message dicts with keys: id, role, content, tokens, timestamp, message_type

        Raises:
            ConversationNotFoundError: If session_id doesn't exist
            DatabaseError: If load operation fails

        Example:
            >>> db = ConversationDatabase()
            >>> session_id = db.create_conversation("gpt-4o")
            >>> db.save_message(session_id, "user", "Hello!", 5)
            >>> messages = db.load_conversation(session_id)
            >>> len(messages)
            1
            >>> messages[0]["role"]
            'user'
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Check if conversation exists
                cursor = conn.execute(
                    "SELECT id FROM conversations WHERE session_id = ?", (session_id,)
                )
                if cursor.fetchone() is None:
                    raise ConversationNotFoundError(
                        f"Conversation not found: {session_id}"
                    )

                # Load messages with message_type
                cursor = conn.execute(
                    "SELECT id, role, content, tokens, timestamp, message_type FROM messages "
                    "WHERE conversation_id = ? ORDER BY id",
                    (session_id,),
                )
                return [dict(row) for row in cursor.fetchall()]
        except ConversationNotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to load conversation: {e}") from e

    def load_conversation_full(self, session_id: str) -> list[dict[str, Any]]:
        """Load all messages with tool calls and attachments for UI reconstruction.

        Args:
            session_id: Conversation session ID

        Returns:
            List of message dicts with keys: id, role, content, tokens, timestamp,
            message_type, tool_calls (list), attachments (list)

        Raises:
            ConversationNotFoundError: If session_id doesn't exist
            DatabaseError: If load operation fails
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Check if conversation exists
                cursor = conn.execute(
                    "SELECT id FROM conversations WHERE session_id = ?", (session_id,)
                )
                if cursor.fetchone() is None:
                    raise ConversationNotFoundError(
                        f"Conversation not found: {session_id}"
                    )

                # Load messages
                cursor = conn.execute(
                    "SELECT id, role, content, tokens, timestamp, message_type FROM messages "
                    "WHERE conversation_id = ? ORDER BY id",
                    (session_id,),
                )
                messages = [dict(row) for row in cursor.fetchall()]

                # Load tool calls and attachments for each message
                for msg in messages:
                    msg_id = msg["id"]

                    # Load tool calls
                    cursor = conn.execute(
                        "SELECT id, tool_name, arguments, status, result, timestamp "
                        "FROM tool_calls WHERE message_id = ? ORDER BY id",
                        (msg_id,),
                    )
                    tool_calls = []
                    for row in cursor.fetchall():
                        tc = dict(row)
                        # Parse JSON arguments
                        tc["arguments"] = json.loads(tc["arguments"])
                        tool_calls.append(tc)
                    msg["tool_calls"] = tool_calls

                    # Load attachments
                    cursor = conn.execute(
                        "SELECT id, file_path, file_type, mime_type, file_size "
                        "FROM attachments WHERE message_id = ? ORDER BY id",
                        (msg_id,),
                    )
                    msg["attachments"] = [dict(row) for row in cursor.fetchall()]

                return messages
        except ConversationNotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to load conversation: {e}") from e

    def save_summary(self, session_id: str, summary: str) -> None:
        """Save or update conversation summary.

        Args:
            session_id: Conversation session ID
            summary: Summary text to save

        Raises:
            ConversationNotFoundError: If session_id doesn't exist
            DatabaseError: If save operation fails

        Example:
            >>> db = ConversationDatabase()
            >>> session_id = db.create_conversation("gpt-4o")
            >>> db.save_summary(session_id, "Summary of conversation")
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if conversation exists
                cursor = conn.execute(
                    "SELECT id FROM conversations WHERE session_id = ?", (session_id,)
                )
                if cursor.fetchone() is None:
                    raise ConversationNotFoundError(
                        f"Conversation not found: {session_id}"
                    )

                # Update summary
                conn.execute(
                    "UPDATE conversations SET summary = ?, updated_at = ? WHERE session_id = ?",
                    (summary, datetime.utcnow().isoformat(), session_id),
                )
        except ConversationNotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to save summary: {e}") from e

    def load_summary(self, session_id: str) -> str | None:
        """Load conversation summary.

        Args:
            session_id: Conversation session ID

        Returns:
            Summary text if exists, None otherwise

        Raises:
            ConversationNotFoundError: If session_id doesn't exist
            DatabaseError: If load operation fails

        Example:
            >>> db = ConversationDatabase()
            >>> session_id = db.create_conversation("gpt-4o")
            >>> db.save_summary(session_id, "Summary text")
            >>> summary = db.load_summary(session_id)
            >>> summary
            'Summary text'
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT summary FROM conversations WHERE session_id = ?",
                    (session_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise ConversationNotFoundError(
                        f"Conversation not found: {session_id}"
                    )
                summary: str | None = row[0]
                return summary
        except ConversationNotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to load summary: {e}") from e

    def search_messages(
        self,
        query: str,
        limit: int = 20,
        model_filter: str | None = None,
        after_date: str | None = None,
        before_date: str | None = None,
    ) -> list[dict[str, Any]]:
        """Full-text search across all conversation messages.

        Uses SQLite FTS5 for efficient searching with BM25 ranking.
        Supports FTS5 query syntax including phrase queries, boolean operators,
        and prefix matching.

        Args:
            query: FTS5 search query (e.g., "bug", "auth*", '"exact phrase"')
            limit: Maximum number of results to return (default: 20)
            model_filter: Filter results by model name (default: None)
            after_date: Filter results after this date (ISO format, default: None)
            before_date: Filter results before this date (ISO format, default: None)

        Returns:
            List of message dicts with keys: id, conversation_id, session_id,
            model, role, content, timestamp, snippet, rank

        Raises:
            DatabaseError: If search operation fails

        Example:
            >>> db = ConversationDatabase()
            >>> session_id = db.create_conversation("gpt-4o")
            >>> db.save_message(session_id, "user", "authentication bug", 3)
            >>> results = db.search_messages("auth*")
            >>> len(results) >= 1
            True
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                sql = """
                    SELECT
                        m.id,
                        m.conversation_id,
                        c.session_id,
                        c.model,
                        m.role,
                        m.content,
                        m.timestamp,
                        snippet(messages_fts, 3, '<mark>', '</mark>', '...', 30) as snippet,
                        bm25(messages_fts) as rank
                    FROM messages_fts
                    JOIN messages m ON messages_fts.message_id = m.id
                    JOIN conversations c ON m.conversation_id = c.session_id
                    WHERE messages_fts MATCH ?
                """

                params: list[Any] = [query]

                if model_filter:
                    sql += " AND c.model = ?"
                    params.append(model_filter)

                if after_date:
                    sql += " AND c.created_at >= ?"
                    params.append(after_date)

                if before_date:
                    sql += " AND c.created_at <= ?"
                    params.append(before_date)

                sql += " ORDER BY rank LIMIT ?"
                params.append(limit)

                cursor = conn.execute(sql, params)
                return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            raise DatabaseError(f"Search failed: {e}") from e

    def get_message_context(
        self, message_id: int, context_size: int = 2
    ) -> list[dict[str, Any]]:
        """Get surrounding messages for context around a specific message.

        Args:
            message_id: ID of the message to get context for
            context_size: Number of messages before and after (default: 2)

        Returns:
            List of message dicts with keys: id, role, content, timestamp
            Returns empty list if message not found

        Raises:
            DatabaseError: If context retrieval fails

        Example:
            >>> db = ConversationDatabase()
            >>> session_id = db.create_conversation("gpt-4o")
            >>> msg_id = db.save_message(session_id, "user", "Hello", 1)
            >>> db.save_message(session_id, "assistant", "Hi there", 2)
            >>> context = db.get_message_context(msg_id, context_size=1)
            >>> len(context) >= 1
            True
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Get the target message's conversation
                target = conn.execute(
                    "SELECT conversation_id, id FROM messages WHERE id = ?",
                    (message_id,),
                ).fetchone()

                if not target:
                    return []

                # Use a window query to get N messages before and after the target
                # This correctly handles non-contiguous IDs within a conversation
                cursor = conn.execute(
                    """
                    WITH ranked_messages AS (
                        SELECT
                            id,
                            role,
                            content,
                            timestamp,
                            ROW_NUMBER() OVER (ORDER BY id) as rn
                        FROM messages
                        WHERE conversation_id = ?
                    ),
                    target_msg AS (
                        SELECT rn FROM ranked_messages WHERE id = ?
                    )
                    SELECT id, role, content, timestamp
                    FROM ranked_messages
                    WHERE rn BETWEEN (SELECT rn FROM target_msg) - ?
                                 AND (SELECT rn FROM target_msg) + ?
                    ORDER BY rn
                    """,
                    (
                        target["conversation_id"],
                        message_id,
                        context_size,
                        context_size,
                    ),
                )

                return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            raise DatabaseError(f"Failed to get message context: {e}") from e

    def list_conversations(
        self, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        """List recent conversations with metadata.

        Args:
            limit: Maximum number of conversations to return (default: 50)
            offset: Number of conversations to skip (default: 0)

        Returns:
            List of conversation dicts with keys: session_id, model, created_at,
            updated_at, message_count, metadata

        Raises:
            DatabaseError: If list operation fails

        Example:
            >>> db = ConversationDatabase()
            >>> db.create_conversation("gpt-4o")
            >>> conversations = db.list_conversations(limit=10)
            >>> len(conversations) >= 1
            True
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT
                        c.session_id,
                        c.model,
                        c.created_at,
                        c.updated_at,
                        c.metadata,
                        COUNT(m.id) as message_count
                    FROM conversations c
                    LEFT JOIN messages m ON c.session_id = m.conversation_id
                    GROUP BY c.session_id
                    ORDER BY c.updated_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                )
                conversations = []
                for row in cursor.fetchall():
                    conv = dict(row)
                    # Parse metadata JSON
                    conv["metadata"] = json.loads(conv["metadata"])
                    conversations.append(conv)
                return conversations
        except Exception as e:
            raise DatabaseError(f"Failed to list conversations: {e}") from e

    def search_conversations(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        """Search conversations using FTS5 full-text search.

        Searches through message content and returns matching conversations
        ordered by relevance (FTS5 rank) and recency.

        Supports partial word matching by automatically adding wildcards.

        Args:
            query: Search query string (supports partial matching)
            limit: Maximum number of conversations to return (default: 50)

        Returns:
            List of conversation dicts with keys: session_id, model, created_at,
            updated_at, message_count, metadata, rank (search relevance score)

        Raises:
            DatabaseError: If search operation fails

        Example:
            >>> db = ConversationDatabase()
            >>> db.create_conversation("gpt-4o")
            >>> db.save_message(session_id, "user", "Python tutorial", 5)
            >>> results = db.search_conversations("Pyth")  # Partial match
            >>> len(results) >= 1
            True
        """
        try:
            # Convert query to support partial matching with wildcards
            # Split on whitespace and add * suffix to each term for prefix matching
            if query.strip():
                terms = query.strip().split()
                fts_query = " ".join(f"{term}*" for term in terms)
            else:
                fts_query = query

            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT
                        c.session_id,
                        c.model,
                        c.created_at,
                        c.updated_at,
                        c.metadata,
                        COUNT(DISTINCT m.id) as message_count
                    FROM messages_fts
                    JOIN messages m ON messages_fts.message_id = m.id
                    JOIN conversations c ON m.conversation_id = c.session_id
                    WHERE messages_fts MATCH ?
                    GROUP BY c.session_id
                    ORDER BY c.updated_at DESC
                    LIMIT ?
                    """,
                    (fts_query, limit),
                )
                conversations = []
                for row in cursor.fetchall():
                    conv = dict(row)
                    # Parse metadata JSON
                    conv["metadata"] = json.loads(conv["metadata"])
                    conversations.append(conv)
                return conversations
        except Exception as e:
            raise DatabaseError(f"Failed to search conversations: {e}") from e

    def get_conversation_metadata(self, session_id: str) -> dict[str, Any]:
        """Get metadata for a specific conversation.

        Args:
            session_id: Conversation session ID

        Returns:
            Dict with keys: session_id, model, created_at, updated_at,
            message_count, metadata

        Raises:
            ConversationNotFoundError: If session_id doesn't exist
            DatabaseError: If operation fails

        Example:
            >>> db = ConversationDatabase()
            >>> session_id = db.create_conversation("gpt-4o")
            >>> meta = db.get_conversation_metadata(session_id)
            >>> meta["model"]
            'gpt-4o'
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    """
                    SELECT
                        c.session_id,
                        c.model,
                        c.created_at,
                        c.updated_at,
                        c.metadata,
                        COUNT(m.id) as message_count
                    FROM conversations c
                    LEFT JOIN messages m ON c.session_id = m.conversation_id
                    WHERE c.session_id = ?
                    GROUP BY c.session_id
                    """,
                    (session_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise ConversationNotFoundError(
                        f"Conversation not found: {session_id}"
                    )

                result = dict(row)
                result["metadata"] = json.loads(result["metadata"])
                return result
        except ConversationNotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to get conversation metadata: {e}") from e

    def update_conversation_metadata(
        self, session_id: str, metadata: dict[str, Any]
    ) -> None:
        """Update metadata for a specific conversation.

        Args:
            session_id: Conversation session ID
            metadata: Metadata dict to update (merged with existing metadata)

        Raises:
            ConversationNotFoundError: If session_id doesn't exist
            DatabaseError: If update operation fails

        Example:
            >>> db = ConversationDatabase()
            >>> session_id = db.create_conversation("gpt-4o")
            >>> db.update_conversation_metadata(session_id, {"title": "My Chat"})
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # First check if conversation exists
                cursor = conn.execute(
                    "SELECT metadata FROM conversations WHERE session_id = ?",
                    (session_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    raise ConversationNotFoundError(
                        f"Conversation not found: {session_id}"
                    )

                # Merge with existing metadata
                existing_metadata = json.loads(row[0])
                existing_metadata.update(metadata)
                metadata_json = json.dumps(existing_metadata)

                # Update metadata and updated_at timestamp
                now = datetime.utcnow().isoformat()
                conn.execute(
                    "UPDATE conversations SET metadata = ?, updated_at = ? WHERE session_id = ?",
                    (metadata_json, now, session_id),
                )
        except ConversationNotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to update conversation metadata: {e}") from e

    def delete_conversation(self, session_id: str) -> None:
        """Delete a conversation and all its messages.

        Args:
            session_id: Conversation session ID

        Raises:
            ConversationNotFoundError: If session_id doesn't exist
            DatabaseError: If delete operation fails

        Example:
            >>> db = ConversationDatabase()
            >>> session_id = db.create_conversation("gpt-4o")
            >>> db.delete_conversation(session_id)
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Enable foreign keys for CASCADE delete
                conn.execute("PRAGMA foreign_keys=ON")
                cursor = conn.execute(
                    "DELETE FROM conversations WHERE session_id = ?", (session_id,)
                )
                if cursor.rowcount == 0:
                    raise ConversationNotFoundError(
                        f"Conversation not found: {session_id}"
                    )
        except ConversationNotFoundError:
            raise
        except Exception as e:
            raise DatabaseError(f"Failed to delete conversation: {e}") from e

    def delete_conversations_older_than(self, days: int) -> int:
        """Delete conversations older than specified number of days.

        Args:
            days: Delete conversations with updated_at older than this many days

        Returns:
            Number of conversations deleted

        Raises:
            DatabaseError: If delete operation fails

        Example:
            >>> db = ConversationDatabase()
            >>> # Delete conversations older than 30 days
            >>> deleted_count = db.delete_conversations_older_than(30)
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Enable foreign keys for CASCADE delete
                conn.execute("PRAGMA foreign_keys=ON")
                cursor = conn.execute(
                    """
                    DELETE FROM conversations
                    WHERE updated_at < datetime('now', '-' || ? || ' days')
                    """,
                    (days,),
                )
                return cursor.rowcount
        except Exception as e:
            raise DatabaseError(
                f"Failed to delete conversations older than {days} days: {e}"
            ) from e

    def clear_all_conversations(self) -> int:
        """Delete all conversations and messages.

        Returns:
            Number of conversations deleted

        Raises:
            DatabaseError: If clear operation fails

        Example:
            >>> db = ConversationDatabase()
            >>> db.create_conversation("gpt-4o")
            >>> count = db.clear_all_conversations()
            >>> count >= 1
            True
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Enable foreign keys for CASCADE delete
                conn.execute("PRAGMA foreign_keys=ON")
                cursor = conn.execute("DELETE FROM conversations")
                return cursor.rowcount
        except Exception as e:
            raise DatabaseError(f"Failed to clear conversations: {e}") from e

    def get_stats(self) -> dict[str, Any]:
        """Get database statistics.

        Returns:
            Dict with keys: total_conversations, total_messages, db_size_bytes,
            oldest_conversation, newest_conversation

        Raises:
            DatabaseError: If stats retrieval fails

        Example:
            >>> db = ConversationDatabase()
            >>> stats = db.get_stats()
            >>> "total_conversations" in stats
            True
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Get counts
                cursor = conn.execute("SELECT COUNT(*) as count FROM conversations")
                total_conversations = cursor.fetchone()["count"]

                cursor = conn.execute("SELECT COUNT(*) as count FROM messages")
                total_messages = cursor.fetchone()["count"]

                # Get date range
                cursor = conn.execute(
                    "SELECT MIN(created_at) as oldest, MAX(created_at) as newest "
                    "FROM conversations"
                )
                row = cursor.fetchone()
                oldest = row["oldest"]
                newest = row["newest"]

                # Get database file size
                db_size = self.db_path.stat().st_size if self.db_path.exists() else 0

                return {
                    "total_conversations": total_conversations,
                    "total_messages": total_messages,
                    "db_size_bytes": db_size,
                    "oldest_conversation": oldest,
                    "newest_conversation": newest,
                }
        except Exception as e:
            raise DatabaseError(f"Failed to get stats: {e}") from e

    def __enter__(self) -> ConversationDatabase:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        # No cleanup needed (connections auto-close)
        pass
