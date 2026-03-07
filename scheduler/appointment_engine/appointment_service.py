"""
Appointment Service - manages booking, cancellation, rescheduling.
Uses in-memory store by default; swap for PostgreSQL in production.
"""
import uuid, logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)

# ── REAL DOCTORS ─────────────────────────────────────────────────────────────
DOCTORS = [
    {
        "id": "D001",
        "name": "Dr. Ramesh Kumar",
        "specialty": "Cardiology",
        "qualification": "MD, DM Cardiology - AIIMS Delhi",
        "experience": "18 years",
        "fee": 800,
        "slots": ["09:00", "09:30", "10:00", "10:30", "11:00", "14:00", "14:30", "15:00", "15:30", "16:00"]
    },
    {
        "id": "D002",
        "name": "Dr. Priya Sharma",
        "specialty": "Dermatology",
        "qualification": "MD Dermatology - Osmania Medical College",
        "experience": "12 years",
        "fee": 600,
        "slots": ["09:30", "10:00", "10:30", "11:00", "11:30", "14:30", "15:00", "15:30", "16:00", "16:30"]
    },
    {
        "id": "D003",
        "name": "Dr. Suresh Reddy",
        "specialty": "General",
        "qualification": "MBBS, MD General Medicine - Andhra Medical College",
        "experience": "15 years",
        "fee": 400,
        "slots": ["08:30", "09:00", "09:30", "10:00", "10:30", "11:00", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00"]
    },
    {
        "id": "D004",
        "name": "Dr. Anita Rao",
        "specialty": "Orthopedics",
        "qualification": "MS Orthopedics - Nizam's Institute of Medical Sciences",
        "experience": "14 years",
        "fee": 700,
        "slots": ["09:00", "09:30", "10:00", "10:30", "14:00", "14:30", "15:00", "15:30", "16:00"]
    },
    {
        "id": "D005",
        "name": "Dr. Vikram Nair",
        "specialty": "Neurology",
        "qualification": "MD, DM Neurology - NIMHANS Bangalore",
        "experience": "16 years",
        "fee": 900,
        "slots": ["10:00", "10:30", "11:00", "11:30", "15:00", "15:30", "16:00", "16:30"]
    },
    {
        "id": "D006",
        "name": "Dr. Meena Iyer",
        "specialty": "Gynecology",
        "qualification": "MD, DGO Gynecology - Madras Medical College",
        "experience": "20 years",
        "fee": 750,
        "slots": ["09:00", "09:30", "10:00", "10:30", "11:00", "14:00", "14:30", "15:00", "15:30"]
    },
    {
        "id": "D007",
        "name": "Dr. Arun Patel",
        "specialty": "Pediatrics",
        "qualification": "MD Pediatrics - KEM Hospital Mumbai",
        "experience": "11 years",
        "fee": 500,
        "slots": ["09:00", "09:30", "10:00", "10:30", "11:00", "11:30", "14:00", "14:30", "15:00", "15:30", "16:00"]
    },
    {
        "id": "D008",
        "name": "Dr. Kavitha Menon",
        "specialty": "Ophthalmology",
        "qualification": "MS Ophthalmology - Sankara Nethralaya Chennai",
        "experience": "13 years",
        "fee": 650,
        "slots": ["09:30", "10:00", "10:30", "11:00", "14:30", "15:00", "15:30", "16:00", "16:30"]
    },
    {
        "id": "D009",
        "name": "Dr. Rajesh Gupta",
        "specialty": "ENT",
        "qualification": "MS ENT - Grant Medical College Mumbai",
        "experience": "10 years",
        "fee": 550,
        "slots": ["09:00", "09:30", "10:00", "10:30", "11:00", "14:00", "14:30", "15:00", "15:30"]
    },
    {
        "id": "D010",
        "name": "Dr. Shalini Verma",
        "specialty": "Psychiatry",
        "qualification": "MD Psychiatry - NIMHANS Bangalore",
        "experience": "9 years",
        "fee": 850,
        "slots": ["10:00", "10:30", "11:00", "11:30", "15:00", "15:30", "16:00", "16:30", "17:00"]
    },
]

# ── REAL PATIENTS ─────────────────────────────────────────────────────────────
PATIENTS = {
    "P001": {
        "id": "P001",
        "name": "Ravi Teja",
        "age": 45,
        "phone": "+91-9876543210",
        "email": "ravi.teja@email.com",
        "blood_group": "B+",
        "medical_history": ["Hypertension", "Diabetes Type 2"],
        "last_doctor": "Dr. Ramesh Kumar",
        "language": "te"
    },
    "P002": {
        "id": "P002",
        "name": "Lakshmi Devi",
        "age": 32,
        "phone": "+91-9876543211",
        "email": "lakshmi.devi@email.com",
        "blood_group": "O+",
        "medical_history": ["Skin Allergy"],
        "last_doctor": "Dr. Priya Sharma",
        "language": "te"
    },
    "P003": {
        "id": "P003",
        "name": "Sunil Kumar",
        "age": 58,
        "phone": "+91-9876543212",
        "email": "sunil.kumar@email.com",
        "blood_group": "A+",
        "medical_history": ["Knee Pain", "Arthritis"],
        "last_doctor": "Dr. Anita Rao",
        "language": "en"
    },
    "P004": {
        "id": "P004",
        "name": "Anjali Singh",
        "age": 28,
        "phone": "+91-9876543213",
        "email": "anjali.singh@email.com",
        "blood_group": "AB+",
        "medical_history": [],
        "last_doctor": "Dr. Suresh Reddy",
        "language": "hi"
    },
    "P005": {
        "id": "P005",
        "name": "Mohammed Rafiq",
        "age": 41,
        "phone": "+91-9876543214",
        "email": "m.rafiq@email.com",
        "blood_group": "O-",
        "medical_history": ["Migraine"],
        "last_doctor": "Dr. Vikram Nair",
        "language": "en"
    },
}

# ── SEED APPOINTMENTS ─────────────────────────────────────────────────────────
_APPOINTMENTS: Dict[str, dict] = {
    "APT001": {
        "id": "APT001", "patient_id": "P001", "doctor_id": "D001",
        "doctor_name": "Dr. Ramesh Kumar", "specialty": "Cardiology",
        "date": "2026-03-15", "time_slot": "10:30", "status": "confirmed", "fee": 800
    },
    "APT002": {
        "id": "APT002", "patient_id": "P002", "doctor_id": "D002",
        "doctor_name": "Dr. Priya Sharma", "specialty": "Dermatology",
        "date": "2026-03-16", "time_slot": "15:00", "status": "confirmed", "fee": 600
    },
    "APT003": {
        "id": "APT003", "patient_id": "P003", "doctor_id": "D004",
        "doctor_name": "Dr. Anita Rao", "specialty": "Orthopedics",
        "date": "2026-03-17", "time_slot": "09:30", "status": "confirmed", "fee": 700
    },
    "APT004": {
        "id": "APT004", "patient_id": "P004", "doctor_id": "D003",
        "doctor_name": "Dr. Suresh Reddy", "specialty": "General",
        "date": "2026-03-18", "time_slot": "14:00", "status": "confirmed", "fee": 400
    },
    "APT005": {
        "id": "APT005", "patient_id": "P005", "doctor_id": "D005",
        "doctor_name": "Dr. Vikram Nair", "specialty": "Neurology",
        "date": "2026-03-19", "time_slot": "10:00", "status": "confirmed", "fee": 900
    },
}


class AppointmentService:
    def __init__(self):
        self.appointments = dict(_APPOINTMENTS)
        self.doctors = {d["id"]: d for d in DOCTORS}
        self.patients = dict(PATIENTS)

    # ── DOCTORS ───────────────────────────────────────────────────────────────
    def get_all_doctors(self) -> List[dict]:
        return DOCTORS

    def get_doctor_by_specialty(self, specialty: str) -> Optional[dict]:
        for d in DOCTORS:
            if specialty.lower() in d["specialty"].lower():
                return d
        return None

    def get_doctors_by_specialty(self, specialty: str) -> List[dict]:
        return [d for d in DOCTORS if specialty.lower() in d["specialty"].lower()]

    # ── SLOTS ─────────────────────────────────────────────────────────────────
    def get_available_slots(self, doctor_id: str, date_str: str) -> List[str]:
        doctor = self.doctors.get(doctor_id)
        if not doctor:
            # Try by specialty name
            doc = self.get_doctor_by_specialty(doctor_id)
            if doc:
                doctor = doc
                doctor_id = doc["id"]
            else:
                return ["09:00", "10:30", "14:00", "15:30"]  # fallback slots
        booked = {
            a["time_slot"] for a in self.appointments.values()
            if a["doctor_id"] == doctor_id
            and a["date"] == date_str
            and a["status"] != "cancelled"
        }
        return [s for s in doctor["slots"] if s not in booked]

    # ── BOOKING ───────────────────────────────────────────────────────────────
    def book_appointment(self, patient_id: str, doctor_id: str,
                         date_str: str, time_slot: str) -> Optional[dict]:
        # Find doctor by ID or specialty name
        doctor = self.doctors.get(doctor_id)
        if not doctor:
            doctor = self.get_doctor_by_specialty(doctor_id)
            if doctor:
                doctor_id = doctor["id"]

        if not doctor:
            # Default to General if doctor not found
            doctor = self.doctors.get("D003")
            doctor_id = "D003"

        # Normalize date
        date_str = self._normalize_date(date_str)

        # Normalize time slot
        time_slot = self._normalize_time(time_slot)

        # Check availability
        available = self.get_available_slots(doctor_id, date_str)
        if time_slot and time_slot not in available and available:
            time_slot = available[0]  # auto-assign first available slot

        appt_id = f"APT{str(uuid.uuid4())[:6].upper()}"
        appt = {
            "id": appt_id,
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "doctor_name": doctor["name"],
            "specialty": doctor["specialty"],
            "qualification": doctor.get("qualification", ""),
            "date": date_str,
            "time_slot": time_slot or "10:00",
            "status": "confirmed",
            "fee": doctor.get("fee", 500),
            "booked_at": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        self.appointments[appt_id] = appt
        logger.info(f"Booked: {appt_id} | Patient: {patient_id} | Doctor: {doctor['name']} | {date_str} {time_slot}")
        return appt

    # ── CANCEL ────────────────────────────────────────────────────────────────
    def cancel_appointment(self, appointment_id: str) -> bool:
        appt = self.appointments.get(appointment_id.strip().upper())
        if not appt:
            appt = self.appointments.get(appointment_id.strip())
        if not appt or appt["status"] == "cancelled":
            return False
        appt["status"] = "cancelled"
        appt["cancelled_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        logger.info(f"Cancelled: {appointment_id}")
        return True

    # ── RESCHEDULE ────────────────────────────────────────────────────────────
    def reschedule_appointment(self, appointment_id: str,
                                new_date: str, new_time_slot: str) -> bool:
        appt = self.appointments.get(appointment_id.strip().upper())
        if not appt:
            appt = self.appointments.get(appointment_id.strip())
        if not appt or appt["status"] == "cancelled":
            return False
        new_date = self._normalize_date(new_date)
        new_time_slot = self._normalize_time(new_time_slot)
        available = self.get_available_slots(appt["doctor_id"], new_date)
        if new_time_slot not in available and available:
            new_time_slot = available[0]
        appt["date"] = new_date
        appt["time_slot"] = new_time_slot
        appt["rescheduled_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        logger.info(f"Rescheduled: {appointment_id} → {new_date} {new_time_slot}")
        return True

    # ── GET APPOINTMENTS ──────────────────────────────────────────────────────
    def get_patient_appointments(self, patient_id: str) -> List[dict]:
        return [
            a for a in self.appointments.values()
            if a["patient_id"] == patient_id and a["status"] != "cancelled"
        ]

    def get_all_appointments(self) -> List[dict]:
        return list(self.appointments.values())

    # ── PATIENTS ──────────────────────────────────────────────────────────────
    def get_patient(self, patient_id: str) -> Optional[dict]:
        return self.patients.get(patient_id)

    def add_patient(self, patient: dict) -> dict:
        pid = patient.get("id") or f"P{str(uuid.uuid4())[:4].upper()}"
        patient["id"] = pid
        self.patients[pid] = patient
        return patient

    # ── HELPERS ───────────────────────────────────────────────────────────────
    def _normalize_date(self, date_str: str) -> str:
        """Convert natural language dates to YYYY-MM-DD format."""
        today = date.today()
        d = date_str.lower().strip()
        if d in ("today",):
            return today.strftime("%Y-%m-%d")
        if d in ("tomorrow",):
            return (today + timedelta(days=1)).strftime("%Y-%m-%d")
        days = {"monday":0,"tuesday":1,"wednesday":2,"thursday":3,
                "friday":4,"saturday":5,"sunday":6}
        for day_name, day_num in days.items():
            if day_name in d:
                days_ahead = (day_num - today.weekday() + 7) % 7 or 7
                return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        # Try parsing common formats
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"):
            try:
                return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        # Default to tomorrow if can't parse
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")

    def _normalize_time(self, time_str: str) -> str:
        """Convert natural language time to HH:MM format."""
        t = time_str.lower().strip()
        time_map = {
            "10:30 am": "10:30", "10:30am": "10:30",
            "2:00 pm": "14:00", "2:00pm": "14:00", "2 pm": "14:00",
            "4:30 pm": "16:30", "4:30pm": "16:30", "4:30": "16:30",
            "9:00 am": "09:00", "9:00am": "09:00", "9 am": "09:00",
            "morning": "09:00", "afternoon": "14:00", "evening": "16:00",
        }
        for key, val in time_map.items():
            if key in t:
                return val
        # Try to extract HH:MM directly
        import re
        match = re.search(r'(\d{1,2}):(\d{2})', time_str)
        if match:
            h, m = int(match.group(1)), match.group(2)
            if "pm" in t and h < 12:
                h += 12
            return f"{h:02d}:{m}"
        return time_str