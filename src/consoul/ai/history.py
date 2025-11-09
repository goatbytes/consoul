"""Conversation history management with intelligent token-based trimming.

This module provides the ConversationHistory class for managing multi-turn
conversations with AI models. It handles message storage, token counting,
and intelligent trimming to fit within model context windows.

Key Features:
    - Stores conversation as LangChain BaseMessage objects
    - Automatic token counting per provider
    - Intelligent message trimming with system message preservation
    - Conversion between dict and LangChain message formats
    - Compatible with existing example code

Example:
    >>> history = ConversationHistory("gpt-4o")
    >>> history.add_system_message("You are a helpful assistant.")
    >>> history.add_user_message("Hello!")
    >>> history.add_assistant_message("Hi! How can I help you?")
    >>> print(f"Messages: {len(history)}, Tokens: {history.count_tokens()}")
    Messages: 3, Tokens: 28
    >>> trimmed = history.get_trimmed_messages(reserve_tokens=1000)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    trim_messages,
)

from consoul.ai.context import (
    count_message_tokens,
    create_token_counter,
    get_model_token_limit,
)

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel


def to_langchain_message(role: str, content: str) -> BaseMessage:
    """Convert role/content dict to LangChain BaseMessage.

    Args:
        role: Message role ("system", "user", "assistant", or "human", "ai")
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
    else:
        raise ValueError(
            f"Unknown message role: {role}. "
            f"Expected: 'system', 'user', 'assistant', 'human', or 'ai'"
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
    else:
        # Fallback for unknown message types
        role = message.type

    return {"role": role, "content": message.content}


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
    ):
        """Initialize conversation history.

        Args:
            model_name: Model identifier (e.g., "gpt-4o", "claude-3-5-sonnet")
            max_tokens: Optional override for context limit (uses model default if None)
            model: Optional LangChain model instance for provider-specific token counting
        """
        self.model_name = model_name
        self.max_tokens = max_tokens or get_model_token_limit(model_name)
        self.messages: list[BaseMessage] = []
        self._token_counter = create_token_counter(model_name, model)
        self._model = model

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
        self.messages.append(HumanMessage(content=content))

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
        self.messages.append(AIMessage(content=content))

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

        Args:
            reserve_tokens: Tokens to reserve for response (default 1000)
            strategy: Trimming strategy - "last" keeps recent messages (default)

        Returns:
            Trimmed list of messages that fit within token limit

        Example:
            >>> history = ConversationHistory("gpt-4o")
            >>> history.add_system_message("You are helpful.")
            >>> # ... add many messages ...
            >>> trimmed = history.get_trimmed_messages(reserve_tokens=1000)
            >>> # System message is always preserved
        """
        if not self.messages:
            return []

        # Calculate available tokens for conversation
        available_tokens = self.max_tokens - reserve_tokens

        # Use LangChain's trim_messages
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
            result: list[BaseMessage] = trimmed
            return result
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
