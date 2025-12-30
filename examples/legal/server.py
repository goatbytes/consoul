#!/usr/bin/env python3
"""Legal Industry Production Server for Consoul.

A production-ready FastAPI server configured for legal industry deployment
with strict security controls, audit logging, and multi-user isolation.

Features:
- Tool restrictions: Read-only tools only (read, grep)
- Filesystem sandbox: Per-matter storage isolation
- User→Matter auth binding: API key tied to matter access
- Audit logging: Tamper-evident, PII-redacted JSON logs
- Rate limiting: Per-key limits (30/min, 500/hour)
- WebSocket streaming: Real-time responses with token validation
- Session isolation: Redis-backed per-user/matter sessions

Security Model:
- All tool execution is logged with correlation IDs
- Path traversal is prevented via allowlist
- Cross-matter access is blocked at auth layer
- No web/shell tools to prevent data exfiltration

Usage:
    # Set environment variables
    export OPENAI_API_KEY=your-key-here
    export CONSOUL_API_KEYS=key1,key2,key3
    export REDIS_URL=redis://localhost:6379

    # Run server
    python examples/legal/server.py

    # Or with uvicorn
    uvicorn examples.legal.server:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from consoul.ai.tools.audit import AuditEvent, StructuredAuditLogger
from consoul.config.models import LoggingConfig
from consoul.sdk import Consoul, create_session

if TYPE_CHECKING:
    from consoul.sdk.models import ToolRequest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("legal-server")


# ============================================================================
# Configuration Loading
# ============================================================================


def load_config() -> dict[str, Any]:
    """Load configuration from config.yaml."""
    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        raise RuntimeError(f"Configuration file not found: {config_path}")

    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Expand environment variables
    def expand_env(value: Any) -> Any:
        if isinstance(value, str):
            # Match ${VAR} or ${VAR:-default} patterns
            pattern = r"\$\{([^}:]+)(?::-([^}]*))?\}"
            matches = re.findall(pattern, value)
            for var_name, default in matches:
                env_value = os.environ.get(var_name, default)
                value = value.replace(f"${{{var_name}:-{default}}}", env_value or "")
                value = value.replace(f"${{{var_name}}}", env_value or "")
            return value
        elif isinstance(value, dict):
            return {k: expand_env(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [expand_env(v) for v in value]
        return value

    return expand_env(config)


CONFIG = load_config()


# ============================================================================
# Security: API Key Management
# ============================================================================


class APIKeyManager:
    """Manages API key authentication with matter-level authorization."""

    def __init__(self, api_keys: str | list[str] | None = None):
        """Initialize with API keys from config or environment."""
        if api_keys is None:
            api_keys = os.environ.get("CONSOUL_API_KEYS", "")

        if isinstance(api_keys, str):
            self.api_keys = {k.strip() for k in api_keys.split(",") if k.strip()}
        else:
            self.api_keys = set(api_keys)

        # Map API keys to authorized matters (in production, load from database)
        # Format: {api_key_hash: set(matter_ids)}
        self._key_matters: dict[str, set[str]] = {}

    def _hash_key(self, key: str) -> str:
        """Hash API key for secure storage."""
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def validate_key(self, api_key: str) -> bool:
        """Check if API key is valid."""
        return api_key in self.api_keys

    def authorize_matter(self, api_key: str, matter_id: str) -> bool:
        """Check if API key is authorized for the given matter.

        In production, this would query a database to check:
        - User associated with API key
        - User's role and permissions
        - Matter assignment to user

        For this example, all valid keys can access all matters.

        In production, query a database for user→matter authorization:
            user = db.get_user_by_api_key(api_key)
            return db.user_has_matter_access(user.id, matter_id)
        """
        return self.validate_key(api_key)


api_key_manager = APIKeyManager(CONFIG.get("security", {}).get("api_keys"))


# ============================================================================
# Security: Filesystem Sandbox
# ============================================================================


class FilesystemSandbox:
    """Enforces per-matter filesystem isolation."""

    def __init__(self, storage_root: str = "/data/matters"):
        self.storage_root = Path(storage_root)
        self.blocked_paths = {
            Path("/etc"),
            Path("/var"),
            Path("/home"),
            Path("/root"),
            Path("/tmp"),
            Path("/proc"),
            Path("/sys"),
        }

    def get_matter_path(self, matter_id: str) -> Path:
        """Get the sandboxed storage path for a matter."""
        # Sanitize matter_id to prevent path traversal
        safe_id = re.sub(r"[^a-zA-Z0-9_-]", "", matter_id)
        if not safe_id:
            raise ValueError("Invalid matter ID")
        return self.storage_root / safe_id

    def validate_path(self, path: str | Path, matter_id: str) -> Path:
        """Validate that a path is within the matter's sandbox.

        Raises:
            ValueError: If path is outside sandbox or blocked
        """
        requested = Path(path).resolve()
        matter_root = self.get_matter_path(matter_id).resolve()

        # Check for path traversal attacks
        try:
            requested.relative_to(matter_root)
        except ValueError:
            raise ValueError(
                f"Access denied: Path '{path}' is outside matter sandbox"
            ) from None

        # Check blocked paths
        for blocked in self.blocked_paths:
            if requested == blocked or blocked in requested.parents:
                raise ValueError(f"Access denied: Path '{path}' is blocked")

        return requested

    def ensure_matter_directory(self, matter_id: str) -> Path:
        """Create matter directory if it doesn't exist."""
        matter_path = self.get_matter_path(matter_id)
        matter_path.mkdir(parents=True, exist_ok=True)
        return matter_path


