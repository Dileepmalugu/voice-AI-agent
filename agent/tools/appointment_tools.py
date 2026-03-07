"""
Appointment Tools — OpenAI Function-Calling definitions + execution bridge
"""
from typing import Any, Dict

from scheduler.appointment_engine.engine import AppointmentEngine

_engine = AppointmentEngine()

# ─── Tool Schemas (OpenAI format) ────────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "checkAvailability",
            "description": "Check available appointment slots for a doctor on a specific date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_id":   {"type": "string", "description": "Doctor identifier or specialty"},
                    "date":        {"type": "string", "description": "Date in YYYY-MM-DD format"},
                },
                "required": ["doctor_id", "date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bookAppointment",
            "description": "Book a new appointment for a patient.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id":  {"type": "string"},
                    "doctor_id":   {"type": "string"},
                    "date":        {"type": "string", "description": "YYYY-MM-DD"},
                    "time_slot":   {"type": "string", "description": "HH:MM"},
                    "notes":       {"type": "string"},
                },
                "required": ["patient_id", "doctor_id", "date", "time_slot"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancelAppointment",
            "description": "Cancel an existing appointment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {"type": "string"},
                    "reason":         {"type": "string"},
                },
                "required": ["appointment_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rescheduleAppointment",
            "description": "Reschedule an appointment to a new date/time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "appointment_id": {"type": "string"},
                    "new_date":       {"type": "string", "description": "YYYY-MM-DD"},
                    "new_time_slot":  {"type": "string", "description": "HH:MM"},
                },
                "required": ["appointment_id", "new_date", "new_time_slot"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "getPatientAppointments",
            "description": "Retrieve all appointments for a patient.",
            "parameters": {
                "type": "object",
                "properties": {
                    "patient_id": {"type": "string"},
                },
                "required": ["patient_id"],
            },
        },
    },
]


# ─── Executor ─────────────────────────────────────────────────────────────────

async def execute_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch tool call to the AppointmentEngine."""
    if name == "checkAvailability":
        return {
            "available_slots": await _engine.get_available_slots(
                args["doctor_id"], args["date"]
            )
        }
    elif name == "bookAppointment":
        return await _engine.book(**args)
    elif name == "cancelAppointment":
        return await _engine.cancel(**args)
    elif name == "rescheduleAppointment":
        return await _engine.reschedule(**args)
    elif name == "getPatientAppointments":
        return {"appointments": await _engine.get_by_patient(args["patient_id"])}
    else:
        return {"error": f"Unknown tool: {name}"}
