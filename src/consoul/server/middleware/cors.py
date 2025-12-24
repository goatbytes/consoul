"""CORS configuration helper for FastAPI.

Provides production-safe CORS configuration with sensible defaults.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi.middleware.cors import CORSMiddleware

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)


def configure_cors(
    app: FastAPI,
    allowed_origins: list[str] | None = None,
    allow_credentials: bool = True,
    allow_methods: list[str] | None = None,
    allow_headers: list[str] | None = None,
    max_age: int = 600,
) -> None:
    """Configure CORS middleware with production-safe defaults.

    Args:
        app: FastAPI application instance
        allowed_origins: List of allowed origins (default: ["*"], use specific domains in production)
        allow_credentials: Whether to allow credentials (default: True)
        allow_methods: Allowed HTTP methods (default: ["*"])
        allow_headers: Allowed HTTP headers (default: ["*"])
        max_age: Preflight cache duration in seconds (default: 600)

    Security Notes:
        - NEVER use ["*"] for allowed_origins with allow_credentials=True in production
        - Always specify exact origins for production (e.g., ["https://app.example.com"])
        - Use HTTPS for all origins in production
        - Restrict methods and headers as needed

    Example - Development (permissive):
        >>> from fastapi import FastAPI
        >>> from consoul.server.middleware import configure_cors
        >>>
        >>> app = FastAPI()
        >>> configure_cors(app)  # Allows all origins

    Example - Production (strict):
        >>> configure_cors(
        ...     app,
        ...     allowed_origins=[
        ...         "https://app.example.com",
        ...         "https://admin.example.com"
        ...     ],
        ...     allow_credentials=True,
        ...     allow_methods=["GET", "POST", "PUT", "DELETE"],
        ...     allow_headers=["Content-Type", "Authorization", "X-API-Key"]
        ... )

    Example - Mixed (API + docs):
        >>> configure_cors(
        ...     app,
        ...     allowed_origins=["https://app.example.com", "http://localhost:3000"],
        ...     allow_credentials=True
        ... )
    """
    # Validate configuration
    if allowed_origins is None:
        allowed_origins = ["*"]
        logger.warning(
            "CORS configured with wildcard origin ['*']. "
            "This is insecure for production! "
            "Specify exact origins: allowed_origins=['https://app.example.com']"
        )

    if "*" in allowed_origins and allow_credentials:
        logger.error(
            "CORS misconfiguration: wildcard origin ['*'] with allow_credentials=True "
            "is not allowed by browsers. Either specify exact origins or set "
            "allow_credentials=False."
        )

    # Apply CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=allow_credentials,
        allow_methods=allow_methods or ["*"],
        allow_headers=allow_headers or ["*"],
        max_age=max_age,
    )

    logger.info(
        f"CORS configured: origins={len(allowed_origins)}, "
        f"credentials={allow_credentials}, methods={allow_methods or '*'}"
    )
