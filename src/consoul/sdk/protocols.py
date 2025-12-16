"""Protocol definitions for SDK service layer.

Protocols define interfaces that implementations must follow without
requiring inheritance. This enables flexible integration patterns and
dependency injection.

Example:
    >>> class WebApprovalProvider:
    ...     async def on_tool_request(self, request: ToolRequest) -> bool:
    ...         # Send approval request to web UI
    ...         return await websocket.send_approval_request(request)
    >>> # Type checker validates protocol compliance
    >>> provider: ToolExecutionCallback = WebApprovalProvider()
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from consoul.sdk.models import ToolRequest


@runtime_checkable
class ToolExecutionCallback(Protocol):
    """Protocol for tool execution approval.

    Implementations provide custom approval logic for tool execution requests.
    The ConversationService calls this before executing any tool, allowing
    the caller to approve or deny based on their requirements.

    Methods:
        on_tool_request: Async method called when tool execution is requested

    Example - Auto-approve safe tools:
        >>> class SafeOnlyApprover:
        ...     async def on_tool_request(self, request: ToolRequest) -> bool:
        ...         return request.risk_level == "safe"

    Example - CLI approval with prompt:
        >>> class CliApprover:
        ...     async def on_tool_request(self, request: ToolRequest) -> bool:
        ...         print(f"Allow {request.name}? [y/n]")
        ...         return input().lower() == 'y'

    Example - WebSocket approval:
        >>> class WebSocketApprover:
        ...     def __init__(self, websocket):
        ...         self.ws = websocket
        ...     async def on_tool_request(self, request: ToolRequest) -> bool:
        ...         await self.ws.send_json({
        ...             "type": "tool_approval_request",
        ...             "tool": request.name,
        ...             "args": request.arguments
        ...         })
        ...         response = await self.ws.receive_json()
        ...         return response.get("approved", False)
    """

    async def on_tool_request(self, request: ToolRequest) -> bool:
        """Request approval for tool execution.

        Args:
            request: Tool execution request with name, arguments, and risk level

        Returns:
            True to approve and execute the tool, False to deny

        Note:
            This method MUST be async to support non-blocking approval workflows
            like showing UI modals, sending network requests, or user input.
        """
        ...