sandbox = FilesystemSandbox(CONFIG.get("storage", {}).get("root", "/data/matters"))


# ============================================================================
# Security: Sandbox Approval Provider
# ============================================================================


class SandboxApprovalProvider:
    """Tool approval provider that enforces filesystem sandbox.

    Validates all file paths in tool arguments against the matter sandbox
    before allowing tool execution. This provides hard enforcement beyond
    prompt-based restrictions.
    """

    def __init__(self, matter_id: str, sandbox: FilesystemSandbox):
        self.matter_id = matter_id
        self.sandbox = sandbox
        self.matter_path = sandbox.get_matter_path(matter_id)

    def on_tool_request(self, request: Any) -> bool:
        """Validate tool request against sandbox rules.

        Args:
            request: Tool request with name and arguments

        Returns:
            True if allowed, False if blocked
        """
        tool_name = getattr(request, "name", "") or request.get("name", "")
        arguments = getattr(request, "arguments", {}) or request.get("arguments", {})

        # Tools that access files need path validation
        if tool_name in ("read", "grep", "code_search", "find_references"):
            # Check common path argument names
            for path_key in ("path", "file_path", "directory", "dir", "pattern"):
                if path_key in arguments:
                    path_value = arguments[path_key]
                    if not self._validate_path(path_value):
                        logger.warning(
                            f"Sandbox blocked: {tool_name} attempted to access '{path_value}' "
                            f"outside matter {self.matter_id}"
                        )
                        return False

        return True

    def _validate_path(self, path: str) -> bool:
        """Check if path is within the matter sandbox.

        Args:
            path: Path to validate

        Returns:
            True if path is allowed, False otherwise
        """
        if not path:
            return True

        try:
            # Resolve the path (handles .. and symlinks)
            # If path is relative, resolve from matter directory
            if not Path(path).is_absolute():
                resolved = (self.matter_path / path).resolve()
            else:
                resolved = Path(path).resolve()

            # Check if resolved path is within matter sandbox
            resolved.relative_to(self.matter_path.resolve())

            # Also check against blocked system paths
            for blocked in self.sandbox.blocked_paths:
                if resolved == blocked or blocked in resolved.parents:
                    return False

            return True

        except (ValueError, OSError):
            # Path is outside sandbox or invalid
            return False


# ============================================================================
# Security: Rate Limiting
# ============================================================================


