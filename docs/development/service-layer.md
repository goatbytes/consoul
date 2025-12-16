# Service Layer Development Guide

This guide explains when and how to work with Consoul's service layer - the headless SDK components that power both the TUI and backend integrations.

## What is the Service Layer?

The service layer (`src/consoul/sdk/services/`) contains business logic for AI conversations, tool execution, and model management. These services are:

- **Headless** - No UI dependencies (no Rich, Textual, Typer)
- **Async-first** - Designed for non-blocking operation
- **Protocol-based** - Uses callbacks for UI integration
- **Reusable** - Same code powers TUI, CLI, FastAPI, WebSocket, etc.

## Core Services

### ConversationService

**Purpose**: Manage AI conversations with streaming and tool execution

**File**: `src/consoul/sdk/services/conversation.py:42`

**Key Methods**:

- `from_config()` - Factory method to create from configuration
- `send_message()` - Send message and stream AI response
- `get_stats()` - Get conversation statistics
- `get_history()` - Get message history
- `clear()` - Clear conversation

**When to use**: Anytime you need AI chat functionality

**Example**:

```python
from consoul.sdk.services import ConversationService

# Initialize from config
service = ConversationService.from_config()

# Send message and stream response
async for token in service.send_message("Hello!"):
    print(token.content, end="", flush=True)
```

### ToolService

**Purpose**: Manage tool configuration, registration, and approval

**File**: `src/consoul/sdk/services/tool.py:30`

**Key Methods**:

- `from_config()` - Factory method to create from configuration
- `list_tools()` - List available tools
- `needs_approval()` - Check if tool needs approval
- `get_tools_count()` - Get total tool count

**When to use**: When working with tool management or approval policies

**Example**:

```python
from consoul.sdk.services import ToolService

# Initialize from config
service = ToolService.from_config(config)

# List enabled tools
tools = service.list_tools(enabled_only=True)
for tool in tools:
    print(f"{tool.name}: {tool.description}")

# Check if tool needs approval
if service.needs_approval("bash_execute", {"command": "ls"}):
    # Show approval modal
    pass
```

### ModelService

**Purpose**: Initialize, switch, and query AI models

**File**: `src/consoul/sdk/services/model.py:32`

**Key Methods**:

- `from_config()` - Factory method to create from configuration
- `get_model()` - Get current LangChain model
- `switch_model()` - Switch to different model
- `list_ollama_models()` - List local Ollama models
- `get_model_pricing()` - Get pricing for a model
- `get_model_capabilities()` - Check model capabilities

**When to use**: When working with model selection or switching

**Example**:

```python
from consoul.sdk.services import ModelService

# Initialize from config
service = ModelService.from_config(config)

# Get current model
model = service.get_model()

# Switch models
service.switch_model("claude-3-5-sonnet-20241022")

# Check capabilities
if service.supports_vision():
    # Send image attachment
    pass
```

## When to Add Code to Services

### ✅ Add to Services When:

1. **Business Logic** - AI conversation flow, tool execution logic
2. **State Management** - Conversation history, model state
3. **LangChain Integration** - Direct model/chain interaction
4. **Data Processing** - Message formatting, token counting
5. **Headless Operations** - Anything that doesn't require UI

**Example**: Adding message summarization

```python
# src/consoul/sdk/services/conversation.py

class ConversationService:
    async def summarize_conversation(self) -> str:
        """Generate summary of conversation history."""
        # GOOD: Business logic in service
        messages = self.conversation.messages
        summary_prompt = "Summarize this conversation in 2-3 sentences."

        # Use model to generate summary
        response = await self.model.ainvoke([
            *messages,
            {"role": "user", "content": summary_prompt}
        ])
        return response.content
```

### ❌ Don't Add to Services:

1. **UI Code** - Widgets, layouts, styling, colors
2. **User Input** - Keyboard handlers, command parsing
3. **Display Logic** - Formatting for terminal, Rich markup
4. **Framework-Specific** - Textual screens, Typer commands

**Example**: Message display (belongs in TUI)

