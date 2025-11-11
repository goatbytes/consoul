"""Conversation history management with intelligent token-based trimming.

This module provides the ConversationHistory class for managing multi-turn
conversations with AI models. It handles message storage, token counting,
and intelligent trimming to fit within model context windows.

Key Features:
    - Stores conversation as LangChain BaseMessage objects
    - Automatic token counting per provider
    - Intelligent message trimming with system message preservation
    - Conversion between dict and LangChain message formats
    - Optional SQLite persistence for conversation resumption
    - Compatible with existing example code

Example:
    >>> history = ConversationHistory("gpt-4o")
    >>> history.add_system_message("You are a helpful assistant.")
    >>> history.add_user_message("Hello!")
    >>> history.add_assistant_message("Hi! How can I help you?")
    >>> print(f"Messages: {len(history)}, Tokens: {history.count_tokens()}")
    Messages: 3, Tokens: 28
    >>> trimmed = history.get_trimmed_messages(reserve_tokens=1000)

    # With persistence
    >>> history = ConversationHistory("gpt-4o", persist=True)
    >>> print(f"Session: {history.session_id}")
    >>> # Later, resume the conversation
    >>> history2 = ConversationHistory("gpt-4o", persist=True, session_id=history.session_id)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
    trim_messages,
)

from consoul.ai.context import (
    count_message_tokens,
    create_token_counter,
    get_model_token_limit,
)

if TYPE_CHECKING:
    from pathlib import Path

    from langchain_core.language_models.chat_models import BaseChatModel

    from consoul.ai.database import ConversationDatabase
    from consoul.ai.summarization import ConversationSummarizer

logger = logging.getLogger(__name__)


def to_langchain_message(role: str, content: str) -> BaseMessage:
    """Convert role/content dict to LangChain BaseMessage.

    Args:
        role: Message role ("system", "user", "assistant", "tool", or "human", "ai")
        content: Message content

    Returns:
        Appropriate LangChain message object

    Raises:
        ValueError: If role is not recognized

    Example:
        >>> msg = to_langchain_message("user", "Hello!")
        >>> isinstance(msg, HumanMessage)
        True
    """
    role_lower = role.lower()

    if role_lower in ("system",):
        return SystemMessage(content=content)
    elif role_lower in ("user", "human"):
        return HumanMessage(content=content)
    elif role_lower in ("assistant", "ai"):
        return AIMessage(content=content)
    elif role_lower in ("tool",):
        # Note: ToolMessage requires tool_call_id, but we can't provide it here
        # This is primarily for persistence compatibility
        return ToolMessage(content=content, tool_call_id="unknown")
    else:
        raise ValueError(
            f"Unknown message role: {role}. "
            f"Expected: 'system', 'user', 'assistant', 'tool', 'human', or 'ai'"
        )


def to_dict_message(message: BaseMessage) -> dict[str, str]:
    """Convert LangChain BaseMessage to role/content dict.

    Args:
        message: LangChain message object

    Returns:
        Dict with 'role' and 'content' keys

    Example:
        >>> from langchain_core.messages import HumanMessage
        >>> msg = HumanMessage(content="Hello!")
        >>> to_dict_message(msg)
        {'role': 'user', 'content': 'Hello!'}
    """
    if isinstance(message, SystemMessage):
        role = "system"
    elif isinstance(message, HumanMessage):
        role = "user"
    elif isinstance(message, AIMessage):
        role = "assistant"
    elif isinstance(message, ToolMessage):
        role = "tool"
    else:
        # Fallback for unknown message types
        role = message.type

    # Convert content to string (handles list blocks from some providers)
    content = message.content
    if isinstance(content, list):
        # Extract text from list blocks
        text_parts = []
        for block in content:
            if isinstance(block, dict) and "text" in block:
                text_parts.append(str(block["text"]))
            elif isinstance(block, str):
                text_parts.append(block)
        content = "".join(text_parts)
    else:
        content = str(content)

    return {"role": role, "content": content}


class ConversationHistory:
    """Manages conversation history with intelligent token-based trimming.

    Stores messages as LangChain BaseMessage objects and provides utilities
    for token counting, message trimming, and format conversion. Ensures
    conversations stay within model context windows while preserving
    important context.

    Attributes:
        model_name: Model identifier for token counting
        max_tokens: Maximum tokens allowed in conversation
        messages: List of LangChain BaseMessage objects

    Example:
        >>> history = ConversationHistory("gpt-4o", max_tokens=4000)
        >>> history.add_system_message("You are helpful.")
        >>> history.add_user_message("Hi!")
        >>> history.add_assistant_message("Hello!")
        >>> len(history)
        3
        >>> history.count_tokens()
        24
    """

    def __init__(
        self,
        model_name: str,
        max_tokens: int | None = None,
        model: BaseChatModel | None = None,
        persist: bool = True,
        session_id: str | None = None,
        db_path: Path | str | None = None,
        summarize: bool = False,
        summarize_threshold: int = 20,
        keep_recent: int = 10,
        summary_model: BaseChatModel | None = None,
    ):
        """Initialize conversation history.

        Args:
            model_name: Model identifier (e.g., "gpt-4o", "claude-3-5-sonnet")
            max_tokens: Optional override for context limit (uses model default if None)
            model: Optional LangChain model instance for provider-specific token counting
            persist: Enable SQLite persistence (default: True)
            session_id: Optional session ID to resume existing conversation
            db_path: Optional custom database path (default: ~/.consoul/history.db)
            summarize: Enable conversation summarization for long conversations (default: False)
            summarize_threshold: Trigger summarization after N messages (default: 20)
            keep_recent: Keep last N messages verbatim when summarizing (default: 10)
            summary_model: Optional cheaper model for generating summaries (default: use main model)

        Example:
            >>> # In-memory (default)
            >>> history = ConversationHistory("gpt-4o")

            >>> # With persistence - new session
            >>> history = ConversationHistory("gpt-4o", persist=True)
            >>> session = history.session_id

            >>> # With persistence - resume session
            >>> history = ConversationHistory("gpt-4o", persist=True, session_id=session)

            >>> # With summarization for cost savings
            >>> history = ConversationHistory(
            ...     "gpt-4o",
            ...     model=chat_model,
            ...     summarize=True,
            ...     summarize_threshold=20
            ... )
        """
        self.model_name = model_name
        self.max_tokens = max_tokens or get_model_token_limit(model_name)
        self.messages: list[BaseMessage] = []
        self._token_counter = create_token_counter(model_name, model)
        self._model = model

        # Persistence setup
        self.persist = persist
        self.session_id = session_id
        self._db: ConversationDatabase | None = None
        self._db_path = db_path or "~/.consoul/history.db"
        self._conversation_created = False  # Track if DB conversation was created

        if persist:
            try:
                from consoul.ai.database import ConversationDatabase

                self._db = ConversationDatabase(self._db_path)

                if session_id:
                    # Resume existing conversation
                    self._load_from_db(session_id)
                    self._conversation_created = True
                # else: Defer conversation creation until first user message

            except Exception as e:
                # Graceful fallback to in-memory mode
                logger.warning(
                    f"Failed to initialize database persistence: {e}. "
                    "Falling back to in-memory mode."
                )
                self.persist = False
                self._db = None

        # Summarization setup
        self.summarize = summarize
        self.conversation_summary = ""
        self._summarizer: ConversationSummarizer | None = None

        if summarize:
            if not model:
                logger.warning(
                    "Summarization requires a model instance. "
                    "Summarization will be disabled."
                )
                self.summarize = False
            else:
                from consoul.ai.summarization import ConversationSummarizer

                self._summarizer = ConversationSummarizer(
                    llm=model,
                    threshold=summarize_threshold,
                    keep_recent=keep_recent,
                    summary_model=summary_model,
                )
                logger.info(
                    f"Initialized summarization: threshold={summarize_threshold}, "
                    f"keep_recent={keep_recent}"
                )

    def _load_from_db(self, session_id: str) -> None:
        """Load conversation from database.

        Args:
            session_id: Session ID to load

        Raises:
            ValueError: If session doesn't exist or database not initialized
        """
        if not self._db:
            raise ValueError("Database not initialized")

        try:
            messages_data = self._db.load_conversation(session_id)

            # Convert dict messages to LangChain BaseMessage objects
            for msg_data in messages_data:
                role = msg_data["role"]
                content = msg_data["content"]
                message = to_langchain_message(role, content)
                self.messages.append(message)

            # Load summary if it exists
            try:
                summary = self._db.load_summary(session_id)
                if summary:
                    self.conversation_summary = summary
                    logger.debug(f"Loaded summary: {len(summary)} chars")
            except Exception as e:
                logger.debug(f"No summary found or error loading summary: {e}")

            logger.info(
                f"Loaded {len(self.messages)} messages from session {session_id}"
            )

        except Exception as e:
            logger.error(f"Failed to load conversation from database: {e}")
            raise ValueError(f"Failed to load session {session_id}: {e}") from e

    def _persist_message(self, message: BaseMessage) -> None:
        """Persist a message to database.

        Args:
            message: Message to persist
        """
        if not self.persist or not self._db or not self.session_id:
            return

        try:
            # Get role from message
            role_map = {
                SystemMessage: "system",
                HumanMessage: "user",
                AIMessage: "assistant",
                ToolMessage: "tool",
            }
            role = role_map.get(type(message), message.type)

            # Count tokens for this message
            tokens = self._token_counter([message])

            # Save to database
            self._db.save_message(self.session_id, role, message.content, tokens)

        except Exception as e:
            # Don't fail the operation if persistence fails, just log
            logger.warning(f"Failed to persist message: {e}")

    def add_system_message(self, content: str) -> None:
        """Add or replace system message.

        System messages are always stored at position 0. If a system message
        already exists, it is replaced. Only one system message is supported.

        Args:
            content: System message content

        Example:
            >>> history = ConversationHistory("gpt-4o")
            >>> history.add_system_message("You are helpful.")
            >>> history.add_system_message("You are very helpful.")  # Replaces first
            >>> len(history)
            1
        """
        system_message = SystemMessage(content=content)

        # Replace existing system message if present
        if self.messages and isinstance(self.messages[0], SystemMessage):
            self.messages[0] = system_message
        else:
            # Insert at beginning
            self.messages.insert(0, system_message)

        # Persist if enabled
        self._persist_message(system_message)

    def add_user_message(self, content: str) -> None:
        """Add user message to conversation history.

        Args:
            content: User message content

        Example:
            >>> history = ConversationHistory("gpt-4o")
            >>> history.add_user_message("Hello!")
            >>> len(history)
            1
        """
        # Create conversation in DB on first user message if not already created
        if self.persist and self._db and not self._conversation_created:
            try:
                self.session_id = self._db.create_conversation(self.model_name)
                self._conversation_created = True
                logger.info(f"Created new conversation session: {self.session_id}")

                # Persist any existing system messages that were added before first user message
                for msg in self.messages:
                    if isinstance(msg, SystemMessage):
                        self._persist_message(msg)
            except Exception as e:
                logger.warning(f"Failed to create conversation in database: {e}")
                self.persist = False

        message = HumanMessage(content=content)
        self.messages.append(message)

        # Persist if enabled
        self._persist_message(message)

    def add_assistant_message(self, content: str) -> None:
        """Add assistant message to conversation history.

        Args:
            content: Assistant message content

        Example:
            >>> history = ConversationHistory("gpt-4o")
            >>> history.add_assistant_message("Hi there!")
            >>> len(history)
            1
        """
        message = AIMessage(content=content)
        self.messages.append(message)

        # Persist if enabled
        self._persist_message(message)

    def add_message(self, role: str, content: str) -> None:
        """Add message to history with specified role.

        Convenience method that routes to role-specific methods.

        Args:
            role: Message role ("system", "user", "assistant")
            content: Message content

        Example:
            >>> history = ConversationHistory("gpt-4o")
            >>> history.add_message("user", "Hello!")
            >>> history.add_message("assistant", "Hi!")
            >>> len(history)
            2
        """
        role_lower = role.lower()

        if role_lower == "system":
            self.add_system_message(content)
        elif role_lower in ("user", "human"):
            self.add_user_message(content)
        elif role_lower in ("assistant", "ai"):
            self.add_assistant_message(content)
        else:
            raise ValueError(f"Unknown role: {role}")

    def get_messages(self) -> list[BaseMessage]:
        """Get raw LangChain messages.

        Returns:
            List of LangChain BaseMessage objects

        Example:
            >>> history = ConversationHistory("gpt-4o")
            >>> history.add_user_message("Hi!")
            >>> messages = history.get_messages()
            >>> isinstance(messages[0], HumanMessage)
            True
        """
        return self.messages.copy()

    def get_messages_as_dicts(self) -> list[dict[str, str]]:
        """Get messages in dict format (compatible with examples).

        Returns:
            List of dicts with 'role' and 'content' keys

        Example:
            >>> history = ConversationHistory("gpt-4o")
            >>> history.add_user_message("Hello!")
            >>> history.get_messages_as_dicts()
            [{'role': 'user', 'content': 'Hello!'}]
        """
        return [to_dict_message(msg) for msg in self.messages]

    def get_trimmed_messages(
        self, reserve_tokens: int = 1000, strategy: str = "last"
    ) -> list[BaseMessage]:
        """Get messages trimmed to fit model's context window.

        Uses LangChain's trim_messages to intelligently trim the conversation
        while preserving the system message and ensuring valid message sequences.

        If summarization is enabled and the conversation exceeds the threshold,
        older messages are summarized and recent messages are kept verbatim,
        providing significant token savings while preserving context.

        Args:
            reserve_tokens: Tokens to reserve for response (default 1000)
            strategy: Trimming strategy - "last" keeps recent messages (default)

        Returns:
            Trimmed list of messages that fit within token limit.
            With summarization: [system_msg, summary_msg, recent_messages]
            Without: standard LangChain trim_messages result

        Raises:
            TokenLimitExceededError: If reserve_tokens >= max_tokens, preventing
                                    any messages from being sent.

        Example:
            >>> history = ConversationHistory("gpt-4o")
            >>> history.add_system_message("You are helpful.")
            >>> # ... add many messages ...
            >>> trimmed = history.get_trimmed_messages(reserve_tokens=1000)
            >>> # System message is always preserved

            >>> # With summarization enabled
            >>> history = ConversationHistory(
            ...     "gpt-4o",
            ...     model=chat_model,
            ...     summarize=True
            ... )
            >>> # ... add 30 messages ...
            >>> trimmed = history.get_trimmed_messages()
            >>> # Returns: [system, summary, last_10_messages] instead of 30
        """
        if not self.messages:
            return []

        # Calculate available tokens for conversation
        available_tokens = self.max_tokens - reserve_tokens

        # Guard against negative available_tokens (e.g., small models with default reserve)
        if available_tokens <= 0:
            from consoul.ai.exceptions import TokenLimitExceededError

            raise TokenLimitExceededError(
                f"Reserve tokens ({reserve_tokens}) exceeds model's context window "
                f"({self.max_tokens}). Cannot trim messages. "
                f"Try reducing reserve_tokens to at most {self.max_tokens - 1}.",
                current_tokens=reserve_tokens,
                max_tokens=self.max_tokens,
            )

        # Try summarization if enabled and threshold exceeded
        if (
            self.summarize
            and self._summarizer
            and self._summarizer.should_summarize(len(self.messages))
        ):
            try:
                from consoul.ai.summarization import SummarizationError

                # Separate system message if present
                messages_to_process = self.messages
                if messages_to_process and isinstance(
                    messages_to_process[0], SystemMessage
                ):
                    messages_to_process = messages_to_process[1:]

                # Determine which messages to summarize
                num_to_keep = self._summarizer.keep_recent
                if len(messages_to_process) > num_to_keep:
                    messages_to_summarize = messages_to_process[:-num_to_keep]

                    # Generate/update summary
                    logger.info(
                        f"Generating summary for {len(messages_to_summarize)} messages "
                        f"(keeping {num_to_keep} recent)"
                    )
                    self.conversation_summary = self._summarizer.create_summary(
                        messages_to_summarize, self.conversation_summary
                    )

                    # Persist summary to database if enabled
                    if self.persist and self._db and self.session_id:
                        try:
                            self._db.save_summary(
                                self.session_id, self.conversation_summary
                            )
                            logger.debug("Saved summary to database")
                        except Exception as e:
                            logger.warning(f"Failed to save summary to database: {e}")

                    # Build context with summary + recent messages
                    result = self._summarizer.get_summarized_context(
                        self.messages, self.conversation_summary
                    )

                    logger.info(
                        f"Summarization reduced {len(self.messages)} messages to {len(result)}"
                    )
                    return result

            except SummarizationError as e:
                # Log error but continue with standard trimming
                logger.warning(
                    f"Summarization failed, falling back to standard trimming: {e}"
                )
            except Exception as e:
                # Catch any unexpected errors
                logger.error(
                    f"Unexpected error during summarization: {e}", exc_info=True
                )

        # Standard LangChain trim_messages (no summarization or summarization failed)
        try:
            trimmed = trim_messages(
                self.messages,
                max_tokens=available_tokens,
                strategy=strategy,
                token_counter=self._token_counter,
                # Always preserve system message (first message if it exists)
                include_system=True,
                # Ensure conversation starts with user message (after system)
                start_on="human",
                # Don't split messages
                allow_partial=False,
            )
            trimmed_result: list[BaseMessage] = trimmed
            return trimmed_result
        except Exception:
            # Fallback: return all messages if trimming fails
            # (Better to send too much than lose context)
            return self.messages.copy()

    def count_tokens(self) -> int:
        """Count total tokens in current conversation history.

        Returns:
            Total number of tokens in all messages

        Example:
            >>> history = ConversationHistory("gpt-4o")
            >>> history.add_user_message("Hello!")
            >>> tokens = history.count_tokens()
            >>> tokens > 0
            True
        """
        if not self.messages:
            return 0

        return count_message_tokens(self.messages, self.model_name, self._model)

    def clear(self, preserve_system: bool = True) -> None:
        """Clear conversation history.

        Args:
            preserve_system: If True, keep the system message (default)

        Example:
            >>> history = ConversationHistory("gpt-4o")
            >>> history.add_system_message("You are helpful.")
            >>> history.add_user_message("Hi!")
            >>> history.clear(preserve_system=True)
            >>> len(history)
            1  # System message preserved
        """
        if (
            preserve_system
            and self.messages
            and isinstance(self.messages[0], SystemMessage)
        ):
            # Keep only the system message
            system_msg = self.messages[0]
            self.messages = [system_msg]
        else:
            # Clear all messages
            self.messages = []

    def __len__(self) -> int:
        """Return number of messages in history.

        Returns:
            Message count

        Example:
            >>> history = ConversationHistory("gpt-4o")
            >>> history.add_user_message("Hello!")
            >>> len(history)
            1
        """
        return len(self.messages)

    def __repr__(self) -> str:
        """Return string representation of conversation history.

        Returns:
            Repr string showing model, message count, and token count
        """
        return (
            f"ConversationHistory(model='{self.model_name}', "
            f"messages={len(self.messages)}, "
            f"tokens={self.count_tokens()}/{self.max_tokens})"
        )