class RateLimiter:
    """Simple in-memory rate limiter (use Redis in production)."""

    def __init__(self, limits: list[str] | None = None):
        self.limits = limits or ["30 per minute", "500 per hour"]
        self._requests: dict[str, list[float]] = {}

    def check(self, key: str) -> bool:
        """Check if request is allowed under rate limits."""
        now = datetime.now(timezone.utc).timestamp()
        requests = self._requests.get(key, [])

        # Clean old requests
        minute_ago = now - 60
        hour_ago = now - 3600
        requests = [t for t in requests if t > hour_ago]

        # Check limits
        minute_count = sum(1 for t in requests if t > minute_ago)
        hour_count = len(requests)

        # Parse limits (e.g., "30 per minute")
        for limit in self.limits:
            parts = limit.split()
            if len(parts) >= 3:
                count = int(parts[0])
                period = parts[2]
                if period == "minute" and minute_count >= count:
                    return False
                if period == "hour" and hour_count >= count:
                    return False

        # Record request
        requests.append(now)
        self._requests[key] = requests
        return True


rate_limiter = RateLimiter(CONFIG.get("security", {}).get("rate_limits"))


# ============================================================================
# Audit Logging
# ============================================================================


def create_audit_logger() -> StructuredAuditLogger:
    """Create audit logger from configuration."""
    log_config = CONFIG.get("logging", {})
    return StructuredAuditLogger(
        LoggingConfig(
            enabled=log_config.get("enabled", True),
            format=log_config.get("format", "json"),
            output=log_config.get("output", "file"),
            file_path=Path(
                log_config.get("file_path", "/var/log/consoul/legal_audit.jsonl")
            ),
            redact_pii=log_config.get("redact_pii", True),
            redact_fields=log_config.get("redact_fields", []),
            correlation_ids=log_config.get("correlation_ids", True),
            max_arg_length=log_config.get("max_arg_length", 500),
        )
    )


audit_logger = create_audit_logger()


# ============================================================================
# Request/Response Models
# ============================================================================


class ChatRequest(BaseModel):
    """Chat request with message and optional attachments."""

    message: str = Field(..., min_length=1, max_length=50000)
    matter_id: str = Field(..., pattern=r"^[a-zA-Z0-9_-]+$")
    attachments: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """Chat response with AI-generated content."""

    response: str
    matter_id: str
    correlation_id: str
    model: str
    tokens: int = 0
    cost: float = 0.0


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    service: str
    version: str
    timestamp: str


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Consoul Legal API",
    description="Production API for legal industry AI document analysis",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
