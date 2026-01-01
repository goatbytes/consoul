"""FastAPI router for webhook management endpoints.

Provides REST API endpoints for webhook CRUD operations, delivery
history, testing, and replay functionality.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from consoul.server.webhooks.errors import WebhookErrorCode, get_webhook_error_status
from consoul.server.webhooks.models import (
    DeliveryRecord,
    WebhookCreateRequest,
    WebhookEventType,
    WebhookResponse,
    WebhookUpdateRequest,
)
from consoul.server.webhooks.security import URLValidationError, WebhookURLValidator
from consoul.server.webhooks.store import generate_event_id

if TYPE_CHECKING:
    from consoul.server.webhooks.emitter import WebhookEventEmitter
    from consoul.server.webhooks.store import ResilientWebhookStore

logger = logging.getLogger(__name__)

__all__ = [
    "DeliveryListResponse",
    "TestWebhookResponse",
    "WebhookListResponse",
    "create_webhook_router",
]


# =============================================================================
# Response Models
# =============================================================================


class WebhookListResponse(BaseModel):
    """Response for listing webhooks."""

    webhooks: list[WebhookResponse] = Field(description="List of webhooks")
    count: int = Field(description="Total number of webhooks")


class DeliveryListResponse(BaseModel):
    """Response for listing deliveries."""

    deliveries: list[DeliveryRecord] = Field(description="List of delivery records")
    count: int = Field(description="Number of records returned")


class TestWebhookResponse(BaseModel):
    """Response for test webhook endpoint."""

    success: bool = Field(description="Whether test delivery was enqueued")
    event_id: str = Field(description="ID of the test event")
    message: str = Field(description="Status message")


class ReplayResponse(BaseModel):
    """Response for replay endpoint."""

    success: bool = Field(description="Whether replay was enqueued")
    new_delivery_id: str = Field(description="ID of the new delivery")
    message: str = Field(description="Status message")


class DeleteResponse(BaseModel):
    """Response for delete endpoint."""

    success: bool = Field(description="Whether deletion was successful")
    message: str = Field(description="Status message")


# =============================================================================
# Router Factory
# =============================================================================


def create_webhook_router(
    store: ResilientWebhookStore,
    emitter: WebhookEventEmitter | None = None,
    url_validator: WebhookURLValidator | None = None,
) -> APIRouter:
    """Create FastAPI router for webhook endpoints.

    Args:
        store: Webhook store for persistence
        emitter: Optional event emitter for test/replay
        url_validator: Optional URL validator (created with defaults if not provided)

    Returns:
        Configured APIRouter
    """
    router = APIRouter(tags=["webhooks"])

    if url_validator is None:
        url_validator = WebhookURLValidator(allow_localhost=False)

    # -------------------------------------------------------------------------
    # Dependency: Get API key from request
    # -------------------------------------------------------------------------

    async def get_api_key(request: Request) -> str:
        """Extract API key from request for ownership verification."""
        # Try header first
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return str(api_key)

        # Try query parameter
        api_key_param = request.query_params.get("api_key")
        if api_key_param:
            return str(api_key_param)

        # Check if stored in request state (set by auth middleware)
        if hasattr(request.state, "api_key"):
            return str(request.state.api_key)

        raise HTTPException(
            status_code=401,
            detail={"code": "E010", "message": "API key required"},
        )

    # -------------------------------------------------------------------------
    # POST /webhooks - Register webhook
    # -------------------------------------------------------------------------

    @router.post(  # type: ignore[misc]
        "",
        response_model=WebhookResponse,
        status_code=201,
        summary="Register a new webhook",
        responses={
            201: {"description": "Webhook created successfully"},
            400: {"description": "Invalid URL or request"},
            401: {"description": "Authentication required"},
        },
    )
    async def create_webhook(
        request: WebhookCreateRequest,
        api_key: str = Depends(get_api_key),
    ) -> WebhookResponse:
        """Register a new webhook.

        Creates a webhook subscription for the specified events.
        The webhook URL must be HTTPS and publicly accessible.
        """
        # Validate URL
        try:
            url_validator.validate(request.url)
        except URLValidationError as e:
            raise HTTPException(
                status_code=get_webhook_error_status(
                    WebhookErrorCode.WEBHOOK_URL_INVALID
                ),
                detail={
                    "code": WebhookErrorCode.WEBHOOK_URL_INVALID.value,
                    "message": str(e.reason),
                },
            ) from e

        # Validate secret length
        if len(request.secret) < 16:
            raise HTTPException(
                status_code=get_webhook_error_status(
                    WebhookErrorCode.WEBHOOK_SECRET_INVALID
                ),
                detail={
                    "code": WebhookErrorCode.WEBHOOK_SECRET_INVALID.value,
                    "message": "Secret must be at least 16 characters",
                },
            )

        # Create webhook
        webhook = store.create_webhook(api_key, request)

        logger.info(f"Created webhook {webhook.id} for {request.url}")
        return webhook

    # -------------------------------------------------------------------------
    # GET /webhooks - List webhooks
    # -------------------------------------------------------------------------

    @router.get(  # type: ignore[misc]
        "",
        response_model=WebhookListResponse,
        summary="List all webhooks",
        responses={
            200: {"description": "List of webhooks"},
            401: {"description": "Authentication required"},
        },
    )
    async def list_webhooks(
        api_key: str = Depends(get_api_key),
    ) -> WebhookListResponse:
        """List all webhooks owned by the authenticated API key."""
        webhooks = store.list_webhooks(api_key)
        return WebhookListResponse(webhooks=webhooks, count=len(webhooks))

    # -------------------------------------------------------------------------
    # GET /webhooks/{id} - Get webhook details
    # -------------------------------------------------------------------------

    @router.get(  # type: ignore[misc]
        "/{webhook_id}",
        response_model=WebhookResponse,
        summary="Get webhook details",
        responses={
            200: {"description": "Webhook details"},
            401: {"description": "Authentication required"},
            403: {"description": "Not authorized to access this webhook"},
            404: {"description": "Webhook not found"},
        },
    )
    async def get_webhook(
        webhook_id: str,
        api_key: str = Depends(get_api_key),
    ) -> WebhookResponse:
        """Get details for a specific webhook."""
        webhook = store.get_webhook(webhook_id, api_key)

        if not webhook:
            raise HTTPException(
                status_code=get_webhook_error_status(
                    WebhookErrorCode.WEBHOOK_NOT_FOUND
                ),
                detail={
                    "code": WebhookErrorCode.WEBHOOK_NOT_FOUND.value,
                    "message": f"Webhook {webhook_id} not found",
                },
            )

        return webhook

    # -------------------------------------------------------------------------
    # PATCH /webhooks/{id} - Update webhook
    # -------------------------------------------------------------------------

    @router.patch(  # type: ignore[misc]
        "/{webhook_id}",
        response_model=WebhookResponse,
        summary="Update webhook",
        responses={
            200: {"description": "Webhook updated"},
            400: {"description": "Invalid URL or request"},
            401: {"description": "Authentication required"},
            404: {"description": "Webhook not found"},
        },
    )
    async def update_webhook(
        webhook_id: str,
        request: WebhookUpdateRequest,
        api_key: str = Depends(get_api_key),
    ) -> WebhookResponse:
        """Update a webhook.

        Only provided fields are updated. The secret can be rotated
        by providing a new value.
        """
        # Validate new URL if provided
        if request.url:
            try:
                url_validator.validate(request.url)
            except URLValidationError as e:
                raise HTTPException(
                    status_code=get_webhook_error_status(
                        WebhookErrorCode.WEBHOOK_URL_INVALID
                    ),
                    detail={
                        "code": WebhookErrorCode.WEBHOOK_URL_INVALID.value,
                        "message": str(e.reason),
                    },
                ) from e

        # Validate new secret if provided
        if request.secret and len(request.secret) < 16:
            raise HTTPException(
                status_code=get_webhook_error_status(
                    WebhookErrorCode.WEBHOOK_SECRET_INVALID
                ),
                detail={
                    "code": WebhookErrorCode.WEBHOOK_SECRET_INVALID.value,
                    "message": "Secret must be at least 16 characters",
                },
            )

        webhook = store.update_webhook(webhook_id, api_key, request)

        if not webhook:
            raise HTTPException(
                status_code=get_webhook_error_status(
                    WebhookErrorCode.WEBHOOK_NOT_FOUND
                ),
                detail={
                    "code": WebhookErrorCode.WEBHOOK_NOT_FOUND.value,
                    "message": f"Webhook {webhook_id} not found",
                },
            )

        logger.info(f"Updated webhook {webhook_id}")
        return webhook

    # -------------------------------------------------------------------------
    # DELETE /webhooks/{id} - Delete webhook
    # -------------------------------------------------------------------------

    @router.delete(  # type: ignore[misc]
        "/{webhook_id}",
        response_model=DeleteResponse,
        summary="Delete webhook",
        responses={
            200: {"description": "Webhook deleted"},
            401: {"description": "Authentication required"},
            404: {"description": "Webhook not found"},
        },
    )
    async def delete_webhook(
        webhook_id: str,
        api_key: str = Depends(get_api_key),
    ) -> DeleteResponse:
        """Delete a webhook.

        This will cancel any pending deliveries for this webhook.
        """
        deleted = store.delete_webhook(webhook_id, api_key)

        if not deleted:
            raise HTTPException(
                status_code=get_webhook_error_status(
                    WebhookErrorCode.WEBHOOK_NOT_FOUND
                ),
                detail={
                    "code": WebhookErrorCode.WEBHOOK_NOT_FOUND.value,
                    "message": f"Webhook {webhook_id} not found",
                },
            )

        logger.info(f"Deleted webhook {webhook_id}")
        return DeleteResponse(success=True, message=f"Webhook {webhook_id} deleted")

    # -------------------------------------------------------------------------
    # GET /webhooks/{id}/deliveries - Delivery history
    # -------------------------------------------------------------------------

    @router.get(  # type: ignore[misc]
        "/{webhook_id}/deliveries",
        response_model=DeliveryListResponse,
        summary="Get delivery history",
        responses={
            200: {"description": "Delivery history"},
            401: {"description": "Authentication required"},
            404: {"description": "Webhook not found"},
        },
    )
    async def get_deliveries(
        webhook_id: str,
        limit: int = 50,
        api_key: str = Depends(get_api_key),
    ) -> DeliveryListResponse:
        """Get delivery history for a webhook.

        Returns the most recent delivery attempts, including status,
        response codes, and error messages.
        """
        # Verify webhook exists and is owned by this API key
        webhook = store.get_webhook(webhook_id, api_key)
        if not webhook:
            raise HTTPException(
                status_code=get_webhook_error_status(
                    WebhookErrorCode.WEBHOOK_NOT_FOUND
                ),
                detail={
                    "code": WebhookErrorCode.WEBHOOK_NOT_FOUND.value,
                    "message": f"Webhook {webhook_id} not found",
                },
            )

        deliveries = store.get_delivery_history(webhook_id, limit=min(limit, 100))
        return DeliveryListResponse(deliveries=deliveries, count=len(deliveries))

    # -------------------------------------------------------------------------
    # POST /webhooks/{id}/test - Send test event
    # -------------------------------------------------------------------------

    @router.post(  # type: ignore[misc]
        "/{webhook_id}/test",
        response_model=TestWebhookResponse,
        summary="Send test event",
        responses={
            200: {"description": "Test event enqueued"},
            401: {"description": "Authentication required"},
            404: {"description": "Webhook not found"},
            503: {"description": "Webhook delivery not available"},
        },
    )
    async def test_webhook(
        webhook_id: str,
        api_key: str = Depends(get_api_key),
    ) -> TestWebhookResponse:
        """Send a test event to the webhook.

        Enqueues a test event with sample data to verify webhook
        configuration and connectivity.
        """
        # Verify webhook exists and is owned by this API key
        webhook = store.get_webhook(webhook_id, api_key)
        if not webhook:
            raise HTTPException(
                status_code=get_webhook_error_status(
                    WebhookErrorCode.WEBHOOK_NOT_FOUND
                ),
                detail={
                    "code": WebhookErrorCode.WEBHOOK_NOT_FOUND.value,
                    "message": f"Webhook {webhook_id} not found",
                },
            )

        if emitter is None:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "E900",
                    "message": "Webhook delivery service not available",
                },
            )

        # Use first subscribed event type for test
        event_type = (
            webhook.events[0] if webhook.events else WebhookEventType.CHAT_COMPLETED
        )

        # Create test data based on event type
        test_data: dict[str, Any] = {
            "test": True,
            "webhook_id": webhook_id,
            "message": "This is a test webhook delivery",
        }

        if event_type == WebhookEventType.CHAT_COMPLETED:
            test_data.update(
                {
                    "session_id": "test-session",
                    "response": "This is a test response from Consoul.",
                    "usage": {"input_tokens": 10, "output_tokens": 15},
                }
            )
        elif event_type == WebhookEventType.CHAT_ERROR:
            test_data.update(
                {
                    "session_id": "test-session",
                    "error_code": "E000",
                    "message": "This is a test error",
                }
            )
        elif event_type == WebhookEventType.BATCH_COMPLETED:
            test_data.update(
                {
                    "session_id": "test-session",
                    "message_count": 5,
                    "success_count": 5,
                    "error_count": 0,
                }
            )

        event_id = generate_event_id()

        try:
            delivery_ids = await emitter.emit(
                event_type=event_type,
                data=test_data,
                owner_id=api_key,
                event_id=event_id,
            )

            if delivery_ids:
                return TestWebhookResponse(
                    success=True,
                    event_id=event_id,
                    message="Test event enqueued for delivery",
                )
            else:
                return TestWebhookResponse(
                    success=False,
                    event_id=event_id,
                    message="No matching webhooks found for delivery",
                )

        except Exception as e:
            logger.error(f"Failed to enqueue test event: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "code": "E900",
                    "message": f"Failed to enqueue test event: {e}",
                },
            ) from e

    # -------------------------------------------------------------------------
    # POST /webhooks/{id}/deliveries/{delivery_id}/replay - Replay delivery
    # -------------------------------------------------------------------------

    @router.post(  # type: ignore[misc]
        "/{webhook_id}/deliveries/{delivery_id}/replay",
        response_model=ReplayResponse,
        summary="Replay a delivery",
        responses={
            200: {"description": "Replay enqueued"},
            401: {"description": "Authentication required"},
            404: {"description": "Webhook or delivery not found"},
            410: {"description": "Delivery has expired"},
        },
    )
    async def replay_delivery(
        webhook_id: str,
        delivery_id: str,
        api_key: str = Depends(get_api_key),
    ) -> ReplayResponse:
        """Replay a previous delivery.

        Re-enqueues a failed or expired delivery for retry. The original
        event data is preserved.
        """
        # Verify webhook exists and is owned by this API key
        webhook = store.get_webhook(webhook_id, api_key)
        if not webhook:
            raise HTTPException(
                status_code=get_webhook_error_status(
                    WebhookErrorCode.WEBHOOK_NOT_FOUND
                ),
                detail={
                    "code": WebhookErrorCode.WEBHOOK_NOT_FOUND.value,
                    "message": f"Webhook {webhook_id} not found",
                },
            )

        # Get the delivery record
        delivery = store.get_delivery(delivery_id)
        if not delivery:
            raise HTTPException(
                status_code=get_webhook_error_status(
                    WebhookErrorCode.DELIVERY_NOT_FOUND
                ),
                detail={
                    "code": WebhookErrorCode.DELIVERY_NOT_FOUND.value,
                    "message": f"Delivery {delivery_id} not found",
                },
            )

        if delivery.webhook_id != webhook_id:
            raise HTTPException(
                status_code=get_webhook_error_status(
                    WebhookErrorCode.DELIVERY_NOT_FOUND
                ),
                detail={
                    "code": WebhookErrorCode.DELIVERY_NOT_FOUND.value,
                    "message": f"Delivery {delivery_id} not found for webhook {webhook_id}",
                },
            )

        if emitter is None:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "E900",
                    "message": "Webhook delivery service not available",
                },
            )

        # Check if we have the original event data
        if not delivery.event_data:
            raise HTTPException(
                status_code=410,
                detail={
                    "code": WebhookErrorCode.DELIVERY_EXPIRED.value,
                    "message": "Original event data not available for replay",
                },
            )

        # Re-emit the event with original data
        try:
            # Use original event data with replay metadata
            replay_data = {
                **delivery.event_data,
                "_replay": {
                    "original_delivery_id": delivery_id,
                    "original_event_id": delivery.event_id,
                },
            }

            new_event_id = generate_event_id()
            delivery_ids = await emitter.emit(
                event_type=delivery.event_type,
                data=replay_data,
                owner_id=api_key,
                event_id=new_event_id,
            )

            if delivery_ids:
                return ReplayResponse(
                    success=True,
                    new_delivery_id=delivery_ids[0],
                    message="Replay enqueued successfully",
                )
            else:
                return ReplayResponse(
                    success=False,
                    new_delivery_id="",
                    message="No matching webhooks found for replay",
                )

        except Exception as e:
            logger.error(f"Failed to replay delivery: {e}")
            raise HTTPException(
                status_code=get_webhook_error_status(
                    WebhookErrorCode.DELIVERY_REPLAY_FAILED
                ),
                detail={
                    "code": WebhookErrorCode.DELIVERY_REPLAY_FAILED.value,
                    "message": f"Failed to replay delivery: {e}",
                },
            ) from e

    return router
