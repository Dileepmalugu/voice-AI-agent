"""
Appointment Engine — scheduling logic, conflict detection, validation
Uses an in-memory store by default; swap for PostgreSQL in production.
"""
import uuid
from datetime import datetime, date
from typing import Any, Dict, List, Optional


# ─── In-Memory Data Store (replace with DB) ──────────────────────────────────

_appointments: Dict[str, Dict] = {}

_doctor_schedules: Dict[str, Dict[str, List[str]]] = {
    "cardiologist": {
        "2024-03-15": ["09:00", "10:30", "14:00", "15:30"],
        "2024-03-16": ["09:00", "11:00", "14:00"],
        "2024-03-17": ["10:00", "11:30", "16:00"],
    },
    "dermatologist": {
        "2024-03-15": ["09:30", "11:00", "15:00"],
        "2024-03-16": ["10:00", "14:30", "16:00"],
    },
    "general": {
        "2024-03-15": ["08:00", "09:00", "10:00", "11:00", "14:00", "15:00", "16:00"],
        "2024-03-16": ["08:00", "09:00", "10:00", "11:00", "14:00", "15:00", "16:00"],
        "2024-03-17": ["08:00", "09:00", "10:00", "11:00", "14:00", "15:00", "16:00"],
    },
}


class AppointmentEngine:

    async def get_available_slots(self, doctor_id: str, date_str: str) -> List[str]:
        """Return open slots for a doctor on a given date."""
        all_slots = _doctor_schedules.get(doctor_id.lower(), {}).get(date_str, [])
        booked = {
            a["time_slot"]
            for a in _appointments.values()
            if a["doctor_id"] == doctor_id and a["date"] == date_str and a["status"] == "confirmed"
        }
        return [s for s in all_slots if s not in booked]

    async def book(
        self,
        patient_id: str,
        doctor_id: str,
        date: str,
        time_slot: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Book an appointment with full validation."""

        # Validate: not in the past
        try:
            appt_dt = datetime.strptime(f"{date} {time_slot}", "%Y-%m-%d %H:%M")
            if appt_dt < datetime.now():
                return {"success": False, "message": "Cannot book appointments in the past."}
        except ValueError:
            return {"success": False, "message": "Invalid date or time format."}

        # Validate: slot available
        available = await self.get_available_slots(doctor_id, date)
        if time_slot not in available:
            alternatives = available[:3]
            return {
                "success": False,
                "message": f"Slot {time_slot} is not available.",
                "alternative_slots": alternatives,
            }

        # Create appointment
        appt_id = str(uuid.uuid4())[:8].upper()
        _appointments[appt_id] = {
            "id": appt_id,
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "date": date,
            "time_slot": time_slot,
            "notes": notes,
            "status": "confirmed",
            "created_at": datetime.now().isoformat(),
        }

        return {
            "success": True,
            "appointment_id": appt_id,
            "message": f"Appointment booked with {doctor_id} on {date} at {time_slot}.",
            "appointment": _appointments[appt_id],
        }

    async def cancel(self, appointment_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """Cancel an appointment."""
        if appointment_id not in _appointments:
            return {"success": False, "message": "Appointment not found."}

        _appointments[appointment_id]["status"] = "cancelled"
        _appointments[appointment_id]["cancel_reason"] = reason

        return {
            "success": True,
            "message": f"Appointment {appointment_id} has been cancelled.",
        }

    async def reschedule(
        self, appointment_id: str, new_date: str, new_time_slot: str
    ) -> Dict[str, Any]:
        """Reschedule an appointment to a new slot."""
        if appointment_id not in _appointments:
            return {"success": False, "message": "Appointment not found."}

        appt = _appointments[appointment_id]
        doctor_id = appt["doctor_id"]

        # Check new slot availability
        available = await self.get_available_slots(doctor_id, new_date)
        if new_time_slot not in available:
            alternatives = available[:3]
            return {
                "success": False,
                "message": f"New slot {new_time_slot} is not available.",
                "alternative_slots": alternatives,
            }

        old_date = appt["date"]
        old_time = appt["time_slot"]
        _appointments[appointment_id]["date"]      = new_date
        _appointments[appointment_id]["time_slot"] = new_time_slot
        _appointments[appointment_id]["status"]    = "rescheduled"

        return {
            "success": True,
            "message": f"Appointment moved from {old_date} {old_time} to {new_date} {new_time_slot}.",
            "appointment": _appointments[appointment_id],
        }

    async def get_by_patient(self, patient_id: str) -> List[Dict]:
        """Get all appointments for a patient."""
        return [
            a for a in _appointments.values()
            if a["patient_id"] == patient_id
        ]