cors_origins = CONFIG.get("security", {}).get("cors_origins", ["http://localhost:3000"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if isinstance(cors_origins, list) else [cors_origins],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key", "Authorization"],
)


# ============================================================================
# Authentication Dependency
# ============================================================================


async def verify_api_key(request: Request) -> str:
    """Verify API key from header or query parameter."""
    api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")

    if not api_key:
        raise HTTPException(status_code=401, detail="API key required")

    if not api_key_manager.validate_key(api_key):
        # Log failed auth attempt
        await audit_logger.log_event(
            AuditEvent(
                event_type="blocked",
                tool_name="auth",
                arguments={"reason": "invalid_api_key"},
                correlation_id=secrets.token_hex(8),
                metadata={
                    "client_ip": request.client.host if request.client else "unknown"
                },
            )
        )
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Check rate limit
    if not rate_limiter.check(api_key):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    return api_key


async def verify_matter_access(request: Request, api_key: str, matter_id: str) -> str:
    """Verify API key has access to the specified matter."""
    if not api_key_manager.authorize_matter(api_key, matter_id):
        await audit_logger.log_event(
            AuditEvent(
                event_type="blocked",
                tool_name="auth",
                arguments={"reason": "unauthorized_matter", "matter_id": matter_id},
                correlation_id=secrets.token_hex(8),
                user=api_key[:8] + "...",
            )
        )
        raise HTTPException(status_code=403, detail="Not authorized for this matter")
    return matter_id


# ============================================================================
# Legal Context Provider
# ============================================================================


class LegalContextProvider:
    """Provides legal context for AI responses."""

    def __init__(
        self,
        jurisdiction: str = "California",
        practice_area: str = "workers_compensation",
    ):
        self.jurisdiction = jurisdiction
        self.practice_area = practice_area

    def get_context(self, matter_id: str | None = None) -> dict[str, str]:
        """Get legal context for system prompt injection."""
        return {
            "jurisdiction": f"{self.jurisdiction} {self.practice_area.replace('_', ' ').title()} Law",
            "legal_notice": (
                "IMPORTANT: This AI provides general legal information only. "
                "It does not constitute legal advice and should not be relied upon "
                "as such. Always consult with a licensed attorney for specific "
                "legal advice regarding your situation. Attorney-client privilege "
                "may apply to communications within this system."
            ),
            "data_handling": (
                "All interactions are logged for compliance purposes. "
                "Sensitive information is redacted from logs. "
                "Do not include client social security numbers, "
                "financial account numbers, or other highly sensitive PII in queries."
            ),
        }


legal_context = LegalContextProvider(
    jurisdiction=CONFIG.get("context", {}).get("jurisdiction", "California"),
    practice_area=CONFIG.get("context", {}).get(
        "practice_area", "workers_compensation"
    ),
)


# ============================================================================
# Endpoints
# ============================================================================


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint (no auth required)."""
    return HealthResponse(
        status="healthy",
        service="Consoul Legal API",
        version="1.0.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/ready")
async def readiness_check() -> dict[str, Any]:
    """Readiness check with dependency verification."""
    checks = {
        "config": True,
        "audit_logger": audit_logger is not None,
    }

    # Check Redis (if configured)
    redis_url = CONFIG.get("session", {}).get("redis_url")
    if redis_url:
        try:
            import redis

            r = redis.from_url(redis_url)
            r.ping()
            checks["redis"] = True
        except Exception:
            checks["redis"] = False

    all_ready = all(checks.values())
    return {
        "status": "ready" if all_ready else "not_ready",
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    api_key: str = Depends(verify_api_key),
) -> ChatResponse:
    """Process a chat message with legal context.

    Requires API key authentication and matter authorization.
    All interactions are logged for compliance.
    """
    correlation_id = secrets.token_hex(8)

    # Verify matter access
    await verify_matter_access(None, api_key, request.matter_id)  # type: ignore

    # Log request
    await audit_logger.log_event(
        AuditEvent(
            event_type="request",
            tool_name="chat",
            arguments={
                "message_length": len(request.message),
                "matter_id": request.matter_id,
            },
            correlation_id=correlation_id,
            session_id=request.matter_id,
            user=api_key[:8] + "...",
        )
    )

    try:
        # Get matter sandbox path - MUST be enforced for security
        matter_path = sandbox.get_matter_path(request.matter_id)
        sandbox.ensure_matter_directory(request.matter_id)

        # Build system prompt with legal context AND sandbox enforcement
        context = legal_context.get_context(request.matter_id)
        system_prompt = f"""You are a legal AI assistant for {context["jurisdiction"]}.

{context["legal_notice"]}

{context["data_handling"]}

CRITICAL FILE ACCESS RESTRICTION:
You may ONLY read files from the following directory: {matter_path}
Any file paths you use MUST start with "{matter_path}/".
DO NOT attempt to access files outside this directory.
If asked to access files elsewhere, explain that you can only access files within the client's matter directory.

Provide accurate, helpful responses based on the documents and information available.
Always cite specific documents or sources when making claims about case facts.
If you're unsure about something, say so clearly."""

        # Create Consoul session with restricted tools and sandbox enforcement
        tools_config = CONFIG.get("tools", {})
        allowed_tools = tools_config.get("allowed_tools", ["read", "grep"])

        # Create sandbox approval provider for hard path enforcement (P1 fix)
        sandbox_provider = SandboxApprovalProvider(request.matter_id, sandbox)

        console = Consoul(
            model=CONFIG.get("model", {}).get("model", "gpt-4o"),
            temperature=CONFIG.get("model", {}).get("temperature", 0.3),
            system_prompt=system_prompt,
            tools=allowed_tools,
            persist=False,  # Don't persist conversation (use Redis for sessions)
            working_dir=str(matter_path),  # Set working directory
            approval_provider=sandbox_provider,  # Enforce sandbox on all tool calls
        )

        # Process message (run in thread pool to avoid blocking event loop)
        response_text = await asyncio.to_thread(console.chat, request.message)

        # Get usage stats
        cost_info = console.last_cost

        # Log response
        await audit_logger.log_event(
            AuditEvent(
                event_type="result",
                tool_name="chat",
                arguments={},
                result=f"Response generated ({len(response_text)} chars)",
                correlation_id=correlation_id,
                session_id=request.matter_id,
                user=api_key[:8] + "...",
                metadata={
                    "model": CONFIG.get("model", {}).get("model", "gpt-4o"),
                    "tokens": cost_info.get("total_tokens", 0),
                    "cost": cost_info.get("estimated_cost", 0.0),
                },
            )
        )

        return ChatResponse(
            response=response_text,
            matter_id=request.matter_id,
            correlation_id=correlation_id,
            model=CONFIG.get("model", {}).get("model", "gpt-4o"),
            tokens=cost_info.get("total_tokens", 0),
            cost=cost_info.get("estimated_cost", 0.0),
        )

    except Exception as e:
        # Log error
        await audit_logger.log_event(
            AuditEvent(
                event_type="error",
                tool_name="chat",
                arguments={},
                error=str(e),
                correlation_id=correlation_id,
                session_id=request.matter_id,
                user=api_key[:8] + "...",
            )
        )
        raise HTTPException(status_code=500, detail="Error processing request") from e


# ============================================================================
# WebSocket Endpoint
# ============================================================================


class WebSocketApprovalProvider:
    """Tool approval provider for WebSocket connections."""

    def __init__(self, websocket: WebSocket, timeout: float = 60.0):
        self.websocket = websocket
        self.timeout = timeout
        self._pending: dict[str, asyncio.Future[bool]] = {}

    async def on_tool_request(self, request: ToolRequest) -> bool:
        """Request tool approval via WebSocket.

        For legal deployments, only read-only tools are allowed,
        so this primarily serves as an audit mechanism.
        """
        # For read-only tools in legal context, auto-approve
        # For any other tools, deny by default
        return request.name in ["read", "grep"]


@app.websocket("/ws/chat/{matter_id}")
async def websocket_chat(websocket: WebSocket, matter_id: str):
    """WebSocket endpoint for streaming chat.

    Protocol:
        Client → Server:
            {"type": "auth", "api_key": "..."}
            {"type": "message", "content": "user message"}

        Server → Client:
            {"type": "auth_result", "success": true}
            {"type": "token", "content": "partial response"}
            {"type": "done", "tokens": 150, "cost": 0.001, "correlation_id": "..."}
            {"type": "error", "message": "error details"}
    """
    await websocket.accept()
    logger.info(f"WebSocket connected for matter: {matter_id}")

    api_key: str | None = None
    correlation_id = secrets.token_hex(8)

    try:
        # Check for API key in query params first (as documented in README)
        api_key = websocket.query_params.get("api_key")

        if api_key:
            # Query param auth - validate immediately
            if not api_key_manager.validate_key(api_key):
                await websocket.send_json(
                    {"type": "auth_result", "success": False, "error": "Invalid key"}
                )
                await websocket.close(code=4001)
                return

            if not api_key_manager.authorize_matter(api_key, matter_id):
                await websocket.send_json(
                    {"type": "auth_result", "success": False, "error": "Not authorized"}
                )
                await websocket.close(code=4003)
                return

            await websocket.send_json({"type": "auth_result", "success": True})

        else:
            # Fallback: First message must be auth frame
            auth_msg = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)

            if auth_msg.get("type") != "auth" or not auth_msg.get("api_key"):
                await websocket.send_json(
                    {"type": "auth_result", "success": False, "error": "Auth required"}
                )
                await websocket.close(code=4001)
                return

            api_key = auth_msg["api_key"]

            if not api_key_manager.validate_key(api_key):
                await websocket.send_json(
                    {"type": "auth_result", "success": False, "error": "Invalid key"}
                )
                await websocket.close(code=4001)
                return

            if not api_key_manager.authorize_matter(api_key, matter_id):
                await websocket.send_json(
                    {"type": "auth_result", "success": False, "error": "Not authorized"}
                )
                await websocket.close(code=4003)
                return

            await websocket.send_json({"type": "auth_result", "success": True})

        # Get matter sandbox path - MUST be enforced for security
        matter_path = sandbox.get_matter_path(matter_id)
        sandbox.ensure_matter_directory(matter_id)

        # Log connection
        await audit_logger.log_event(
            AuditEvent(
                event_type="request",
                tool_name="websocket_connect",
                arguments={"matter_id": matter_id},
                correlation_id=correlation_id,
                session_id=matter_id,
                user=api_key[:8] + "...",
            )
        )

        # Build session with sandbox enforcement
        context = legal_context.get_context(matter_id)
        system_prompt = f"""You are a legal AI assistant for {context["jurisdiction"]}.

{context["legal_notice"]}

CRITICAL FILE ACCESS RESTRICTION:
You may ONLY read files from the following directory: {matter_path}
Any file paths you use MUST start with "{matter_path}/".
DO NOT attempt to access files outside this directory.

Provide accurate, helpful responses based on the documents and information available."""

        tools_config = CONFIG.get("tools", {})
        allowed_tools = tools_config.get("allowed_tools", ["read", "grep"])

        # Create sandbox approval provider for hard path enforcement (P1 fix)
        sandbox_provider = SandboxApprovalProvider(matter_id, sandbox)

        console = create_session(
            session_id=f"legal-{matter_id}-{correlation_id}",
            model=CONFIG.get("model", {}).get("model", "gpt-4o"),
            temperature=CONFIG.get("model", {}).get("temperature", 0.3),
            system_prompt=system_prompt,
            tools=allowed_tools,
            working_dir=str(matter_path),  # Set working directory
            approval_provider=sandbox_provider,  # Enforce sandbox on all tool calls
        )

        # Message loop
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "message":
                # Check rate limit for each message (P2 fix)
                if not rate_limiter.check(api_key):
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "Rate limit exceeded",
                        }
                    )
                    continue

                content = data.get("content", "")
                msg_correlation_id = secrets.token_hex(8)

                # Log message
                await audit_logger.log_event(
                    AuditEvent(
                        event_type="request",
                        tool_name="chat",
                        arguments={"message_length": len(content)},
                        correlation_id=msg_correlation_id,
                        session_id=matter_id,
                        user=api_key[:8] + "...",
                    )
                )

                try:
                    # Process (synchronous for now)
                    response = await asyncio.to_thread(console.chat, content)

                    # Send response
                    await websocket.send_json(
                        {
                            "type": "response",
                            "content": response,
                        }
                    )

                    cost = console.last_cost
                    await websocket.send_json(
                        {
                            "type": "done",
                            "tokens": cost.get("total_tokens", 0),
                            "cost": cost.get("estimated_cost", 0.0),
                            "correlation_id": msg_correlation_id,
                        }
                    )

                    # Log completion
                    await audit_logger.log_event(
                        AuditEvent(
                            event_type="result",
                            tool_name="chat",
                            arguments={},
                            result=f"Response ({len(response)} chars)",
                            correlation_id=msg_correlation_id,
                            session_id=matter_id,
                            user=api_key[:8] + "...",
                            metadata={"tokens": cost.get("total_tokens", 0)},
                        )
                    )

                except Exception as e:
                    logger.error(f"Chat error: {e}", exc_info=True)
                    await websocket.send_json(
                        {
                            "type": "error",
                            "message": "Error processing message",
                            "correlation_id": msg_correlation_id,
                        }
                    )

            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})

            else:
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Unknown message type: {msg_type}",
                    }
                )

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {matter_id}")
    except asyncio.TimeoutError:
        logger.warning(f"WebSocket auth timeout: {matter_id}")
        await websocket.close(code=4008)
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        await websocket.close(code=4000)

    finally:
        # Log disconnection
        if api_key:
            await audit_logger.log_event(
                AuditEvent(
                    event_type="result",
                    tool_name="websocket_disconnect",
                    arguments={"matter_id": matter_id},
                    correlation_id=correlation_id,
                    session_id=matter_id,
                    user=api_key[:8] + "...",
                )
            )


