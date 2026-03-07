"""
Appointment REST API Routes
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from scheduler.appointment_engine.engine import AppointmentEngine

router = APIRouter()
engine = AppointmentEngine()


# ─── Schemas ─────────────────────────────────────────────────────────────────

class BookRequest(BaseModel):
    patient_id: str
    doctor_id: str
    date: str          # YYYY-MM-DD
    time_slot: str     # HH:MM
    notes: Optional[str] = None

class RescheduleRequest(BaseModel):
    appointment_id: str
    new_date: str
    new_time_slot: str

class CancelRequest(BaseModel):
    appointment_id: str
    reason: Optional[str] = None


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/availability/{doctor_id}")
async def get_availability(doctor_id: str, date: str):
    """Check available time slots for a doctor on a given date."""
    slots = await engine.get_available_slots(doctor_id, date)
    return {"doctor_id": doctor_id, "date": date, "available_slots": slots}


@router.post("/book")
async def book_appointment(req: BookRequest):
    """Book a new appointment."""
    result = await engine.book(
        patient_id=req.patient_id,
        doctor_id=req.doctor_id,
        date=req.date,
        time_slot=req.time_slot,
        notes=req.notes,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.put("/reschedule")
async def reschedule_appointment(req: RescheduleRequest):
    """Reschedule an existing appointment."""
    result = await engine.reschedule(
        appointment_id=req.appointment_id,
        new_date=req.new_date,
        new_time_slot=req.new_time_slot,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.delete("/cancel")
async def cancel_appointment(req: CancelRequest):
    """Cancel an existing appointment."""
    result = await engine.cancel(
        appointment_id=req.appointment_id,
        reason=req.reason,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.get("/patient/{patient_id}")
async def get_patient_appointments(patient_id: str):
    """Retrieve all appointments for a patient."""
    appointments = await engine.get_by_patient(patient_id)
    return {"patient_id": patient_id, "appointments": appointments}
