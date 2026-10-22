"""AES-GCM for lead/visitor PII at rest. Key from LEAD_KEY_B64 (Fly secret)."""

from __future__ import annotations

import base64
import logging
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

log = logging.getLogger(__name__)


class Box:
    def __init__(self, key_b64: str, *, prod: bool):
        if key_b64:
            key = base64.b64decode(key_b64)
        elif prod:
            raise RuntimeError("LEAD_KEY_B64 is required in prod")
        else:
            log.warning("LEAD_KEY_B64 not set: using an ephemeral dev key (data unreadable after restart)")
            key = AESGCM.generate_key(bit_length=256)
        if len(key) != 32:
            raise RuntimeError("LEAD_KEY_B64 must decode to 32 bytes")
        self._aes = AESGCM(key)

    def seal(self, text: str | None) -> bytes | None:
        if text is None:
            return None
        nonce = os.urandom(12)
        return nonce + self._aes.encrypt(nonce, text.encode(), None)

    def open(self, blob: bytes | None) -> str | None:
        if blob is None:
            return None
        return self._aes.decrypt(blob[:12], blob[12:], None).decode()
