"""Session ID utilities for namespace-based scoping.

Provides helpers for constructing and parsing namespaced session IDs
without mandating specific patterns. SDK users can adopt these conventions
or implement their own.

Namespace Pattern:
    {tenant}:{user}:{session} or {user}:{session}

    Examples:
        - "acme:user123:conv456" (tenant + user + session)
        - "user123:conv456" (user + session)
        - "conv456" (session only, no namespace)

Example - Building namespaced session IDs:
    >>> from consoul.sdk.session_id import build_session_id, SessionIdBuilder

    >>> # Simple user-scoped session
    >>> session_id = build_session_id(user_id="alice")
    >>> print(session_id)
    alice:a1b2c3d4e5f6

    >>> # Multi-tenant with fluent builder
    >>> session_id = (
    ...     SessionIdBuilder()
    ...     .tenant("acme_corp")
    ...     .user("alice")
    ...     .session()  # Auto-generates UUID
    ...     .build()
    ... )
    >>> print(session_id)
    acme_corp:alice:a1b2c3d4e5f6

Example - Parsing session IDs:
    >>> from consoul.sdk.session_id import parse_session_id

    >>> parsed = parse_session_id("acme:alice:conv123")
    >>> print(parsed.tenant_id, parsed.user_id, parsed.session_id)
    acme alice conv123

Security Notes:
    - Session IDs should be cryptographically secure (UUID, not sequential)
    - Never expose internal tenant/user IDs to untrusted clients
    - Consider using opaque session tokens with server-side mapping
    - Validate session IDs before use to prevent injection attacks
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from urllib.parse import quote, unquote

__all__ = [
    "ParsedSessionId",
    "SessionIdBuilder",
    "build_session_id",
    "generate_session_id",
    "is_namespaced",
    "parse_session_id",
]


@dataclass
class ParsedSessionId:
    """Parsed components of a namespaced session ID.

    Attributes:
        full_id: Complete session ID string as originally passed
        tenant_id: Tenant namespace component (None if not present)
        user_id: User namespace component (None if not present)
        session_id: Unique session identifier component (always present)

    Example:
        >>> from consoul.sdk.session_id import parse_session_id
        >>> parsed = parse_session_id("acme:alice:conv123")
        >>> parsed.tenant_id
        'acme'
        >>> parsed.user_id
        'alice'
        >>> parsed.session_id
        'conv123'
    """

    full_id: str
    tenant_id: str | None
    user_id: str | None
    session_id: str


def _encode_component(value: str, separator: str) -> str:
    """URL-encode separator characters in a component.

    This allows user_id, tenant_id, or session_id to contain the separator
    character without breaking parsing.

    Args:
        value: Component value to encode
        separator: Separator character to escape

    Returns:
        Encoded string with separator characters escaped
    """
    # URL-encode just the separator character
    # We use a custom safe set that excludes the separator
    return quote(value, safe="")


def _decode_component(value: str) -> str:
    """URL-decode a component value.

    Args:
        value: Encoded component value

    Returns:
        Decoded original string
    """
    return unquote(value)


class SessionIdBuilder:
    """Fluent builder for namespaced session IDs.

    Provides a chainable API for constructing session IDs with
    optional tenant and user namespaces.

    Example - Full namespace:
        >>> session_id = (
        ...     SessionIdBuilder()
        ...     .tenant("acme_corp")
        ...     .user("user_123")
        ...     .session()  # Auto-generates UUID
        ...     .build()
        ... )
        >>> print(session_id)
        acme_corp:user_123:a1b2c3d4e5f6

    Example - User-scoped only:
        >>> session_id = (
        ...     SessionIdBuilder()
        ...     .user("user_123")
        ...     .session("my_chat")
        ...     .build()
        ... )
        >>> print(session_id)
        user_123:my_chat

    Example - Custom separator:
        >>> session_id = (
        ...     SessionIdBuilder(separator="/")
        ...     .tenant("org")
        ...     .user("alice")
        ...     .session()
        ...     .build()
        ... )
        >>> print(session_id)
        org/alice/a1b2c3d4e5f6
    """

    def __init__(self, separator: str = ":") -> None:
        """Initialize builder.

        Args:
            separator: Namespace separator character (default: ":")
        """
        self._separator = separator
        self._tenant: str | None = None
        self._user: str | None = None
        self._session: str | None = None

    def tenant(self, tenant_id: str) -> SessionIdBuilder:
        """Set tenant namespace.

        Args:
            tenant_id: Tenant/organization identifier

        Returns:
            Self for chaining
        """
        self._tenant = tenant_id
        return self

    def user(self, user_id: str) -> SessionIdBuilder:
        """Set user namespace.

        Args:
            user_id: User identifier

        Returns:
            Self for chaining
        """
        self._user = user_id
        return self

    def session(self, session_id: str | None = None) -> SessionIdBuilder:
        """Set session identifier.

        Args:
            session_id: Session ID, or None to auto-generate secure UUID

        Returns:
            Self for chaining
        """
        self._session = session_id or generate_session_id()
        return self

    def build(self) -> str:
        """Build the namespaced session ID.

        Components are URL-encoded to allow separator characters in values.
        Use parse_session_id() to decode them back.

        Returns:
            Namespaced session ID string

        Raises:
            ValueError: If no session ID was set (call .session() first)
        """
        if not self._session:
            raise ValueError("Session ID must be set. Call .session() before .build()")

        parts = []
        if self._tenant:
            parts.append(_encode_component(self._tenant, self._separator))
        if self._user:
            parts.append(_encode_component(self._user, self._separator))
        parts.append(_encode_component(self._session, self._separator))

        return self._separator.join(parts)


def is_namespaced(session_id: str, separator: str = ":") -> bool:
    """Check if a session ID already has namespace components.

    A session ID is considered namespaced if it contains the separator
    and has 2-3 parts (user:session or tenant:user:session).

    Args:
        session_id: Session ID to check
        separator: Namespace separator (default: ":")

    Returns:
        True if session_id appears to be namespaced

    Examples:
        >>> is_namespaced("conv123")
        False

        >>> is_namespaced("alice:conv123")
        True

        >>> is_namespaced("acme:alice:conv123")
        True
    """
    parts = session_id.split(separator)
    return len(parts) in (2, 3)


def build_session_id(
    session_id: str | None = None,
    *,
    user_id: str | None = None,
    tenant_id: str | None = None,
    separator: str = ":",
) -> str:
    """Build namespaced session ID (convenience function).

    Constructs a session ID with optional user and tenant namespaces.
    If session_id is not provided, generates a secure random ID.

    If session_id is already namespaced AND its components match the
    provided user_id/tenant_id, it is returned as-is to prevent double-namespacing.

    Args:
        session_id: Session identifier (auto-generated if None)
        user_id: Optional user namespace
        tenant_id: Optional tenant namespace
        separator: Namespace separator (default: ":")

    Returns:
        Namespaced session ID string

    Examples:
        >>> build_session_id()  # Auto-generated
        'a1b2c3d4e5f6'

        >>> build_session_id(user_id="alice")
        'alice:a1b2c3d4e5f6'

        >>> build_session_id("my_chat", user_id="alice", tenant_id="acme")
        'acme:alice:my_chat'

        >>> build_session_id(session_id="conv1", user_id="bob")
        'bob:conv1'

        >>> # Already namespaced with matching components - returned as-is
        >>> build_session_id("acme:alice:conv123", user_id="alice", tenant_id="acme")
        'acme:alice:conv123'
    """
    # Check if session_id appears to be already namespaced with matching components
    if session_id and is_namespaced(session_id, separator):
        try:
            parsed = parse_session_id(session_id, separator)
            # Only skip if parsed components match what would be added
            if (user_id is None or parsed.user_id == user_id) and (
                tenant_id is None or parsed.tenant_id == tenant_id
            ):
                return session_id
        except ValueError:
            pass  # If parsing fails, proceed with building

    builder = SessionIdBuilder(separator=separator)
    if tenant_id:
        builder.tenant(tenant_id)
    if user_id:
        builder.user(user_id)
    builder.session(session_id)
    return builder.build()


def parse_session_id(
    session_id: str,
    separator: str = ":",
    expected_parts: int | None = None,
) -> ParsedSessionId:
    """Parse namespaced session ID into components.

    Components are URL-decoded to reverse encoding done by build_session_id().

    Parsing rules based on number of parts:
        - 1 part: session only (no namespace)
        - 2 parts: user:session
        - 3 parts: tenant:user:session

    Args:
        session_id: Namespaced session ID string
        separator: Namespace separator (default: ":")
        expected_parts: Expected number of parts (for validation, optional)

    Returns:
        ParsedSessionId with extracted components

    Raises:
        ValueError: If expected_parts is set and doesn't match actual count

    Examples:
        >>> parse_session_id("conv123")
        ParsedSessionId(full_id='conv123', tenant_id=None, user_id=None, session_id='conv123')

        >>> parse_session_id("alice:conv123")
        ParsedSessionId(full_id='alice:conv123', tenant_id=None, user_id='alice', session_id='conv123')

        >>> parse_session_id("acme:alice:conv123")
        ParsedSessionId(full_id='acme:alice:conv123', tenant_id='acme', user_id='alice', session_id='conv123')

        >>> # Values with colons are URL-encoded
        >>> parse_session_id("acme%3Acorp:alice:conv123")  # tenant was "acme:corp"
        ParsedSessionId(full_id='acme%3Acorp:alice:conv123', tenant_id='acme:corp', ...)
    """
    parts = session_id.split(separator)

    if expected_parts is not None and len(parts) != expected_parts:
        raise ValueError(
            f"Expected {expected_parts} parts, got {len(parts)} in '{session_id}'"
        )

    if len(parts) == 1:
        return ParsedSessionId(
            full_id=session_id,
            tenant_id=None,
            user_id=None,
            session_id=_decode_component(parts[0]),
        )
    elif len(parts) == 2:
        return ParsedSessionId(
            full_id=session_id,
            tenant_id=None,
            user_id=_decode_component(parts[0]),
            session_id=_decode_component(parts[1]),
        )
    elif len(parts) == 3:
        # Exactly 3 parts: tenant:user:session
        return ParsedSessionId(
            full_id=session_id,
            tenant_id=_decode_component(parts[0]),
            user_id=_decode_component(parts[1]),
            session_id=_decode_component(parts[2]),
        )
    else:
        # 4+ parts is ambiguous - raise error
        raise ValueError(
            f"Session ID '{session_id}' has {len(parts)} parts. "
            f"Expected 1-3 parts (session, user:session, or tenant:user:session). "
            f"If your IDs contain '{separator}', they should be URL-encoded."
        )


def generate_session_id(
    length: int = 12,
    prefix: str = "",
) -> str:
    """Generate a cryptographically secure session ID.

    Uses UUID4 for cryptographic randomness, truncated to specified length.
    Suitable for production use.

    Args:
        length: Length of random hex string (default: 12, providing ~48 bits of entropy)
        prefix: Optional prefix (e.g., "sess_", "sid_")

    Returns:
        Secure session ID string

    Examples:
        >>> generate_session_id()
        'a1b2c3d4e5f6'

        >>> generate_session_id(prefix="sess_")
        'sess_a1b2c3d4e5f6'

        >>> generate_session_id(length=24)
        'a1b2c3d4e5f67890abcd1234'

    Security Notes:
        - Uses uuid4() which is cryptographically random
        - Default 12 hex chars = ~48 bits of entropy
        - For higher security, increase length to 24+ chars
    """
    random_part = uuid.uuid4().hex[:length]
    return f"{prefix}{random_part}"
