"""ConversationService - TUI-agnostic conversation management.

This service encapsulates all business logic for AI conversations, streaming
responses, tool execution, and message management. Extracted from ConsoulApp
to enable headless SDK usage without Textual/TUI dependencies.

Example:
    >>> service = ConversationService.from_config()
    >>> async for token in service.send_message("Hello!"):
    ...     print(token.content, end="", flush=True)
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import TYPE_CHECKING, Any

from consoul.sdk.models import ConversationStats, Token, ToolRequest
from consoul.sdk.protocols import ToolExecutionCallback

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from langchain_core.language_models.chat_models import BaseChatModel

    from consoul.ai.history import ConversationHistory
    from consoul.ai.tools import ToolRegistry
    from consoul.config import ConsoulConfig
    from consoul.sdk.models import Attachment

# Type alias for tool approval callbacks
# Must be async callable or protocol implementation with async on_tool_request method
ToolApprovalCallback = ToolExecutionCallback | Callable[[ToolRequest], Awaitable[bool]]

logger = logging.getLogger(__name__)


class ConversationService:
    """Service layer for AI conversation management.

    Provides headless conversation interface with streaming responses,
    tool execution approval, multimodal message support, and cost tracking.
    Completely decoupled from TUI/CLI to enable SDK-first architecture.

    Attributes:
        model: LangChain chat model for AI interactions
        conversation: Conversation history manager
        tool_registry: Optional tool registry for function calling
        config: Consoul configuration
        executor: Thread pool for non-blocking operations

    Example - Basic usage:
        >>> service = ConversationService.from_config()
        >>> async for token in service.send_message("Hello!"):
        ...     print(token.content, end="", flush=True)

    Example - With tool approval:
        >>> async def approve_tool(request: ToolRequest) -> bool:
        ...     return request.risk_level == "safe"
        >>> async for token in service.send_message(
        ...     "List files",
        ...     on_tool_request=approve_tool
        ... ):
        ...     print(token, end="")

    Example - With attachments:
        >>> attachments = [
        ...     Attachment(path="screenshot.png", type="image"),
        ...     Attachment(path="code.py", type="code")
        ... ]
        >>> async for token in service.send_message(
        ...     "Analyze this",
        ...     attachments=attachments
        ... ):
        ...     print(token, end="")
    """

    def __init__(
        self,
        model: BaseChatModel,
        conversation: ConversationHistory,
        tool_registry: ToolRegistry | None = None,
        config: ConsoulConfig | None = None,
    ) -> None:
        """Initialize conversation service.

        Args:
            model: LangChain chat model for AI interactions
            conversation: Conversation history manager
            tool_registry: Optional tool registry for function calling
            config: Optional Consoul configuration (uses default if None)
        """
        self.model = model
        self.conversation = conversation
        self.tool_registry = tool_registry
        self.config = config
        self.executor = ThreadPoolExecutor(max_workers=1)

    @classmethod
    def from_config(cls, config: ConsoulConfig | None = None) -> ConversationService:
        """Create ConversationService from configuration.

        Factory method that initializes model, conversation history, and
        tool registry from config. Provides convenient instantiation without
        manually creating dependencies.

        Args:
            config: Optional Consoul configuration (loads default if None)

        Returns:
            Initialized ConversationService ready for use

        Example:
            >>> service = ConversationService.from_config()
            >>> # Or with custom config:
            >>> from consoul.config import ConsoulConfig
            >>> config = ConsoulConfig.load()
            >>> service = ConversationService.from_config(config)
        """
        # Import here to avoid circular dependencies
        from consoul.ai import ConversationHistory, get_chat_model

        if config is None:
            from consoul.config import load_config

            config = load_config()

        # Initialize AI model
        model_config = config.get_current_model_config()
        model = get_chat_model(model_config, config=config)

        # Get active profile conversation config
        active_profile = config.profiles[config.active_profile]
        conv_config = active_profile.conversation

        # Initialize conversation history
        conversation = ConversationHistory(
            model_name=config.current_model,
            model=model,
            persist=conv_config.persist,
            db_path=conv_config.db_path,
        )

        # Initialize tool registry if tools are enabled
        tool_registry = None
        if config.tools and config.tools.enabled:
            from consoul.ai.tools import ToolRegistry
            from consoul.ai.tools.catalog import TOOL_CATALOG
            from consoul.ai.tools.implementations import (
                set_analyze_images_config,
                set_bash_config,
                set_code_search_config,
                set_file_edit_config,
                set_find_references_config,
                set_grep_search_config,
                set_read_config,
                set_read_url_config,
                set_web_search_config,
                set_wikipedia_config,
            )

            # Configure tools with profile settings
            if config.tools.bash:
                set_bash_config(config.tools.bash)
            if config.tools.read:
                set_read_config(config.tools.read)
            if config.tools.grep_search:
                set_grep_search_config(config.tools.grep_search)
            if config.tools.code_search:
                set_code_search_config(config.tools.code_search)
            if config.tools.find_references:
                set_find_references_config(config.tools.find_references)
            if config.tools.web_search:
                set_web_search_config(config.tools.web_search)
            if config.tools.wikipedia:
                set_wikipedia_config(config.tools.wikipedia)
            if config.tools.read_url:
                set_read_url_config(config.tools.read_url)
            if config.tools.file_edit:
                set_file_edit_config(config.tools.file_edit)
            if config.tools.image_analysis:
                set_analyze_images_config(config.tools.image_analysis)

            # Create tool registry with config
            tool_registry = ToolRegistry(config.tools)

            # Get all available tools from catalog
            for tool, risk_level, categories in TOOL_CATALOG.values():
                # Determine if tool should be enabled
                enabled = True  # Default to enabled
                if config.tools.allowed_tools:
                    enabled = tool.name in config.tools.allowed_tools
                elif config.tools.risk_filter:
                    enabled = risk_level.value in config.tools.risk_filter

                # Convert categories to string tags
                tags_list = [cat.value for cat in categories]

                tool_registry.register(
                    tool,
                    risk_level=risk_level,
                    tags=tags_list,
                    enabled=enabled,
                )

            # Bind tools to model if registry has enabled tools
            enabled_tools = [
                meta.tool for meta in tool_registry.list_tools(enabled_only=True)
            ]
            if enabled_tools:
                model = model.bind_tools(enabled_tools)  # type: ignore[assignment]

        return cls(
            model=model,
            conversation=conversation,
            tool_registry=tool_registry,
            config=config,
        )

    async def send_message(
        self,
        content: str,
        *,
        attachments: list[Attachment] | None = None,
        on_tool_request: ToolApprovalCallback | None = None,
    ) -> AsyncIterator[Token]:
        """Send message and stream AI response.

        Main entry point for SDK consumers. Handles message preparation,
        streaming response, tool execution approval, and cost tracking.

        Args:
            content: User message text
            attachments: Optional file attachments (images, code files, etc.)
            on_tool_request: Optional callback for tool execution approval.
                Can be either:
                - An async callable: async def(request: ToolRequest) -> bool
                - A ToolExecutionCallback protocol implementation

        Yields:
            Token: Streaming tokens with content, cost, and metadata

        Example - Simple streaming:
            >>> async for token in service.send_message("Hello!"):
            ...     print(token.content, end="", flush=True)

        Example - With async function approval:
            >>> async def approve(request: ToolRequest) -> bool:
            ...     return request.risk_level != "dangerous"
            >>> async for token in service.send_message(
            ...     "Run command",
            ...     on_tool_request=approve
            ... ):
            ...     print(token, end="")

        Example - With protocol implementation:
            >>> class MyApprover:
            ...     async def on_tool_request(self, request: ToolRequest) -> bool:
            ...         return request.risk_level == "safe"
            >>> approver = MyApprover()
            >>> async for token in service.send_message(
            ...     "Run command",
            ...     on_tool_request=approver
            ... ):
            ...     print(token, end="")

        Example - With image attachment:
            >>> from consoul.sdk import Attachment
            >>> attachments = [Attachment(path="image.png", type="image")]
            >>> async for token in service.send_message(
            ...     "What's in this image?",
            ...     attachments=attachments
            ... ):
            ...     print(token, end="")
        """
        from langchain_core.messages import HumanMessage

        # Prepare user message with attachments
        message_content = self._prepare_user_message(content, attachments)

        # Create HumanMessage and add to conversation
        message = HumanMessage(content=message_content)  # type: ignore[arg-type]
        self.conversation.messages.append(message)

        # Stream response
        async for token in self._stream_response(on_tool_request):
            yield token

    def _model_supports_vision(self) -> bool:
        """Check if current model supports vision/multimodal input.

        Detects vision capabilities based on model name patterns for:
        - Anthropic Claude 3+
        - OpenAI GPT-4/5 (excludes GPT-3.5)
        - Google Gemini
        - Ollama vision models (qwen2-vl, qwen3-vl, llava, bakllava)

        Returns:
            True if model supports vision, False otherwise
        """
        if not self.config or not self.config.current_model:
            return False

        model_name = self.config.current_model.lower()

        vision_patterns = [
            "claude-3",
            "claude-4",  # Anthropic Claude 3+
            "gpt-4",
            "gpt-5",  # OpenAI GPT-4V/5
            "gemini",  # Google Gemini
            "qwen2-vl",
            "qwen3-vl",  # Ollama qwen vision
            "llava",
            "bakllava",  # Ollama llava models
        ]

        return any(pattern in model_name for pattern in vision_patterns)

    def _prepare_user_message(
        self,
        content: str,
        attachments: list[Attachment] | None = None,
    ) -> str | list[dict[str, Any]]:
        """Prepare user message with optional attachments.

        Handles file attachment processing and multimodal message creation.
        Extracted from ConsoulApp._handle_user_message (lines 1597-1799).

        Args:
            content: User message text
            attachments: Optional file attachments

        Returns:
            Simple string message or multimodal message structure
        """
        if not attachments:
            return content

        # Separate images from text files
        image_attachments = [a for a in attachments if a.type == "image"]
        text_attachments = [
            a for a in attachments if a.type in {"code", "document", "data"}
        ]

        # Handle text file attachments - prepend to message
        final_message = content
        if text_attachments:
            text_content_parts = []
            for attachment in text_attachments:
                try:
                    path = Path(attachment.path)
                    # Limit to 10KB per file
                    if path.stat().st_size > 10 * 1024:
                        logger.warning(
                            f"Skipping large file {path.name} ({path.stat().st_size} bytes)"
                        )
                        continue

                    file_content = path.read_text(encoding="utf-8")
                    text_content_parts.append(
                        f"--- {path.name} ---\n{file_content}\n--- End of {path.name} ---"
                    )
                except Exception as e:
                    logger.error(f"Failed to read file {attachment.path}: {e}")
                    continue

            # Prepend file contents to message
            if text_content_parts:
                final_message = "\n\n".join(text_content_parts) + "\n\n" + content

        # Handle image attachments - create multimodal message if model supports vision
        if image_attachments and self._model_supports_vision():
            image_paths = [Path(a.path) for a in image_attachments]
            try:
                return self._create_multimodal_message(final_message, image_paths)
            except Exception as e:
                logger.error(f"Failed to create multimodal message: {e}")
                # Fall back to text-only message
                return final_message

        return final_message

    def _create_multimodal_message(
        self,
        text: str,
        image_paths: list[Path],
    ) -> list[dict[str, Any]]:
        """Create multimodal message with text and images.

        Encodes images to base64 and formats for provider-specific schemas.
        Extracted from ConsoulApp._create_multimodal_message (lines 1275-1435).

        Args:
            text: Message text content
            image_paths: Paths to image files

        Returns:
            Multimodal message with text and image content blocks
        """
        import base64
        import mimetypes

        from consoul.ai.multimodal import format_vision_message

        # Load and encode images
        encoded_images: list[dict[str, Any]] = []
        for path in image_paths:
            # Detect MIME type
            mime_type, _ = mimetypes.guess_type(str(path))
            if not mime_type or not mime_type.startswith("image/"):
                raise ValueError(f"Invalid MIME type for {path.name}: {mime_type}")

            # Read and encode image
            with open(path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            encoded_images.append(
                {"path": str(path), "data": image_data, "mime_type": mime_type}
            )

        # Get current provider from model config
        if not self.config:
            raise ValueError("Config not available for multimodal message creation")

        model_config = self.config.get_current_model_config()
        provider = model_config.provider

        # Format message for the provider
        message = format_vision_message(provider, text, encoded_images)
        return message.content  # type: ignore[return-value]

    async def _stream_response(
        self,
        on_tool_request: ToolApprovalCallback | None = None,
    ) -> AsyncIterator[Token]:
        """Stream AI response with tool execution support.

        Main streaming logic with token queueing, tool call detection,
        and context window management. Extracted from ConsoulApp._stream_ai_response
        (lines 1836-2740).

        Args:
            on_tool_request: Optional callback for tool execution approval

        Yields:
            Token: Streaming tokens with content, cost, and metadata
        """

        # Get trimmed messages for context window
        messages = await self._get_trimmed_messages()

        # Check if last message is multimodal
        has_multimodal = self._has_multimodal_content(messages)

        # Use model without tools for multimodal messages
        model_to_use = self.model
        if has_multimodal and hasattr(self.model, "bound"):
            # Unwrap RunnableBinding from bind_tools()
            model_to_use = self.model.bound

        # Stream tokens from model in background thread
        token_queue: asyncio.Queue[str | None] = asyncio.Queue()
        exception_queue: asyncio.Queue[Exception | None] = asyncio.Queue()
        collected_chunks: list[Any] = []
        event_loop = asyncio.get_running_loop()

        def _stream_producer() -> None:
            """Background thread to stream tokens from model."""
            try:
                for chunk in model_to_use.stream(messages):
                    collected_chunks.append(chunk)
                    token = self._normalize_chunk_content(chunk.content)
                    if token:
                        asyncio.run_coroutine_threadsafe(
                            token_queue.put(token), event_loop
                        )
            except Exception as e:
                asyncio.run_coroutine_threadsafe(exception_queue.put(e), event_loop)
            finally:
                asyncio.run_coroutine_threadsafe(token_queue.put(None), event_loop)

        # Start streaming in background
        import threading

        thread = threading.Thread(target=_stream_producer, daemon=True)
        thread.start()

        # Yield tokens to caller
        while True:
            try:
                token_str = await asyncio.wait_for(token_queue.get(), timeout=0.1)
                if token_str is None:
                    break
                yield Token(content=token_str, cost=None)
            except asyncio.TimeoutError:
                # Check for exceptions
                try:
                    exc = exception_queue.get_nowait()
                    if exc:
                        raise exc
                except asyncio.QueueEmpty:
                    pass

        # Check for exceptions after streaming
        try:
            exc = await asyncio.wait_for(exception_queue.get(), timeout=0.1)
            if exc:
                raise exc
        except asyncio.TimeoutError:
            pass

        # Reconstruct final AIMessage with tool_calls and cost
        if collected_chunks:
            final_message = self._reconstruct_message(collected_chunks)

            # Add AI message to conversation history
            self.conversation.messages.append(final_message)

            # Handle tool calls if present
            if final_message.tool_calls and self.tool_registry:
                tool_results = await self._execute_tool_calls(
                    final_message.tool_calls, on_tool_request
                )
                # Add tool results to conversation
                for result in tool_results:
                    self.conversation.messages.append(result)

                # Stream next iteration with tool results
                async for token in self._stream_response(on_tool_request):
                    yield token

    async def _get_trimmed_messages(self) -> list[Any]:
        """Get context-window-aware trimmed messages.

        Returns:
            List of messages trimmed to fit context window
        """
        if not self.config:
            # No config, return all messages
            return list(self.conversation.messages)

        # Get model's context window size
        context_size = self.conversation.max_tokens

        # Reserve tokens for response
        model_config = self.config.get_current_model_config()
        default_reserve = 4096
        if model_config.max_tokens:
            reserve_tokens = min(model_config.max_tokens, context_size // 2)
        else:
            reserve_tokens = min(default_reserve, context_size // 2)

        # Ensure reserve_tokens leaves room for input
        reserve_tokens = min(reserve_tokens, context_size - 512)

        # Check for multimodal content (skip token counting if present)
        has_multimodal = any(
            hasattr(msg, "content")
            and isinstance(msg.content, list)
            and any(
                isinstance(block, dict) and block.get("type") in ["image", "image_url"]
                for block in msg.content
            )
            for msg in self.conversation.messages[-10:]
        )

        if has_multimodal:
            # Just take last 10 messages for multimodal conversations
            return list(self.conversation.messages[-10:])

        # Get trimmed messages in executor to avoid blocking
        loop = asyncio.get_event_loop()
        messages_result: list[Any] = []
        try:
            messages_result = await asyncio.wait_for(
                loop.run_in_executor(
                    self.executor,
                    self.conversation.get_trimmed_messages,
                    reserve_tokens,
                ),
                timeout=10.0,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "Token counting timed out, using last 20 messages as fallback"
            )
            messages_result = list(self.conversation.messages[-20:])
        except Exception as e:
            logger.error(f"Error trimming messages: {e}")
            messages_result = list(self.conversation.messages[-20:])

        return messages_result

    def _has_multimodal_content(self, messages: list[Any]) -> bool:
        """Check if last message contains multimodal content.

        Args:
            messages: List of messages to check

        Returns:
            True if last message has image content blocks
        """
        if not messages:
            return False

        last_msg = messages[-1]
        if not hasattr(last_msg, "content") or not isinstance(last_msg.content, list):
            return False

        return any(
            isinstance(block, dict) and block.get("type") in ["image", "image_url"]
            for block in last_msg.content
        )

    def _normalize_chunk_content(self, content: str | list[Any] | None) -> str:
        """Normalize chunk content to string.

        LangChain chunks can have content as str, list of blocks, or None.

        Args:
            content: Chunk content from AIMessage

        Returns:
            Normalized string content
        """
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            # Extract text from block list (Anthropic/Gemini format)
            text_parts: list[str] = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text" and "text" in block:
                        text_parts.append(block["text"])
                elif isinstance(block, str):
                    text_parts.append(block)
            return "".join(text_parts)
        return str(content)

    def _reconstruct_message(self, chunks: list[Any]) -> Any:  # AIMessage
        """Reconstruct final AIMessage from chunks.

        Combines content, tool_calls, and usage_metadata from all chunks.

        Args:
            chunks: List of AIMessage chunks from streaming

        Returns:
            Complete AIMessage with reconstructed content and tool_calls
        """
        import json

        from langchain_core.messages import AIMessage

        # Reconstruct content
        content_parts = []
        for chunk in chunks:
            normalized = self._normalize_chunk_content(chunk.content)
            if normalized:
                content_parts.append(normalized)

        # Reconstruct tool_calls from tool_call_chunks
        tool_calls_by_index: dict[int, dict[str, Any]] = {}
        for chunk in chunks:
            if not hasattr(chunk, "tool_call_chunks") or not chunk.tool_call_chunks:
                continue

            for tc in chunk.tool_call_chunks:
                if not isinstance(tc, dict):
                    continue

                tc_index = tc.get("index", 0)
                if tc_index not in tool_calls_by_index:
                    tool_calls_by_index[tc_index] = {
                        "name": "",
                        "args": "",
                        "id": None,
                        "type": "tool_call",
                    }

                if tc.get("name"):
                    tool_calls_by_index[tc_index]["name"] = tc["name"]
                if tc.get("id"):
                    tool_calls_by_index[tc_index]["id"] = tc["id"]
                if tc.get("args"):
                    tool_calls_by_index[tc_index]["args"] += tc["args"]

        # Parse tool call args
        tool_calls = []
        for tc_data in tool_calls_by_index.values():
            args_str = tc_data["args"]
            try:
                parsed_args = json.loads(args_str) if args_str else {}
                tool_calls.append(
                    {
                        "name": tc_data["name"],
                        "args": parsed_args,
                        "id": tc_data["id"],
                        "type": "tool_call",
                    }
                )
            except json.JSONDecodeError as e:
                logger.warning(
                    f"Failed to parse tool call args: {args_str!r}, error: {e}"
                )
                tool_calls.append(
                    {
                        "name": tc_data["name"],
                        "args": {},
                        "id": tc_data["id"],
                        "type": "tool_call",
                    }
                )

        # Extract usage_metadata
        usage_metadata = None
        for chunk in reversed(chunks[-5:]):
            if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                usage_metadata = chunk.usage_metadata
                break

        return AIMessage(
            content="".join(content_parts),
            tool_calls=tool_calls if tool_calls else [],
            usage_metadata=usage_metadata,
        )

    def _calculate_cost(self, usage_metadata: dict[str, Any]) -> dict[str, Any]:
        """Calculate cost from usage metadata.

        Args:
            usage_metadata: Usage metadata dict with input_tokens, output_tokens

        Returns:
            Cost breakdown dictionary
        """
        from consoul.pricing import calculate_cost

        if not self.config:
            return {"total_cost": 0.0}

        input_tokens = usage_metadata.get("input_tokens", 0)
        output_tokens = usage_metadata.get("output_tokens", 0)

        return calculate_cost(
            model_name=self.config.current_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    async def _execute_tool_calls(
        self,
        tool_calls: list[dict[str, Any]],
        on_tool_request: ToolApprovalCallback | None = None,
    ) -> list[Any]:
        """Execute tool calls with approval workflow.

        Handles tool approval, execution in thread pool, and result persistence.
        Extracted from ConsoulApp tool execution logic (lines 3087-3906).

        Args:
            tool_calls: Parsed tool calls from AI response
            on_tool_request: Optional callback for tool execution approval

        Returns:
            List of ToolMessage results
        """
        from langchain_core.messages import ToolMessage

        from consoul.sdk.models import ToolRequest

        if not self.tool_registry:
            return []

        tool_messages = []

        for tool_call in tool_calls:
            tool_name = tool_call.get("name", "")
            tool_args = tool_call.get("args", {})
            tool_id = tool_call.get("id", "")

            # Find tool metadata
            tool_metadata = None
            for meta in self.tool_registry.list_tools(enabled_only=True):
                if meta.tool.name == tool_name:
                    tool_metadata = meta
                    break

            if not tool_metadata:
                result = f"Unknown tool: {tool_name}"
                tool_messages.append(ToolMessage(content=result, tool_call_id=tool_id))
                continue

            # Request approval if callback provided
            if on_tool_request:
                request = ToolRequest(
                    id=tool_id,
                    name=tool_name,
                    arguments=tool_args,
                    risk_level=tool_metadata.risk_level.value,
                )

                try:
                    # Support both Protocol implementations and plain async callables
                    if hasattr(on_tool_request, "on_tool_request"):
                        # Protocol implementation with on_tool_request method
                        approved = await on_tool_request.on_tool_request(request)
                    else:
                        # Plain async callable
                        approved = await on_tool_request(request)

                    if not approved:
                        result = "Tool execution denied by user"
                        tool_messages.append(
                            ToolMessage(content=result, tool_call_id=tool_id)
                        )
                        continue
                except Exception as e:
                    logger.error(f"Tool approval callback failed: {e}")
                    result = f"Tool approval failed: {e}"
                    tool_messages.append(
                        ToolMessage(content=result, tool_call_id=tool_id)
                    )
                    continue

            # Execute tool in thread pool
            try:
                loop = asyncio.get_running_loop()
                result = await loop.run_in_executor(
                    self.executor, tool_metadata.tool.invoke, tool_args
                )
                tool_messages.append(
                    ToolMessage(content=str(result), tool_call_id=tool_id)
                )
            except Exception as e:
                logger.error(f"Tool execution error: {e}", exc_info=True)
                result = f"Tool execution failed: {e}"
                tool_messages.append(ToolMessage(content=result, tool_call_id=tool_id))

        return tool_messages

    def get_stats(self) -> ConversationStats:
        """Get conversation statistics.

        Returns:
            ConversationStats with message count, tokens, cost, and session ID

        Example:
            >>> stats = service.get_stats()
            >>> print(f"Messages: {stats.message_count}")
            >>> print(f"Cost: ${stats.total_cost:.4f}")
        """
        # Count tokens manually
        total_tokens = self.conversation.count_tokens()

        # For now, cost tracking is not implemented in the service layer
        # It would require tracking all usage_metadata from streaming responses
        total_cost = 0.0

        return ConversationStats(
            message_count=len(self.conversation.messages),
            total_tokens=total_tokens,
            total_cost=total_cost,
            session_id=self.conversation.session_id,
        )

    def get_history(self) -> list[Any]:
        """Get conversation message history.

        Returns:
            List of LangChain messages (HumanMessage, AIMessage, ToolMessage)

        Example:
            >>> history = service.get_history()
            >>> for msg in history:
            ...     print(f"{msg.type}: {msg.content}")
        """
        return self.conversation.messages

    def clear(self) -> None:
        """Clear conversation history.

        Resets message history and cost tracking. Useful for starting
        fresh conversations without creating new service instance.

        Example:
            >>> service.clear()
            >>> stats = service.get_stats()
            >>> assert stats.message_count == 0
        """
        self.conversation.clear()
