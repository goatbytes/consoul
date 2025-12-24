"""Request validation utilities for FastAPI.

Enhanced request validation with detailed error messages and size limits.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException, Request, status
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class RequestValidator:
    """Enhanced request validation for FastAPI.

    Provides validation utilities with:
    - Detailed validation error messages
    - Request size limits
    - Custom validators
    - Standardized error format

    Example - Basic validation:
        >>> from pydantic import BaseModel
        >>> from consoul.server.middleware import RequestValidator
        >>>
        >>> class ChatRequest(BaseModel):
        ...     session_id: str
        ...     message: str
        >>>
        >>> validator = RequestValidator(max_body_size=1024 * 1024)  # 1MB
        >>>
        >>> @app.post("/chat")
        >>> async def chat(request: Request):
        ...     data = await validator.validate_json(request, ChatRequest)
        ...     return {"status": "ok"}

    Example - With size check:
        >>> validator = RequestValidator(max_body_size=1024 * 100)  # 100KB
        >>> await validator.check_size(request)  # Raises 413 if too large
    """

    def __init__(self, max_body_size: int = 1024 * 1024):
        """Initialize request validator.

        Args:
            max_body_size: Maximum request body size in bytes (default: 1MB)
        """
        self.max_body_size = max_body_size

        logger.info(
            f"RequestValidator initialized: max_body_size={max_body_size} bytes"
        )

    async def check_size(self, request: Request) -> None:
        """Check if request body size is within limit.

        Args:
            request: FastAPI request object

        Raises:
            HTTPException: 413 if body exceeds max size

        Example:
            >>> await validator.check_size(request)
        """
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_body_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail={
                    "error": "Request too large",
                    "message": f"Request body must be less than {self.max_body_size} bytes",
                    "limit": self.max_body_size,
                },
            )

    async def validate_json(
        self,
        request: Request,
        model: type[BaseModel],
    ) -> BaseModel:
        """Validate JSON request body against Pydantic model.

        Args:
            request: FastAPI request object
            model: Pydantic model class

        Returns:
            Validated model instance

        Raises:
            HTTPException: 422 if validation fails
            HTTPException: 400 if JSON parsing fails

        Example:
            >>> class ChatRequest(BaseModel):
            ...     session_id: str
            ...     message: str
            >>>
            >>> data = await validator.validate_json(request, ChatRequest)
            >>> print(data.session_id, data.message)
        """
        # Check size first
        await self.check_size(request)

        # Parse JSON
        try:
            body = await request.json()
        except Exception as e:
            logger.warning(f"JSON parsing failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Invalid JSON",
                    "message": "Request body must be valid JSON",
                },
            ) from e

        # Validate with Pydantic
        try:
            return model.model_validate(body)
        except ValidationError as e:
            logger.warning(f"Validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "Validation error",
                    "message": "Request body failed validation",
                    "errors": e.errors(),
                },
            ) from e

    @staticmethod
    def format_validation_error(error: ValidationError) -> dict[str, Any]:
        """Format Pydantic validation error for API response.

        Args:
            error: Pydantic ValidationError

        Returns:
            Formatted error dictionary

        Example:
            >>> try:
            ...     model.model_validate(data)
            ... except ValidationError as e:
            ...     error_dict = RequestValidator.format_validation_error(e)
            ...     return JSONResponse(status_code=422, content=error_dict)
        """
        return {
            "error": "Validation error",
            "message": "Request failed validation",
            "errors": [
                {
                    "field": ".".join(str(loc) for loc in err["loc"]),
                    "message": err["msg"],
                    "type": err["type"],
                }
                for err in error.errors()
            ],
        }
