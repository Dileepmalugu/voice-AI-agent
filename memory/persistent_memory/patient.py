"""
Persistent Memory Manager
Stores long-term patient preferences and history in Redis.
"""
import json
from typing import Any, Dict, Optional


class PersistentMemoryManager:
    def __init__(self, redis_client):
        self.redis = redis_client

    def _key(self, patient_id: str) -> str:
        return f"patient:{patient_id}"

    async def get(self, patient_id: str) -> Dict[str, Any]:
        """Load patient profile. Returns default if not found."""
        raw = await self.redis.get(self._key(patient_id))
        if raw:
            return json.loads(raw)
        return {
            "patient_id": patient_id,
            "name": "Unknown",
            "preferred_language": "en",
            "preferred_doctor": "",
            "preferred_hospital": "",
            "past_appointments": [],
        }

    async def save(self, patient_id: str, data: Dict[str, Any]) -> None:
        """Save patient profile (no TTL — persistent)."""
        await self.redis.set(self._key(patient_id), json.dumps(data))

    async def update_after_appointment(
        self,
        patient_id: str,
        appointment: Dict[str, Any],
    ) -> None:
        """Append appointment to patient history and update preferences."""
        profile = await self.get(patient_id)

        profile["past_appointments"].append({
            "id":     appointment.get("id"),
            "doctor": appointment.get("doctor_id"),
            "date":   appointment.get("date"),
            "status": appointment.get("status"),
        })
        # Keep last 50 appointments
        profile["past_appointments"] = profile["past_appointments"][-50:]

        # Update preferred doctor based on most recent booking
        if appointment.get("doctor_id"):
            profile["preferred_doctor"] = appointment["doctor_id"]

        await self.save(patient_id, profile)

    async def set_language_preference(self, patient_id: str, language: str) -> None:
        """Update patient's preferred language."""
        profile = await self.get(patient_id)
        profile["preferred_language"] = language
        await self.save(patient_id, profile)