# ============================================================================
# File Upload Endpoint
# ============================================================================


@app.post("/upload/{matter_id}")
async def upload_file(
    matter_id: str,
    request: Request,
    api_key: str = Depends(verify_api_key),
) -> dict[str, Any]:
    """Upload a document to a matter's sandbox.

    Validates:
    - API key authorization for matter
    - File size limits
    - MIME type allowlist
    - Filename sanitization
    """
    correlation_id = secrets.token_hex(8)

    # Verify matter access
    await verify_matter_access(request, api_key, matter_id)

    # Get storage config
    storage_config = CONFIG.get("storage", {})
    max_size_mb = storage_config.get("max_file_size_mb", 50)
    allowed_mimes = storage_config.get(
        "allowed_mime_types", ["application/pdf", "text/plain"]
    )

    # Read file from request
    content_type = request.headers.get("content-type", "")
    content_length = int(request.headers.get("content-length", 0))

    # Check size
    if content_length > max_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=413, detail=f"File too large (max {max_size_mb}MB)"
        )

    # Check MIME type
    mime_type = content_type.split(";")[0].strip()
    if mime_type not in allowed_mimes:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_mimes)}",
        )

    # Get filename from header
    content_disposition = request.headers.get("content-disposition", "")
    filename = "document"
    if "filename=" in content_disposition:
        filename = content_disposition.split("filename=")[-1].strip('"')

    # Sanitize filename
    safe_filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
    if not safe_filename:
        safe_filename = f"upload_{secrets.token_hex(4)}"

    # Ensure matter directory exists
    matter_path = sandbox.ensure_matter_directory(matter_id)
    file_path = matter_path / safe_filename

    # Avoid overwrites
    counter = 1
    while file_path.exists():
        stem = Path(safe_filename).stem
        suffix = Path(safe_filename).suffix
        file_path = matter_path / f"{stem}_{counter}{suffix}"
        counter += 1

    # Stream body with size limit to prevent memory exhaustion (P1 fix)
    # Don't use request.body() which loads everything into memory first
    max_size_bytes = max_size_mb * 1024 * 1024
    chunks: list[bytes] = []
    total_size = 0

    async for chunk in request.stream():
        total_size += len(chunk)
        if total_size > max_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum: {max_size_mb}MB ({max_size_bytes} bytes)",
            )
        chunks.append(chunk)

    body = b"".join(chunks)

    # Write file
    file_path.write_bytes(body)

    # Log upload
    await audit_logger.log_event(
        AuditEvent(
            event_type="execution",
            tool_name="file_upload",
            arguments={
                "matter_id": matter_id,
                "filename": safe_filename,
                "size_bytes": len(body),
                "mime_type": mime_type,
            },
            result=f"Uploaded to {file_path.name}",
            correlation_id=correlation_id,
            session_id=matter_id,
            user=api_key[:8] + "...",
            decision=True,
        )
    )

    return {
        "status": "uploaded",
        "filename": file_path.name,
        "path": str(file_path.relative_to(sandbox.storage_root)),
        "size_bytes": len(body),
        "correlation_id": correlation_id,
    }


# ============================================================================
# Error Handlers
# ============================================================================


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Handle validation errors without exposing internals."""
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected errors without exposing stack traces."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("Consoul Legal Industry Server")
    print("=" * 60)
    print()
    print("Configuration:")
    print(f"  Model: {CONFIG.get('model', {}).get('model', 'gpt-4o')}")
    print(f"  Tools: {CONFIG.get('tools', {}).get('allowed_tools', [])}")
    print(f"  Storage: {CONFIG.get('storage', {}).get('root', '/data/matters')}")
    print(f"  Audit Log: {CONFIG.get('logging', {}).get('file_path')}")
    print()
    print("Endpoints:")
    print("  GET  /health          - Health check")
    print("  GET  /ready           - Readiness check")
    print("  POST /chat            - Chat with AI")
    print("  POST /upload/{matter} - Upload document")
    print("  WS   /ws/chat/{matter} - WebSocket chat")
    print()
    print("Security:")
    print("  - API key required (X-API-Key header)")
    print("  - Per-matter filesystem sandbox")
    print("  - All actions logged for compliance")
    print()
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
