"""Rate limiting middleware using slowapi (Flask-Limiter for FastAPI).

Provides token bucket rate limiting with in-memory or Redis storage for
distributed systems.
"""

from __future__ import annotations

import fnmatch
import logging
from typing import TYPE_CHECKING, Any

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi import FastAPI, Request

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token bucket rate limiter for FastAPI.

    Wrapper around slowapi providing rate limiting with multiple strategies:
    - Per API key
    - Per IP address
    - Per user ID
    - Global limits

    Attributes:
        limiter: Slowapi Limiter instance
        key_func: Function to extract rate limit key from request

    Example - Basic usage (per-IP):
        >>> from consoul.server.middleware import RateLimiter
        >>> from fastapi import FastAPI
        >>>
        >>> app = FastAPI()
        >>> limiter = RateLimiter(default_limits=["10 per minute"])
        >>> limiter.init_app(app)
        >>>
        >>> @app.post("/chat")
        >>> @limiter.limit("10/minute")
        >>> async def chat():
        ...     return {"status": "ok"}

    Example - Per API key:
        >>> def get_api_key(request: Request) -> str:
        ...     return request.headers.get("X-API-Key", get_remote_address(request))
        >>>
        >>> limiter = RateLimiter(
        ...     default_limits=["100 per hour"],
        ...     key_func=get_api_key
        ... )

    Example - Redis backend (distributed):
        >>> limiter = RateLimiter(
        ...     default_limits=["10/minute"],
        ...     storage_url="redis://localhost:6379"
        ... )

    Example - Multiple limits:
        >>> @app.post("/chat")
        >>> @limiter.limit("10/minute;100/hour;1000/day")
        >>> async def chat():
        ...     pass
    """

    def __init__(
        self,
        default_limits: list[str] | None = None,
        key_func: Callable[[Request], str] | None = None,
        storage_url: str | None = None,
        key_prefix: str = "consoul:ratelimit",
        enabled: bool = True,
    ):
        """Initialize rate limiter.

        Args:
            default_limits: Default rate limits (e.g., ["10 per minute"])
            key_func: Function to extract rate limit key (default: IP address)
            storage_url: Redis URL for distributed limiting (e.g., "redis://localhost:6379")
            key_prefix: Redis key prefix
            enabled: Whether rate limiting is enabled

        Example:
            >>> limiter = RateLimiter(
            ...     default_limits=["10 per minute", "100 per hour"],
            ...     storage_url="redis://localhost:6379"
            ... )
        """
        self.enabled = enabled
        self.default_limits = default_limits or ["10 per minute"]
        self.key_func = key_func or get_remote_address
        self.storage_url = storage_url
        self.key_prefix = key_prefix

        # Initialize slowapi limiter
        self.limiter = Limiter(
            key_func=self.key_func,
            default_limits=self.default_limits,
            storage_uri=storage_url,
            storage_options={"socket_connect_timeout": 30, "socket_timeout": 30}
            if storage_url
            else {},
            key_prefix=key_prefix,
            enabled=enabled,
        )

        logger.info(
            f"RateLimiter initialized: limits={self.default_limits}, "
            f"storage={'Redis' if storage_url else 'in-memory'}, enabled={enabled}"
        )

    def init_app(self, app: FastAPI) -> None:
        """Initialize rate limiter with FastAPI app.

        Adds rate limit exception handler and state.

        Args:
            app: FastAPI application instance

        Example:
            >>> app = FastAPI()
            >>> limiter = RateLimiter()
            >>> limiter.init_app(app)
        """
        # Add limiter to app state
        app.state.limiter = self.limiter

        # Add exception handler for rate limit exceeded
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

        logger.info("RateLimiter integrated with FastAPI app")

    def limit(
        self, limit_value: str | Callable[[], str] | Callable[[Request], str]
    ) -> Any:
        """Decorator to apply rate limit to endpoint.

        Args:
            limit_value: Rate limit string (e.g., "10/minute", "10 per minute;100 per hour")
                or a callable that returns a limit string. The callable can either:
                - Take no arguments (reads request from ContextVar, SOUL-348 pattern)
                - Take a Request argument (legacy pattern, note: slowapi doesn't pass request)

        Returns:
            Decorator function

        Example - Static limit:
            >>> @app.post("/chat")
            >>> @limiter.limit("10/minute")
            >>> async def chat():
            ...     return {"status": "ok"}

        Example - Dynamic limit with ContextVar (recommended):
            >>> def get_limit() -> str:
            ...     request = get_current_request()
            ...     if request and is_premium(request):
            ...         return "100/minute"
            ...     return "10/minute"
            >>>
            >>> @app.post("/chat")
            >>> @limiter.limit(get_limit)
            >>> async def chat():
            ...     return {"status": "ok"}
        """
        return self.limiter.limit(limit_value)

    def exempt(self, func: Any) -> Any:
        """Decorator to exempt endpoint from rate limiting.

        Args:
            func: Endpoint function

        Returns:
            Decorated function

        Example:
            >>> @app.get("/health")
            >>> @limiter.exempt
            >>> async def health():
            ...     return {"status": "ok"}
        """
        return self.limiter.exempt(func)


def create_api_key_limiter(
    header_name: str = "X-API-Key",
    default_limits: list[str] | None = None,
    storage_url: str | None = None,
) -> RateLimiter:
    """Create rate limiter that limits per API key.

    Convenience factory for per-API-key rate limiting.

    Args:
        header_name: HTTP header containing API key
        default_limits: Default rate limits
        storage_url: Redis URL for distributed limiting

    Returns:
        RateLimiter instance configured for per-API-key limiting

    Example:
        >>> limiter = create_api_key_limiter(
        ...     header_name="X-API-Key",
        ...     default_limits=["100 per hour"],
        ...     storage_url="redis://localhost:6379"
        ... )
        >>> limiter.init_app(app)
    """

    def get_api_key(request: Request) -> str:
        """Extract API key from request header."""
        key = request.headers.get(header_name)
        if key:
            return str(key)
        return str(get_remote_address(request))

    return RateLimiter(
        default_limits=default_limits,
        key_func=get_api_key,
        storage_url=storage_url,
    )


def create_tiered_limit_func(
    tier_limits: dict[str, str],
    api_key_tiers: dict[str, str],
    default_limit: str,
    header_name: str = "X-API-Key",
) -> Callable[[Request], str]:
    """Create dynamic limit function based on API key tier.

    Uses glob-style pattern matching (fnmatch) to map API keys to tiers.
    First matching pattern wins, so order patterns from most specific to least.

    Args:
        tier_limits: Mapping of tier name to rate limit string
            (e.g., {"premium": "100/minute", "basic": "30/minute"})
        api_key_tiers: Mapping of API key patterns to tier names
            (e.g., {"sk-premium-*": "premium", "sk-basic-*": "basic"})
        default_limit: Fallback limit when no pattern matches
        header_name: HTTP header containing the API key

    Returns:
        Callable that extracts limit string from request

    Example:
        >>> limit_func = create_tiered_limit_func(
        ...     tier_limits={"premium": "100/minute", "basic": "30/minute"},
        ...     api_key_tiers={"sk-premium-*": "premium", "sk-basic-*": "basic"},
        ...     default_limit="10/minute",
        ... )
        >>> @app.post("/chat")
        >>> @limiter.limit(limit_func)
        >>> async def chat():
        ...     pass
    """
    # Pre-convert to list to ensure consistent ordering
    patterns = list(api_key_tiers.items())

    def get_limit(request: Request) -> str:
        api_key = request.headers.get(header_name, "")

        for pattern, tier in patterns:
            if fnmatch.fnmatch(api_key, pattern):
                limit = tier_limits.get(tier)
                if limit is None:
                    logger.warning(
                        f"Tier '{tier}' not found in tier_limits, "
                        f"using default limit for key pattern '{pattern}'"
                    )
                    # Store tier info for debugging
                    request.state.rate_limit_tier = f"{tier} (missing, default)"
                    return default_limit
                # Store resolved tier in request.state for debugging/logging
                request.state.rate_limit_tier = tier
                return limit

        # No pattern matched
        request.state.rate_limit_tier = "default"
        return default_limit

    return get_limit
