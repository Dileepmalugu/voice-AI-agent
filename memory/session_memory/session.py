"""
Session Memory Manager
Stores short-term conversation context in Redis with TTL.
"""
import json
from typing import Any, Dict

SESSION_TTL_SECONDS = 3600  # 1 hour


class SessionMemoryManager:
    def __init__(self, redis_client):
        self.redis = redis_client

    def _key(self, session_id: str) -> str:
        return f"session:{session_id}"

    async def get(self, session_id: str) -> Dict[str, Any]:
        """Load session context. Returns empty dict if not found."""
        raw = await self.redis.get(self._key(session_id))
        if raw:
            return json.loads(raw)
        return {"history": [], "patient_id": session_id}

    async def update(self, session_id: str, updates: Dict[str, Any]) -> None:
        """Merge updates into session and save with TTL."""
        ctx = await self.get(session_id)

        # Append to conversation history
        if "last_utterance" in updates and "last_response" in updates:
            ctx.setdefault("history", []).extend([
                {"role": "user",      "content": updates["last_utterance"]},
                {"role": "assistant", "content": updates["last_response"]},
            ])
            # Keep last 10 turns (20 messages)
            ctx["history"] = ctx["history"][-20:]

        # Merge other fields
        for k, v in updates.items():
            if k not in ("last_utterance", "last_response"):
                ctx[k] = v

        await self.redis.set(
            self._key(session_id),
            json.dumps(ctx),
            ex=SESSION_TTL_SECONDS,
        )

    async def clear(self, session_id: str) -> None:
        """Delete session data."""
        await self.redis.delete(self._key(session_id))
