"""Session memory - stores current conversation context (in-memory with optional Redis)."""
import os, json, time, logging
logger = logging.getLogger(__name__)

class SessionStore:
    def __init__(self):
        self._store = {}   # fallback in-memory
        self.redis = None
        try:
            import redis
            url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis = redis.Redis.from_url(url, decode_responses=True)
            self.redis.ping()
            logger.info("SessionStore: Connected to Redis")
        except Exception:
            logger.warning("SessionStore: Redis unavailable, using in-memory store")

    def get(self, session_id: str) -> dict:
        try:
            if self.redis:
                raw = self.redis.get(f"session:{session_id}")
                return json.loads(raw) if raw else None
        except: pass
        return self._store.get(session_id)

    def set(self, session_id: str, data: dict, ttl: int = 3600):
        try:
            if self.redis:
                self.redis.setex(f"session:{session_id}", ttl, json.dumps(data)); return
        except: pass
        self._store[session_id] = data

    def delete(self, session_id: str):
        try:
            if self.redis: self.redis.delete(f"session:{session_id}"); return
        except: pass
        self._store.pop(session_id, None)
