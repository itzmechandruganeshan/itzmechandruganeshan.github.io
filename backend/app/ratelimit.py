"""In-memory sliding-window limits (single machine, ADR-005)."""

from __future__ import annotations

import hashlib
import time
from collections import defaultdict, deque


class Limiter:
    def __init__(self):
        self.events: dict[str, deque] = defaultdict(deque)
        self._hits = 0

    def hit(self, key: str, limit: int, window_s: float) -> bool:
        """Records an event; returns False if the key is over its limit."""
        now = time.monotonic()
        self._hits += 1
        if self._hits % 1000 == 0:  # forget keys idle for a day (the longest window), so the dict doesn't only grow
            for k in [k for k, v in self.events.items() if not v or now - v[-1] > 86400]:
                del self.events[k]
        q = self.events[key]
        while q and now - q[0] > window_s:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        return True


def ip_key(ip: str | None) -> str:
    return "ip:" + hashlib.sha256((ip or "?").encode()).hexdigest()[:16]
