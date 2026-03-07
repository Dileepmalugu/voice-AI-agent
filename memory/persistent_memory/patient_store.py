"""Persistent memory - stores long-term patient preferences and history."""
import os, json, logging
logger = logging.getLogger(__name__)

# Seed data for demo
SEED_PATIENTS = {
    "P001": {"id":"P001","name":"Rajesh Kumar","preferred_language":"hi","last_doctor":"Dr. Sharma","preferred_hospital":"Apollo","email":"rajesh@example.com"},
    "P002": {"id":"P002","name":"Priya Venkat","preferred_language":"ta","last_doctor":"Dr. Priya","preferred_hospital":"Fortis","email":"priya@example.com"},
    "P003": {"id":"P003","name":"John Smith","preferred_language":"en","last_doctor":"Dr. Williams","preferred_hospital":"City Clinic","email":"john@example.com"},
    "guest":{"id":"guest","name":"Guest Patient","preferred_language":"en","last_doctor":None,"preferred_hospital":None,"email":None},
}

class PatientStore:
    def __init__(self):
        self._store = dict(SEED_PATIENTS)
        self.redis = None
        try:
            import redis
            url = os.getenv("REDIS_URL", "redis://localhost:6379")
            self.redis = redis.Redis.from_url(url, decode_responses=True)
            self.redis.ping()
            for pid, data in SEED_PATIENTS.items():
                self.redis.set(f"patient:{pid}", json.dumps(data))
            logger.info("PatientStore: Connected to Redis")
        except Exception:
            logger.warning("PatientStore: Redis unavailable, using in-memory store")

    def get(self, patient_id: str) -> dict:
        try:
            if self.redis:
                raw = self.redis.get(f"patient:{patient_id}")
                return json.loads(raw) if raw else None
        except: pass
        return self._store.get(patient_id)

    def upsert(self, patient_id: str, data: dict):
        existing = self.get(patient_id) or {}
        merged = {**existing, **data}
        try:
            if self.redis: self.redis.set(f"patient:{patient_id}", json.dumps(merged)); return
        except: pass
        self._store[patient_id] = merged