```python
# BAD: Don't add this to ConversationService
from rich.console import Console  # UI dependency!

class ConversationService:
    def display_message(self, message: str):
        console = Console()
        console.print(f"[bold]{message}[/bold]")  # NO! UI in service

# GOOD: Keep in TUI layer
# src/consoul/tui/widgets/chat.py
from rich.text import Text

class ChatWidget(Widget):
    def display_message(self, message: str):
        # UI code belongs here
        self.text_display.update(Text(message, style="bold"))
```

## Extension Patterns

### Adding a New Service Method

**Pattern**: Add method to existing service for new functionality

**Example**: Add cost calculation to ConversationService

```python
# src/consoul/sdk/services/conversation.py

class ConversationService:
    async def get_conversation_cost(self) -> float:
        """Calculate total cost of conversation.

        Returns:
            Total cost in USD

        Example:
            >>> cost = await service.get_conversation_cost()
            >>> print(f"Total: ${cost:.4f}")
        """
        # Implementation using pricing module
        from consoul.pricing import calculate_cost

        total_cost = 0.0
        for message in self.conversation.messages:
            if hasattr(message, 'usage_metadata'):
                cost_info = calculate_cost(
                    self.config.current_model,
                    message.usage_metadata['input_tokens'],
                    message.usage_metadata['output_tokens']
                )
                total_cost += cost_info['total_cost']

        return total_cost
```

**Steps**:

1. Add method to service class
2. Write comprehensive docstring with example
3. Add unit test in `tests/sdk/services/`
4. Update API reference if public method
5. Consider adding to `get_stats()` if it's a statistic

### Creating a New Service

**Pattern**: Create new service when logical grouping changes

**When to create**:

- New major feature area (e.g., "AuditService" for logging)
- Clear separation of concerns
- Can be used independently

**Example**: Creating an AuditService

```python
# src/consoul/sdk/services/audit.py

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from consoul.config import ConsoulConfig

logger = logging.getLogger(__name__)

class AuditService:
    """Service layer for audit logging and event tracking.

    Tracks tool executions, model usage, and conversation events
    for compliance and analysis.

    Example:
        >>> service = AuditService.from_config(config)
        >>> await service.log_tool_execution("bash", {"command": "ls"}, "output")
    """

    def __init__(self, config: ConsoulConfig):
        """Initialize audit service.

        Args:
            config: Consoul configuration
        """
        self.config = config

    @classmethod
    def from_config(cls, config: ConsoulConfig) -> AuditService:
        """Create AuditService from configuration.

        Args:
            config: Consoul configuration

        Returns:
            Initialized AuditService

        Example:
            >>> from consoul.config import load_config
            >>> config = load_config()
            >>> service = AuditService.from_config(config)
        """
        return cls(config=config)

    async def log_tool_execution(
        self,
        tool_name: str,
        arguments: dict,
        result: str
    ) -> None:
        """Log tool execution event.

        Args:
            tool_name: Name of executed tool
            arguments: Tool arguments
            result: Tool execution result
        """
        # Implementation here
        pass
```

**Steps**:

1. Create `src/consoul/sdk/services/audit.py`
2. Implement service with `from_config()` factory
3. Add to `src/consoul/sdk/services/__init__.py`:
   ```python
   from consoul.sdk.services.audit import AuditService
   __all__ = ["ConversationService", "ToolService", "ModelService", "AuditService"]
   ```
4. Write unit tests in `tests/unit/sdk/services/test_audit.py`
5. Add to API reference docs
6. Update architecture docs

## Callback Protocols

Services use protocols for UI integration without coupling to specific UI frameworks.

### Defining a Protocol

**Pattern**: Define protocol in `src/consoul/sdk/protocols.py`

**Example**: Tool execution callback

```python
# src/consoul/sdk/protocols.py

from typing import Protocol
from consoul.sdk.models import ToolRequest

class ToolExecutionCallback(Protocol):
    """Protocol for tool execution approval.

    Implementations provide UI-specific approval mechanisms:
    - TUI: Modal dialog with approval buttons
    - CLI: Auto-approve or deny based on policy
    - WebSocket: Send approval request to client
    """

    async def on_tool_request(self, request: ToolRequest) -> bool:
        """Called when tool execution needs approval.

        Args:
            request: Tool execution request with name, args, risk level

        Returns:
            True if approved, False if denied

        Example:
            >>> class MyApprover:
            ...     async def on_tool_request(self, request: ToolRequest) -> bool:
            ...         return request.risk_level == "safe"
        """
        ...
```

