"""Encryption hook example for session state.

IMPORTANT: This is an EXAMPLE implementation demonstrating the hook pattern.
DO NOT use this in production. For real encryption, use a proper
cryptographic library like `cryptography` or `PyNaCl`.

This example shows the hook structure for encryption/decryption.
Replace the placeholder methods with real cryptographic implementations.

Example (production pattern):
    >>> from cryptography.fernet import Fernet
    >>>
    >>> class ProductionEncryptionHook:
    ...     def __init__(self, key: bytes):
    ...         self.fernet = Fernet(key)
    ...
    ...     def on_before_save(self, session_id, state):
    ...         # Encrypt message content before storage
    ...         encrypted_messages = []
    ...         for msg in state.get("messages", []):
    ...             content = msg.get("content", "")
    ...             encrypted = self.fernet.encrypt(content.encode())
    ...             encrypted_messages.append({
    ...                 **msg,
    ...                 "content": encrypted.decode(),
    ...                 "_encrypted": True
    ...             })
    ...         return {**state, "messages": encrypted_messages}
    ...
    ...     def on_after_load(self, session_id, state):
    ...         if state is None:
    ...             return None
    ...         # Decrypt message content after loading
    ...         decrypted_messages = []
    ...         for msg in state.get("messages", []):
    ...             if msg.get("_encrypted"):
    ...                 content = msg["content"]
    ...                 decrypted = self.fernet.decrypt(content.encode())
    ...                 msg = {k: v for k, v in msg.items() if k != "_encrypted"}
    ...                 msg["content"] = decrypted.decode()
    ...             decrypted_messages.append(msg)
    ...         return {**state, "messages": decrypted_messages}
"""

from __future__ import annotations

import base64
from typing import Any


class EncryptionHook:
    """Example encryption hook demonstrating the hook pattern.

    WARNING: This uses XOR "encryption" for demonstration only.
    DO NOT use in production - use proper cryptography instead.

    This example shows:
    - How to transform state before save (encrypt)
    - How to transform state after load (decrypt)
    - How to mark encrypted content for selective decryption

    For production use, replace _encrypt/_decrypt with real crypto:
    - Use `cryptography.fernet.Fernet` for symmetric encryption
    - Use envelope encryption with cloud KMS for key management
    - Consider field-level encryption for granular access control

    Attributes:
        key: Encryption key (in production, use proper key management)
        encrypt_fields: Fields to encrypt (default: ["content"])
    """

    def __init__(
        self,
        key: str = "EXAMPLE_KEY_DO_NOT_USE",
        encrypt_fields: list[str] | None = None,
    ) -> None:
        """Initialize encryption hook.

        Args:
            key: Encryption key (EXAMPLE ONLY - use proper key management)
            encrypt_fields: Message fields to encrypt
        """
        self.key = key.encode()
        self.encrypt_fields = encrypt_fields or ["content"]

    def _xor_cipher(self, data: bytes) -> bytes:
        """XOR cipher (INSECURE - for demonstration only).

        DO NOT use in production. Replace with proper encryption.
        """
        key_len = len(self.key)
        return bytes(b ^ self.key[i % key_len] for i, b in enumerate(data))

    def _encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext (EXAMPLE - use real crypto in production)."""
        encrypted = self._xor_cipher(plaintext.encode("utf-8"))
        return base64.b64encode(encrypted).decode("ascii")

    def _decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext (EXAMPLE - use real crypto in production)."""
        encrypted = base64.b64decode(ciphertext.encode("ascii"))
        decrypted = self._xor_cipher(encrypted)
        return decrypted.decode("utf-8")

    def _encrypt_message(self, msg: dict[str, Any]) -> dict[str, Any]:
        """Encrypt specified fields in a message."""
        result = msg.copy()
        for field in self.encrypt_fields:
            if field in result and isinstance(result[field], str):
                result[field] = self._encrypt(result[field])
        result["_encrypted"] = True
        return result

    def _decrypt_message(self, msg: dict[str, Any]) -> dict[str, Any]:
        """Decrypt specified fields in a message."""
        import contextlib

        if not msg.get("_encrypted"):
            return msg

        result = {k: v for k, v in msg.items() if k != "_encrypted"}
        for field in self.encrypt_fields:
            if field in result and isinstance(result[field], str):
                with contextlib.suppress(Exception):
                    result[field] = self._decrypt(result[field])
        return result

    def on_before_save(
        self,
        session_id: str,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Encrypt message content before saving.

        Args:
            session_id: Session identifier
            state: Session state dictionary

        Returns:
            State with encrypted message content
        """
        messages = state.get("messages", [])
        encrypted_messages = [
            self._encrypt_message(msg) if isinstance(msg, dict) else msg
            for msg in messages
        ]
        return {**state, "messages": encrypted_messages, "_content_encrypted": True}

    def on_after_load(
        self,
        session_id: str,
        state: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Decrypt message content after loading.

        Args:
            session_id: Session identifier
            state: Session state dictionary

        Returns:
            State with decrypted message content
        """
        if state is None:
            return None

        if not state.get("_content_encrypted"):
            return state

        messages = state.get("messages", [])
        decrypted_messages = [
            self._decrypt_message(msg) if isinstance(msg, dict) else msg
            for msg in messages
        ]

        # Remove encryption marker
        result = {k: v for k, v in state.items() if k != "_content_encrypted"}
        result["messages"] = decrypted_messages
        return result

    def on_after_save(
        self,
        session_id: str,
        state: dict[str, Any],
    ) -> None:
        """No-op for encryption hook.

        Args:
            session_id: Session identifier
            state: Session state dictionary
        """
        pass
