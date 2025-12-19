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
        context_providers: list[Any] | None = None,
        base_prompt: str | None = None,
        include_tool_docs: bool = True,
        include_env_context: bool = True,
        include_git_context: bool = True,
        auto_append_tools: bool = True,
    ) -> None:
        """Initialize conversation service.

        Args:
            model: LangChain chat model for AI interactions
            conversation: Conversation history manager
            tool_registry: Optional tool registry for function calling
            config: Optional Consoul configuration (uses default if None)
            context_providers: Optional list of context providers for dynamic context
            base_prompt: Base system prompt (before context injection)
            include_tool_docs: Include tool documentation in system prompt
            include_env_context: Include OS/shell/directory info
            include_git_context: Include git repository info
            auto_append_tools: Auto-append tool docs if no marker present
        """
        self.model = model
        self.conversation = conversation
        self.tool_registry = tool_registry
        self.config = config
        self.context_providers = context_providers or []
        self.base_prompt = base_prompt
        self.include_tool_docs = include_tool_docs
        self.include_env_context = include_env_context
        self.include_git_context = include_git_context
        self.auto_append_tools = auto_append_tools
        self.executor = ThreadPoolExecutor(max_workers=1)

    @classmethod
    def from_config(
        cls,
        config: ConsoulConfig | None = None,
        custom_system_prompt: str | None = None,
        include_tool_docs: bool = True,
        include_env_context: bool = True,
        include_git_context: bool = True,
        auto_append_tools: bool = True,
        approval_provider: Any | None = None,
        context_providers: list[Any] | None = None,
    ) -> ConversationService:
        """Create ConversationService from configuration.

        Factory method that initializes model, conversation history, and
        tool registry from config. Provides convenient instantiation without
        manually creating dependencies.

        Args:
            config: Optional Consoul configuration (loads default if None)
            custom_system_prompt: Custom system prompt (overrides profile prompt)
            include_tool_docs: Include tool documentation in system prompt (default: True)
            include_env_context: Include OS/shell/directory info (default: True)
            include_git_context: Include git repository info (default: True)
            auto_append_tools: Auto-append tool docs if no marker present (default: True)
            approval_provider: Optional approval provider for tool execution
            context_providers: List of ContextProvider implementations for dynamic context injection

        Returns:
            Initialized ConversationService ready for use

        Example - Default behavior (CLI/TUI):
            >>> service = ConversationService.from_config()

        Example - SDK with custom prompt, tools but no docs:
            >>> service = ConversationService.from_config(
            ...     custom_system_prompt="My AI assistant",
            ...     include_tool_docs=False,  # Tools enabled, not documented
            ... )

        Example - Full SDK control:
            >>> service = ConversationService.from_config(
            ...     custom_system_prompt="Clean prompt",
            ...     include_tool_docs=False,
            ...     include_env_context=False,
            ...     include_git_context=False,
            ... )
        """
        # Import here to avoid circular dependencies
        from consoul.ai import ConversationHistory, get_chat_model

        if config is None:
            from consoul.config import load_config

            config = load_config()

        # Initialize AI model
        model_config = config.get_current_model_config()
        model = get_chat_model(model_config, config=config)

        # Get conversation config from profile (TUI) or use defaults (SDK)
        # SDK uses ConsoulCoreConfig (no profiles), TUI uses ConsoulTuiConfig (has profiles)
        persist = True  # Default for SDK
        db_path = None  # Default for SDK

        # Check if config has profiles (TUI mode)
        if hasattr(config, "profiles") and hasattr(config, "active_profile"):
            # TUI mode - get config from active profile
            active_profile = config.profiles[config.active_profile]
            conv_config = active_profile.conversation
            persist = conv_config.persist
            db_path = conv_config.db_path

        # Initialize conversation history
        conversation = ConversationHistory(
            model_name=config.current_model,
            model=model,
            persist=persist,
            db_path=db_path,
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

            # Create tool registry with config and approval provider
            tool_registry = ToolRegistry(
                config.tools, approval_provider=approval_provider
            )

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

        # Build and add system prompt if configured
        # For SDK: custom_system_prompt or None (no profile)
        # For TUI: custom_system_prompt or profile's system_prompt
        profile_system_prompt = None
        if hasattr(config, "profiles") and hasattr(config, "active_profile"):
            active_profile = config.profiles[config.active_profile]
            profile_system_prompt = active_profile.system_prompt

        base_prompt = custom_system_prompt or profile_system_prompt

        # For static prompts (no context providers), build once at initialization
        # For dynamic prompts (with providers), build on first message
        if base_prompt and not context_providers:
            # Apply controlled injections to custom or profile prompt
            from consoul.ai.prompt_builder import build_enhanced_system_prompt

            # Only pass tool_registry if user wants tool docs
            registry_for_prompt = tool_registry if include_tool_docs else None

            system_prompt = build_enhanced_system_prompt(
                base_prompt=base_prompt,
                tool_registry=registry_for_prompt,
                include_env_context=include_env_context,
                include_git_context=include_git_context,
                auto_append_tools=auto_append_tools,
            )

            if system_prompt:
                conversation.add_system_message(system_prompt)

        return cls(
            model=model,
            conversation=conversation,
            tool_registry=tool_registry,
            config=config,
            context_providers=context_providers,
            base_prompt=base_prompt,
            include_tool_docs=include_tool_docs,
            include_env_context=include_env_context,
            include_git_context=include_git_context,
            auto_append_tools=auto_append_tools,
        )

    def _build_dynamic_system_prompt(
        self, query: str | None = None, conversation_id: str | None = None
    ) -> str | None:
        """Build system prompt with dynamic context from providers.

        Called per-message to inject fresh, query-aware context.

        Args:
            query: Current user query (for query-aware context)
            conversation_id: Conversation ID (for stateful context)

        Returns:
            Enhanced system prompt with dynamic context, or None if no prompt
        """
        if not self.base_prompt:
            return None

        # Collect context from providers
        dynamic_context: dict[str, str] = {}
        if self.context_providers:
            for provider in self.context_providers:
                try:
                    # Pass query and conversation_id for dynamic context
                    provider_context = provider.get_context(
                        query=query, conversation_id=conversation_id
                    )
                    dynamic_context.update(provider_context)
                except Exception as e:
                    # Log but don't fail - partial context is acceptable
                    import logging

                    logging.warning(
                        f"Context provider {provider.__class__.__name__} failed: {e}"
                    )

        # Build enhanced system prompt with provider context
        from consoul.ai.prompt_builder import build_enhanced_system_prompt

        # Only pass tool_registry if user wants tool docs
        registry_for_prompt = self.tool_registry if self.include_tool_docs else None

        system_prompt = build_enhanced_system_prompt(
            base_prompt=self.base_prompt,
            tool_registry=registry_for_prompt,
            include_env_context=self.include_env_context,
            include_git_context=self.include_git_context,
            auto_append_tools=self.auto_append_tools,
            context_sections=dynamic_context if dynamic_context else None,
        )

        return system_prompt

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
        # Update system prompt with dynamic context from providers
        if self.context_providers:
            conversation_id = getattr(self.conversation, "conversation_id", None)
            enhanced_prompt = self._build_dynamic_system_prompt(
                query=content, conversation_id=conversation_id
            )
            if enhanced_prompt:
                self.conversation.add_system_message(enhanced_prompt)

        # Prepare user message with attachments
        message_content = self._prepare_user_message(content, attachments)

        # Add user message to conversation with persistence
        # Use add_user_message_async() instead of direct append to ensure DB persistence
        if isinstance(message_content, str):
            # Simple text message
            await self.conversation.add_user_message_async(message_content)
        else:
            # Complex content (multimodal) - use direct append + manual persistence
            from langchain_core.messages import HumanMessage

            # Ensure conversation is created in DB before persisting multimodal message
            # This matches the logic in add_user_message_async() (history.py:705-716)
            if (
                self.conversation.persist
                and self.conversation._db
                and not self.conversation._conversation_created
            ):
                import asyncio

                loop = asyncio.get_event_loop()
                self.conversation.session_id = await loop.run_in_executor(
                    None,
                    self.conversation._db.create_conversation,
                    self.conversation.model_name,
                )
                self.conversation._conversation_created = True

                # Store any pending metadata
                if self.conversation._pending_metadata:
                    await loop.run_in_executor(
                        None,
                        self.conversation._db.update_conversation_metadata,
                        self.conversation.session_id,
                        self.conversation._pending_metadata,
                    )
                    self.conversation._pending_metadata.clear()

                # Persist any existing system messages
                from langchain_core.messages import SystemMessage

                for msg in self.conversation.messages:
                    if isinstance(msg, SystemMessage):
                        await loop.run_in_executor(
                            None,
                            self.conversation._persist_message_sync,
                            msg,
                        )

            message = HumanMessage(content=message_content)  # type: ignore[arg-type]
            self.conversation.messages.append(message)
            # Persist multimodal message (conversation now guaranteed to be created)
            await self.conversation._persist_message(message)

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

        # Stream tokens from model using async streaming
        collected_chunks: list[Any] = []

        # Use async streaming API (no threads/queues needed)
        async for chunk in model_to_use.astream(messages):
            collected_chunks.append(chunk)

            # Stream content tokens
            if chunk.content:
                token = self._normalize_chunk_content(chunk.content)
                if token:
                    yield Token(content=token, cost=None)

        # Reconstruct final AIMessage with tool_calls and cost
        if collected_chunks:
            final_message = self._reconstruct_message(collected_chunks)

            # Add AI message to conversation history with persistence
            self.conversation.messages.append(final_message)
            # Persist assistant message to database
            await self.conversation._persist_message(final_message)

            # Handle tool calls if present
            if final_message.tool_calls and self.tool_registry:
                tool_results, any_executed = await self._execute_tool_calls(
                    final_message.tool_calls, on_tool_request
                )
                # Add tool results to conversation with persistence
                for result in tool_results:
                    self.conversation.messages.append(result)
                    # Persist each tool result message
                    await self.conversation._persist_message(result)

                # Only continue if tools were actually executed
                # (If all were rejected, don't recurse to avoid infinite loop)
                if any_executed:
                    # Stream next iteration with tool results
                    async for result_token in self._stream_response(on_tool_request):
                        yield result_token

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

        # Reconstruct tool_calls from tool_call_chunks or tool_calls
        tool_calls = []
        tool_calls_by_index: dict[int, dict[str, Any]] = {}

        # First, check if any chunks have complete tool_calls (some providers do this)
        for chunk in chunks:
            if (
                hasattr(chunk, "tool_calls")
                and chunk.tool_calls
                and isinstance(chunk.tool_calls, list)
            ):
                # Chunk has complete tool_calls - use them directly
                tool_calls.extend(chunk.tool_calls)

        # If no complete tool_calls, reconstruct from tool_call_chunks
        if not tool_calls:
            for chunk in chunks:
                if not hasattr(chunk, "tool_call_chunks") or not chunk.tool_call_chunks:
                    continue

                # Ensure tool_call_chunks is iterable (not a Mock or other non-iterable)
                try:
                    tool_call_chunks = list(chunk.tool_call_chunks)
                except (TypeError, AttributeError):
                    continue

                for tc in tool_call_chunks:
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

            # Parse tool call args from chunks
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

        # Extract usage_metadata (must be dict or None for Pydantic validation)
        usage_metadata = None
        for chunk in reversed(chunks[-5:]):
            if (
                hasattr(chunk, "usage_metadata")
                and chunk.usage_metadata
                and isinstance(chunk.usage_metadata, dict)
            ):
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
    ) -> tuple[list[Any], bool]:
        """Execute tool calls with approval workflow.

        Handles tool approval, execution in thread pool, and result persistence.
        Extracted from ConsoulApp tool execution logic (lines 3087-3906).

        Args:
            tool_calls: Parsed tool calls from AI response
            on_tool_request: Optional callback for tool execution approval

        Returns:
            Tuple of (ToolMessage results, any_executed flag)
            any_executed is False if all tools were rejected
        """
        from langchain_core.messages import ToolMessage

        from consoul.sdk.models import ToolRequest

        if not self.tool_registry:
            return [], False

        tool_messages = []
        any_executed = False

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

            # Always call approval callback if provided (for tool call data collection)
            # The callback handles checking needs_approval() and showing modals only when needed
            # This enables BALANCED/TRUSTING policies to auto-approve SAFE/whitelisted commands
            approved = True  # Default to approved if no callback

            if on_tool_request:
                # Create tool request for callback
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
                any_executed = True
            except Exception as e:
                logger.error(f"Tool execution error: {e}", exc_info=True)
                result = f"Tool execution failed: {e}"
                tool_messages.append(ToolMessage(content=result, tool_call_id=tool_id))

        return tool_messages, any_executed

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
