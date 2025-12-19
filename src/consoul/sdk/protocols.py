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
class ContextProvider(Protocol):
    """Protocol for dynamic context injection into AI system prompts.

    Implementations provide domain-specific context that gets injected into
    the system prompt at runtime. This enables building specialized AI agents
    (legal, medical, customer support) with dynamic knowledge from databases,
    APIs, or other runtime sources.

    Methods:
        get_context: Return context sections to inject into system prompt

    Use Cases:
        - Legal AI: Query case law databases for relevant precedents
        - Medical Chatbot: Fetch patient data from EHR systems
        - Customer Support: Load customer history from CRM
        - Research Assistant: Retrieve relevant papers from knowledge base

    Example - Legal AI with case law database:
        >>> class LegalContextProvider:
        ...     def __init__(self, jurisdiction: str, case_db):
        ...         self.jurisdiction = jurisdiction
        ...         self.db = case_db
        ...
        ...     def get_context(
        ...         self,
        ...         query: str | None = None,
        ...         conversation_id: str | None = None
        ...     ) -> dict[str, str]:
        ...         # Search case law based on query
        ...         cases = self.db.search_cases(query, self.jurisdiction)
        ...         return {
        ...             "jurisdiction": f"{self.jurisdiction} workers' compensation law",
        ...             "relevant_cases": self._format_cases(cases),
        ...             "last_updated": datetime.now().isoformat()
        ...         }
        >>>
        >>> # Usage with SDK
        >>> provider = LegalContextProvider("California", case_database)
        >>> console = Consoul(
        ...     model="gpt-4o",
        ...     system_prompt="You are a legal assistant...",
        ...     context_providers=[provider],
        ...     tools=False
        ... )

    Example - Medical chatbot with patient context:
        >>> class PatientContextProvider:
        ...     def __init__(self, patient_id: str, ehr_client):
        ...         self.patient_id = patient_id
        ...         self.ehr = ehr_client
        ...
        ...     def get_context(
        ...         self,
        ...         query: str | None = None,
        ...         conversation_id: str | None = None
        ...     ) -> dict[str, str]:
        ...         # Fetch patient data from EHR
        ...         patient = self.ehr.get_patient(self.patient_id)
        ...         return {
        ...             "patient_demographics": patient.demographics_summary(),
        ...             "medical_history": patient.relevant_history(),
        ...             "current_medications": patient.active_medications(),
        ...             "allergies": patient.known_allergies()
        ...         }

    Example - Customer support with CRM integration:
        >>> class CRMContextProvider:
        ...     def __init__(self, customer_id: str, crm_api):
        ...         self.customer_id = customer_id
        ...         self.crm = crm_api
        ...
        ...     def get_context(
        ...         self,
        ...         query: str | None = None,
        ...         conversation_id: str | None = None
        ...     ) -> dict[str, str]:
        ...         customer = self.crm.get_customer(self.customer_id)
        ...         return {
        ...             "customer_tier": customer.subscription_tier,
        ...             "account_status": customer.status_summary(),
        ...             "recent_tickets": customer.recent_support_tickets(limit=5),
        ...             "product_licenses": customer.active_licenses()
        ...         }

    Example - Multiple providers composition:
        >>> console = Consoul(
        ...     model="gpt-4o",
        ...     system_prompt="You are a comprehensive assistant...",
        ...     context_providers=[
        ...         KnowledgeBaseProvider(kb_id="medical"),
        ...         PatientContextProvider(patient_id="12345", ehr=ehr_client),
        ...         ComplianceProvider(regulations=["HIPAA", "GDPR"])
        ...     ]
        ... )

    Security Notes:
        - Sanitize/validate all data before returning from get_context()
        - Don't expose sensitive credentials or internal IDs in context
        - Consider token limits - keep context concise
        - Handle errors gracefully (SDK will catch exceptions)
    """

    def get_context(
        self,
        query: str | None = None,
        conversation_id: str | None = None,
    ) -> dict[str, str]:
        """Return context sections to inject into system prompt.

        Called by the SDK before building the system prompt. The returned
        dictionary maps section names to content strings, which are injected
        into the prompt as separate context blocks.

        Args:
            query: Optional current user query for context-aware injection.
                  Enables providers to return different context based on
                  the specific question being asked.
            conversation_id: Optional conversation identifier for stateful
                           context providers that track conversation history.

        Returns:
            Dictionary mapping context section names to content strings.
            Each key becomes a section header in the system prompt, and
            the value is the section content.

        Raises:
            Any exception raised will be caught and logged by the SDK.
            The conversation will continue with partial context from other
            providers.

        Example Return Value:
            {
                "domain_knowledge": "California workers' compensation...",
                "relevant_precedents": "Case A: ...\nCase B: ...",
                "client_context": "Matter ID: 12345, Filed: 2024-01-15"
            }

        Note:
            - Keep context concise to avoid exceeding token limits
            - Return empty dict {} if no context is available
            - Section names should be descriptive (avoid generic names)
            - Content should be well-formatted (use newlines, bullets)
        """
        ...


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