### Using a Protocol in Services

**Pattern**: Accept protocol as optional parameter

```python
# src/consoul/sdk/services/conversation.py

from consoul.sdk.protocols import ToolExecutionCallback

class ConversationService:
    async def send_message(
        self,
        content: str,
        on_tool_request: ToolExecutionCallback | None = None
    ) -> AsyncIterator[Token]:
        """Send message with optional tool approval callback.

        Args:
            content: Message text
            on_tool_request: Optional callback for tool approval
        """
        # Call protocol method when tool execution needed
        if tool_call and on_tool_request:
            approved = await on_tool_request.on_tool_request(request)
            if not approved:
                # Skip tool execution
                continue
```

### Implementing a Protocol

**Pattern**: Implement in UI layer (TUI, CLI, or backend)

**TUI Example**:

```python
# src/consoul/tui/providers/approval.py

from consoul.sdk.protocols import ToolExecutionCallback
from consoul.sdk.models import ToolRequest

class TuiApprovalProvider:
    """Textual modal-based approval provider."""

    def __init__(self, app):
        self.app = app

    async def on_tool_request(self, request: ToolRequest) -> bool:
        """Show approval modal and wait for user decision."""
        # Show Textual modal
        modal = ApprovalModal(request)
        result = await self.app.push_screen(modal)
        return result  # True/False from modal
```

**WebSocket Example**:

```python
# examples/fastapi_websocket_server.py

from consoul.sdk.protocols import ToolExecutionCallback
from consoul.sdk.models import ToolRequest

class WebSocketApprovalProvider:
    """WebSocket-based approval provider."""

    def __init__(self, websocket):
        self.websocket = websocket
        self._pending = {}

    async def on_tool_request(self, request: ToolRequest) -> bool:
        """Send approval request via WebSocket."""
        # Send to client
        await self.websocket.send_json({
            "type": "tool_request",
            "id": request.id,
            "name": request.name,
            "risk_level": request.risk_level
        })

        # Wait for response
        response = await self.websocket.receive_json()
        return response.get("approved", False)
```

## Data Models

Services use data classes for structured data exchange with UI.

### Existing Models

**Location**: `src/consoul/sdk/models.py`

**Key Models**:

- `Token` - Streaming token with content and cost
- `ToolRequest` - Tool execution request for approval
- `ConversationStats` - Conversation statistics
- `Attachment` - File attachment metadata
- `ModelInfo` - Model metadata and capabilities
- `PricingInfo` - Model pricing information

### Creating New Models

**Pattern**: Add to `src/consoul/sdk/models.py`

**Example**: Adding a model capability query result

```python
# src/consoul/sdk/models.py

from dataclasses import dataclass

@dataclass
class ModelCapabilities:
    """Model capability information.

    Attributes:
        supports_vision: Model can process images
        supports_tools: Model can call functions
        supports_reasoning: Model has reasoning capabilities
        supports_streaming: Model supports token streaming
        supports_json_mode: Model has JSON output mode
        supports_caching: Model supports prompt caching
        supports_batch: Model supports batch API

    Example:
        >>> caps = service.get_model_capabilities("gpt-4o")
        >>> if caps.supports_vision and caps.supports_tools:
        ...     print("Model supports both vision and tools")
    """
    supports_vision: bool
    supports_tools: bool
    supports_reasoning: bool = False
    supports_streaming: bool = True
    supports_json_mode: bool = False
    supports_caching: bool = False
    supports_batch: bool = False
```

## Testing Services

### Unit Testing Pattern

**Pattern**: Mock dependencies, test service logic in isolation

**Example**: Testing ConversationService

