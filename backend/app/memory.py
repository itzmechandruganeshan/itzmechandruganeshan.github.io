import json
import time
from typing import List, Dict, Optional

class MemoryManager:
    def __init__(self, ttl_seconds: int = 86400): # 1 day TTL
        self.ttl = ttl_seconds
        # In-memory storage: session_id -> list of message dicts
        self._store: Dict[str, List[Dict[str, str]]] = {}
        self._last_accessed: Dict[str, float] = {}

    def _cleanup(self):
        """Removes expired sessions from memory to prevent memory leaks."""
        now = time.time()
        expired = [sid for sid, last in self._last_accessed.items() if now - last > self.ttl]
        for sid in expired:
            self._store.pop(sid, None)
            self._last_accessed.pop(sid, None)

    async def get_history(self, session_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """Retrieves the recent conversation history for a session."""
        self._cleanup()
        self._last_accessed[session_id] = time.time()
        history = self._store.get(session_id, [])
        # Return the last 'limit' items
        return history[-limit:]

    async def add_message(self, session_id: str, role: str, content: str):
        """Appends a new message to the session history."""
        self._cleanup()
        self._last_accessed[session_id] = time.time()
        if session_id not in self._store:
            self._store[session_id] = []
        self._store[session_id].append({"role": role, "content": content})

    async def get_context(self, session_id: str) -> str:
        """Formats the recent history into a text block for the LLM prompt."""
        history = await self.get_history(session_id)
        if not history:
            return ""
        
        context_lines = []
        for msg in history:
            role_prefix = "User" if msg["role"] == "user" else "Digital Chandru"
            context_lines.append(f"{role_prefix}: {msg['content']}")
        return "\n".join(context_lines)

memory_manager = MemoryManager()
