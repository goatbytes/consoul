"""Example SessionHooks implementations for production patterns.

This module provides reference implementations of the SessionHooks protocol
for common use cases like PII redaction, audit logging, validation, and encryption.

These examples demonstrate patterns you can adapt for your own hooks.
They are NOT included in the main SDK package - copy and modify as needed.

Example Usage:
    >>> from consoul.sdk import HookedSessionStore, MemorySessionStore
    >>> from examples.sdk.session_hooks import RedactionHook, AuditHook
    >>>
    >>> # Create hooks
    >>> redaction_hook = RedactionHook(fields=["password", "ssn"])
    >>> audit_hook = AuditHook(logger)
    >>>
    >>> # Wrap store with hooks
    >>> base_store = MemorySessionStore(ttl=3600)
    >>> store = HookedSessionStore(
    ...     store=base_store,
    ...     hooks=[redaction_hook, audit_hook]
    ... )
    >>>
    >>> # Use as normal - hooks applied automatically
    >>> store.save("session_123", state)

Available Hooks:
    - RedactionHook: Redact PII from session messages before storage
    - AuditHook: Log session save/load operations for compliance
    - ValidationHook: Validate session state before storage
    - EncryptionHook: Example encryption pattern (use real crypto in production)

For production encryption, use a real cryptographic library (cryptography, PyNaCl)
and implement your own hook following the EncryptionHook pattern.
"""

from examples.sdk.session_hooks.audit_hook import AuditHook
from examples.sdk.session_hooks.encryption_hook import EncryptionHook
from examples.sdk.session_hooks.redaction_hook import RedactionHook
from examples.sdk.session_hooks.validation_hook import ValidationHook

__all__ = [
    "AuditHook",
    "EncryptionHook",
    "RedactionHook",
    "ValidationHook",
]
