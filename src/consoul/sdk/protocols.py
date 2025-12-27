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

from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

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


@runtime_checkable
class SessionHooks(Protocol):
    """Protocol for session lifecycle transformation hooks.

    Implementations can transform session state during save/load operations,
    enabling encryption, summarization, redaction, or custom processing
    without modifying core session management logic.

    Hook methods can be either sync or async - the HookedSessionStore wrapper
    auto-detects and handles both cases.

    Hook Execution Order:
        Save: on_before_save (all hooks, in order) -> store.save -> on_after_save (all hooks)
        Load: store.load -> on_after_load (all hooks, in reverse order for unwrapping)

    Example - Encryption hook:
        >>> class EncryptionHook:
        ...     def __init__(self, key_provider):
        ...         self.key_provider = key_provider
        ...
        ...     async def on_before_save(
        ...         self,
        ...         session_id: str,
        ...         state: dict[str, Any]
        ...     ) -> dict[str, Any]:
        ...         # Encrypt messages before storage
        ...         key = await self.key_provider.get_key(session_id)
        ...         encrypted_messages = encrypt(state["messages"], key)
        ...         return {**state, "messages": encrypted_messages, "_encrypted": True}
        ...
        ...     async def on_after_load(
        ...         self,
        ...         session_id: str,
        ...         state: dict[str, Any] | None
        ...     ) -> dict[str, Any] | None:
        ...         if not state or not state.get("_encrypted"):
        ...             return state
        ...         key = await self.key_provider.get_key(session_id)
        ...         decrypted = decrypt(state["messages"], key)
        ...         result = {**state, "messages": decrypted}
        ...         del result["_encrypted"]
        ...         return result
        ...
        ...     async def on_after_save(
        ...         self,
        ...         session_id: str,
        ...         state: dict[str, Any]
        ...     ) -> None:
        ...         pass  # No-op

    Example - Summarization hook (context compaction):
        >>> class SummarizationHook:
        ...     def __init__(self, summarizer, threshold: int = 50):
        ...         self.summarizer = summarizer
        ...         self.threshold = threshold
        ...
        ...     async def on_before_save(
        ...         self,
        ...         session_id: str,
        ...         state: dict[str, Any]
        ...     ) -> dict[str, Any]:
        ...         messages = state["messages"]
        ...         if len(messages) < self.threshold:
        ...             return state
        ...         # Summarize older messages, keep recent
        ...         summary = await self.summarizer.summarize(messages[:-10])
        ...         summarized_messages = [
        ...             {"role": "system", "content": f"Previous context: {summary}"}
        ...         ] + messages[-10:]
        ...         return {**state, "messages": summarized_messages}

    Example - Sync PII redaction hook:
        >>> class RedactionHook:
        ...     def __init__(self, redactor):
        ...         self.redactor = redactor
        ...
        ...     def on_before_save(  # Sync method - auto-detected
        ...         self,
        ...         session_id: str,
        ...         state: dict[str, Any]
        ...     ) -> dict[str, Any]:
        ...         redacted_messages = [
        ...             self.redactor.redact_dict(msg)
        ...             for msg in state["messages"]
        ...         ]
        ...         return {**state, "messages": redacted_messages}
        ...
        ...     def on_after_load(self, session_id, state):
        ...         return state  # Redaction is one-way
        ...
        ...     def on_after_save(self, session_id, state):
        ...         pass

    Security Notes:
        - Hooks receive full session state - implement carefully
        - on_before_save runs before storage - ideal for encryption/redaction
        - on_after_load runs after retrieval - ideal for decryption
        - Errors in on_after_save are logged but don't fail the save
        - Errors in on_before_save/on_after_load abort the operation
    """

    def on_before_save(
        self,
        session_id: str,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Transform state before saving to storage.

        Called after state extraction, before store.save().
        Can be sync or async - HookedSessionStore handles both.

        Args:
            session_id: Session identifier
            state: Session state dictionary (mutable copy)

        Returns:
            Transformed state dictionary (same or modified)

        Raises:
            Any exception will abort the save operation
        """
        ...

    def on_before_load(
        self,
        session_id: str,
    ) -> str | None:
        """Pre-load hook for session access control or ID transformation.

        Called before store.load(). Useful for access control checks,
        session ID transformation, or logging access attempts.
        Can be sync or async - HookedSessionStore handles both.

        Args:
            session_id: Session identifier to be loaded

        Returns:
            Session ID to load (may be transformed), or None to abort load

        Raises:
            Any exception will abort the load operation
        """
        ...

    def on_after_load(
        self,
        session_id: str,
        state: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Transform state after loading from storage.

        Called after store.load(), before returning to caller.
        Can be sync or async - HookedSessionStore handles both.

        Args:
            session_id: Session identifier
            state: Session state dictionary or None if not found

        Returns:
            Transformed state dictionary, or None

        Raises:
            Any exception will be propagated to caller
        """
        ...

    def on_after_save(
        self,
        session_id: str,
        state: dict[str, Any],
    ) -> None:
        """Callback after successful save (optional).

        Called after store.save() completes successfully.
        Useful for audit logging, notifications, metrics.
        Can be sync or async - HookedSessionStore handles both.

        Args:
            session_id: Session identifier
            state: Session state that was saved

        Note:
            Exceptions are logged but don't affect the save result.
        """
        ...

    def on_before_delete(
        self,
        session_id: str,
    ) -> None:
        """Callback before session deletion (optional).

        Called before store.delete(). Useful for cleanup operations
        or preventing deletion of certain sessions.
        Can be sync or async - HookedSessionStore handles both.

        Args:
            session_id: Session identifier to be deleted

        Raises:
            Any exception will abort the delete operation
        """
        ...

    def on_after_delete(
        self,
        session_id: str,
    ) -> None:
        """Callback after session deletion (optional).

        Called after store.delete() completes successfully.
        Useful for audit logging, cache invalidation, notifications.
        Can be sync or async - HookedSessionStore handles both.

        Args:
            session_id: Session identifier that was deleted

        Note:
            Exceptions are logged but don't affect the delete result.
        """
        ...