```python
# tests/unit/sdk/services/test_conversation.py

import pytest
from unittest.mock import AsyncMock, Mock, patch
from consoul.sdk.services import ConversationService
from consoul.sdk.models import Token

@pytest.fixture
def mock_model():
    """Mock LangChain model."""
    model = Mock()
    model.stream = Mock(return_value=iter([
        Mock(content="Hello", tool_calls=[]),
        Mock(content=" world", tool_calls=[])
    ]))
    return model

@pytest.fixture
def mock_conversation():
    """Mock conversation history."""
    conversation = Mock()
    conversation.messages = []
    conversation.add_user_message_async = AsyncMock()
    conversation._persist_message = AsyncMock()
    return conversation

@pytest.mark.asyncio
async def test_send_message_streaming(mock_model, mock_conversation):
    """Test message streaming yields tokens."""
    # Create service with mocks
    service = ConversationService(
        model=mock_model,
        conversation=mock_conversation,
        tool_registry=None
    )

    # Send message
    tokens = []
    async for token in service.send_message("Hi"):
        tokens.append(token.content)

    # Verify
    assert "".join(tokens) == "Hello world"
    mock_conversation.add_user_message_async.assert_called_once_with("Hi")
```

### Integration Testing Pattern

**Pattern**: Test service with real dependencies in isolation

```python
# tests/integration/sdk/test_conversation_integration.py

import pytest
from consoul.sdk.services import ConversationService
from consoul.config import load_config

@pytest.mark.integration
@pytest.mark.asyncio
async def test_conversation_service_real_model():
    """Integration test with real model."""
    # Use test config
    config = load_config()
    config.current_model = "gpt-4o-mini"  # Cheap for testing

    # Create service
    service = ConversationService.from_config(config)

    # Send simple message
    response_text = ""
    async for token in service.send_message("Say 'OK'"):
        response_text += token.content

    # Verify we got a response
    assert len(response_text) > 0
    assert "OK" in response_text.upper()
```

## Common Patterns

### Async Iterator Pattern

Services use async iterators for streaming:

```python
async def send_message(self, msg: str) -> AsyncIterator[Token]:
    """Stream tokens as they arrive."""
    for chunk in self.model.stream(messages):
        yield Token(content=chunk.content, cost=None)
```

### Factory Method Pattern

Services use `from_config()` for initialization:

```python
@classmethod
def from_config(cls, config: ConsoulConfig | None = None) -> ConversationService:
    """Create from configuration.

    Args:
        config: Optional config (loads default if None)

    Returns:
        Initialized service
    """
    if config is None:
        from consoul.config import load_config
        config = load_config()

    # Initialize dependencies
    model = get_chat_model(config.get_current_model_config())
    conversation = ConversationHistory(...)

    return cls(model=model, conversation=conversation, config=config)
```

### Executor Pattern

Services use thread pool for blocking calls:

```python
from concurrent.futures import ThreadPoolExecutor

class ConversationService:
    def __init__(self, ...):
        self.executor = ThreadPoolExecutor(max_workers=1)

    async def _get_trimmed_messages(self):
        """Get trimmed messages without blocking."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self.conversation.get_trimmed_messages,
            reserve_tokens
        )
```

## Best Practices

### ✅ Do:

- **Comprehensive Docstrings**: Every public method needs docstring with example
- **Type Hints**: Use proper type hints including TYPE_CHECKING imports
- **Async-First**: Prefer async methods for I/O operations
- **Factory Methods**: Use `from_config()` classmethod pattern
- **Protocol Callbacks**: Use protocols for UI integration
- **Data Classes**: Use dataclasses for structured data
- **Error Handling**: Catch and log errors, don't let them bubble to UI

### ❌ Don't:

- **Import UI Frameworks**: No Rich, Textual, Typer in services
- **Print to Console**: Use logging instead
- **Block Event Loop**: Use `run_in_executor()` for blocking I/O
- **Hardcode Paths**: Use config for file paths
- **Tight Coupling**: Avoid depending on specific UI implementations

## Examples

See these files for real-world service usage:

- **FastAPI Integration**: `examples/fastapi_websocket_server.py` (SOUL-257)
- **WebSocket Streaming**: `examples/sdk/websocket_streaming.py` (SOUL-277)
- **Service Tests**: `tests/unit/sdk/services/test_conversation.py` (SOUL-256)
- **TUI Integration**: `src/consoul/tui/app.py` (uses all services)

## Next Steps

- **[Architecture Guide](architecture.md)** - Understanding the full architecture
- **[Testing Guide](testing.md)** - Testing patterns for each layer
- **[API Reference](../api/reference.md)** - Service layer API documentation
