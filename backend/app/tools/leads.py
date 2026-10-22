"""C2: lead capture helpers. Email validation is code, never a model."""

from __future__ import annotations

import re
import time
import uuid

from app.storage.crypto import Box
from app.storage.db import DB

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
REQUIRED = ("name", "email")
ORDER = ("name", "company", "about", "email")


def find_email(text: str) -> str | None:
    m = EMAIL_RE.search(text)
    return m.group(0).lower() if m else None


def missing(slots: dict) -> list[str]:
    return [k for k in ORDER if not slots.get(k) and (k in REQUIRED or k not in slots)]


async def save_lead(db: DB, box: Box, session_id: str, slots: dict) -> str:
    lead_id = f"lead-{uuid.uuid4().hex[:12]}"
    await db.execute(
        "INSERT INTO leads(id, session_id, name_enc, company_enc, role_enc, email_enc, about_enc, created_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (lead_id, session_id, box.seal(slots.get("name")), box.seal(slots.get("company")),
         box.seal(slots.get("role")), box.seal(slots.get("email")), box.seal(slots.get("about")), time.time()),
    )
    return lead_id
