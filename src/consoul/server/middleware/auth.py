"""API key authentication middleware for FastAPI.

Provides flexible API key authentication supporting both header and query
parameter authentication with multiple valid keys.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, APIKeyQuery

from consoul.server.errors import ErrorCode, create_error_response

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi import Request

logger = logging.getLogger(__name__)


class APIKeyAuth:
    """API key authentication for FastAPI endpoints.

    Supports authentication via HTTP header or query parameter with multiple
    valid API keys. Provides path-based bypass for health checks and public endpoints.

    Attributes:
        api_keys: Set of valid API keys
        header_name: HTTP header name (default: X-API-Key)
        query_name: Query parameter name (default: api_key)
        bypass_paths: Paths that skip authentication

    Example - Basic usage:
        >>> from fastapi import FastAPI, Depends
        >>> from consoul.server.middleware import APIKeyAuth
        >>>
        >>> app = FastAPI()
        >>> auth = APIKeyAuth(api_keys=["secret-key-1", "secret-key-2"])
        >>>
        >>> @app.post("/chat")
        >>> async def chat(api_key: str = Depends(auth.verify)):
        ...     # api_key is validated
        ...     return {"status": "authenticated"}

    Example - Environment variables:
        >>> import os
        >>> os.environ["CONSOUL_API_KEYS"] = "key1,key2,key3"
        >>> from consoul.server.models import SecurityConfig
        >>>
        >>> config = SecurityConfig()
        >>> auth = APIKeyAuth(api_keys=config.api_keys)

    Example - Path bypass:
        >>> auth = APIKeyAuth(
        ...     api_keys=["secret"],
        ...     bypass_paths=["/health", "/metrics", "/docs"]
        ... )
        >>> # Health endpoint bypasses auth
        >>> @app.get("/health")
        >>> async def health():
        ...     return {"status": "ok"}

    Security Notes:
        - Store API keys in environment variables
        - Use HTTPS in production
        - Rotate keys regularly
        - Log failed authentication attempts
        - Consider rate limiting per key
    """

    def __init__(
        self,
        api_keys: list[str] | None = None,
        header_name: str = "X-API-Key",
        query_name: str = "api_key",
        bypass_paths: list[str] | None = None,
    ):
        """Initialize API key authentication.

        Args:
            api_keys: List of valid API keys (load from environment in production)
            header_name: HTTP header name for API key
            query_name: Query parameter name for API key
            bypass_paths: Paths that skip authentication (e.g., ["/health"])

        Raises:
            ValueError: If no API keys provided
        """
        if not api_keys:
            raise ValueError(
                "At least one API key must be provided. "
                "Set CONSOUL_API_KEYS environment variable or pass api_keys parameter."
            )

        self.api_keys = set(api_keys)
        self.header_name = header_name
        self.query_name = query_name
        self.bypass_paths = set(bypass_paths or ["/health", "/docs", "/openapi.json"])

        # FastAPI security dependencies
        self.header_scheme = APIKeyHeader(name=header_name, auto_error=False)
        self.query_scheme = APIKeyQuery(name=query_name, auto_error=False)

        logger.info(
            f"APIKeyAuth initialized with {len(self.api_keys)} keys, "
            f"bypassing {len(self.bypass_paths)} paths"
        )

    def should_bypass(self, request: Request) -> bool:
        """Check if request path should bypass authentication.

        Args:
            request: FastAPI request object

        Returns:
            True if path is in bypass list
        """
        return request.url.path in self.bypass_paths

    async def verify(
        self,
        request: Request,
        header_key: str | None = Security(lambda: None),
        query_key: str | None = Security(lambda: None),
    ) -> str:
        """Verify API key from header or query parameter.

        Dependency for FastAPI endpoints. Checks header first, then query param.

        Args:
            request: FastAPI request object
            header_key: API key from header (injected by FastAPI)
            query_key: API key from query param (injected by FastAPI)

        Returns:
            Valid API key

        Raises:
            HTTPException: 401 if no key provided or invalid key

        Example:
            >>> @app.post("/endpoint")
            >>> async def endpoint(api_key: str = Depends(auth.verify)):
            ...     # Authenticated, api_key is valid
            ...     pass
        """
        # Skip auth for bypass paths
        if self.should_bypass(request):
            return "bypass"

        # Try header first
        header_key = await self.header_scheme(request)
        if header_key and header_key in self.api_keys:
            return header_key

        # Try query param
        query_key = await self.query_scheme(request)
        if query_key and query_key in self.api_keys:
            return query_key

        # No valid key found
        logger.warning(
            f"Authentication failed for {request.client.host if request.client else 'unknown'} "
            f"on {request.url.path}"
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=create_error_response(
                ErrorCode.INVALID_API_KEY,
                message=f"Provide valid API key via '{self.header_name}' header or '{self.query_name}' query parameter",
            ),
            headers={"WWW-Authenticate": f"ApiKey name={self.header_name}"},
        )

    def create_dependency(self) -> Callable[..., Any]:
        """Create FastAPI dependency for this auth instance.

        Returns:
            Callable dependency for FastAPI Depends()

        Example:
            >>> auth = APIKeyAuth(api_keys=["secret"])
            >>> AuthDep = auth.create_dependency()
            >>>
            >>> @app.post("/endpoint")
            >>> async def endpoint(api_key: str = Depends(AuthDep)):
            ...     pass
        """
        auth_instance = self

        async def dependency(
            request: Request,
            header_key: str | None = Security(auth_instance.header_scheme),
            query_key: str | None = Security(auth_instance.query_scheme),
        ) -> str:
            return await auth_instance.verify(request, header_key, query_key)

        return dependency
