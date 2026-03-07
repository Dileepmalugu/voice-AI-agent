"""
AI Agent Engine - LLM-based reasoning for appointment management.
Supports OpenAI GPT-4o and Groq (free). Falls back to mock mode if no API key.
"""
import os, json, logging
from typing import Optional

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are 2Care - a friendly, professional healthcare appointment assistant.
You help patients book, reschedule, and cancel medical appointments via voice.

You support English, Hindi, and Tamil. ALWAYS reply in the SAME language the patient used.

Available actions (call as JSON tool):
  book_appointment(doctor_id, date, time_slot, patient_id)
  cancel_appointment(appointment_id)
  reschedule_appointment(appointment_id, new_date, new_time_slot)
  check_availability(doctor_id, date)
  get_patient_appointments(patient_id)

Rules:
- Be warm and concise (max 2 sentences per response).
- If intent is unclear, ask ONE clarifying question.
- Always confirm before booking.
- Never make up slot times - check availability first.
- When replying in Hindi or Tamil, keep medical terms in English.

Respond ONLY with JSON:
{
  "action": "<action_name or null>",
  "params": { ... },
  "reply": "<response to patient in their language>"
}"""


class AgentEngine:
    def __init__(self, appt_service, session_store, patient_store):
        self.appt_service  = appt_service
        self.session_store = session_store
        self.patient_store = patient_store
        self.api_key       = os.getenv("OPENAI_API_KEY", "")
        self.use_mock      = not bool(self.api_key)

        # Detect if Groq key is being used (starts with gsk_)
        self.use_groq = self.api_key.startswith("gsk_")

        if self.use_mock:
            logger.warning("No OPENAI_API_KEY found — running in MOCK mode.")
        elif self.use_groq:
            logger.info("Groq API key detected — using Llama 3.3 70B model.")
        else:
            logger.info("OpenAI API key detected — using GPT-4o model.")

    async def process(self, text: str, session_id: str, patient_id: str, language: str) -> str:
        ctx = self.session_store.get(session_id) or {}
        ctx["session_id"] = session_id
        history = ctx.get("history", [])
        patient = self.patient_store.get(patient_id) or {}

        history.append({"role": "user", "content": text})

        if self.use_mock:
            reply = self._mock_response(text, language, ctx, patient_id)
        else:
            reply = await self._llm_response(history, patient, patient_id, language)

        history.append({"role": "assistant", "content": reply})
        ctx["history"] = history[-10:]
        ctx["language"] = language
        self.session_store.set(session_id, ctx)
        return reply

    async def _llm_response(self, history, patient, patient_id, language) -> str:
        try:
            import openai

            # Use Groq base URL if Groq key detected
            if self.use_groq:
                client = openai.AsyncOpenAI(
                    api_key=self.api_key,
                    base_url="https://api.groq.com/openai/v1"
                )
                model = "llama-3.3-70b-versatile"
            else:
                client = openai.AsyncOpenAI(api_key=self.api_key)
                model = "gpt-4o"

            context_note = (
                f"Patient: {patient.get('name', 'Unknown')} | "
                f"Language: {language} | "
                f"Past doctor: {patient.get('last_doctor', 'N/A')}"
            )
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT + f"\n\nContext: {context_note}"},
                *history
            ]
            resp = await client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=300,
                temperature=0.4
            )
            raw = resp.choices[0].message.content.strip()

            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            parsed = json.loads(raw)
            action = parsed.get("action")
            params = parsed.get("params", {})
            reply  = parsed.get("reply", "I'm here to help.")

            if action and action != "null":
                tool_result = self._execute_tool(action, {**params, "patient_id": patient_id})
                if tool_result:
                    reply = reply + " " + tool_result
            return reply

        except json.JSONDecodeError:
            return raw if raw else "I'm here to help. How can I assist you?"
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return "I'm having trouble processing that. Could you please repeat?"

    def _execute_tool(self, action: str, params: dict) -> str:
        try:
            if action == "check_availability":
                slots = self.appt_service.get_available_slots(
                    params.get("doctor_id", ""), params.get("date", ""))
                return f"Available slots: {', '.join(slots)}" if slots else "No slots available."

            elif action == "book_appointment":
                result = self.appt_service.book_appointment(
                    params.get("patient_id"),
                    params.get("doctor_id"),
                    params.get("date"),
                    params.get("time_slot"))
                return f"Booked! Confirmation ID: {result.get('id', '')}" if result else "Booking failed."

            elif action == "cancel_appointment":
                ok = self.appt_service.cancel_appointment(params.get("appointment_id", ""))
                return "Appointment cancelled." if ok else "Could not cancel."

            elif action == "reschedule_appointment":
                ok = self.appt_service.reschedule_appointment(
                    params.get("appointment_id"),
                    params.get("new_date"),
                    params.get("new_time_slot"))
                return "Appointment rescheduled." if ok else "Could not reschedule."

            elif action == "get_patient_appointments":
                appts = self.appt_service.get_patient_appointments(params.get("patient_id", ""))
                if not appts:
                    return "You have no upcoming appointments."
                lines = [
                    f"{a['date']} {a['time_slot']} with {a['doctor_name']}"
                    for a in appts[:3]
                ]
                return "Your appointments: " + "; ".join(lines)

        except Exception as e:
            logger.error(f"Tool error: {e}")
        return ""

    def _mock_response(self, text: str, language: str, ctx: dict, patient_id: str) -> str:
        """Rule-based mock when no API key is set."""
        t = text.lower().strip()
        step = ctx.get("step", "")

        # ── BOOKING FLOW ──────────────────────────────────────────────────────
        if step == "awaiting_specialty":
            detected = ""
            if "cardio" in t:                     detected = "Cardiology"
            elif "derm" in t:                     detected = "Dermatology"
            elif "general" in t:                  detected = "General"
            elif "ortho" in t:                    detected = "Orthopedics"
            elif "neuro" in t:                    detected = "Neurology"
            elif "gynec" in t or "gyne" in t:     detected = "Gynecology"
            elif "pediatr" in t or "child" in t:  detected = "Pediatrics"
            elif "eye" in t or "ophthal" in t:    detected = "Ophthalmology"
            elif "ent" in t or "ear" in t:        detected = "ENT"
            elif "psych" in t or "mental" in t:   detected = "Psychiatry"

            if detected:
                ctx["step"] = "awaiting_date"
                ctx["specialty"] = detected
                doctor = self.appt_service.get_doctor_by_specialty(detected)
                if doctor:
                    ctx["doctor_id"] = doctor["id"]
                    ctx["doctor_name"] = doctor["name"]
                    return (f"Got it — {detected} with {doctor['name']} "
                            f"(Consultation fee: ₹{doctor.get('fee', 500)}). "
                            f"What date would you like? (e.g. tomorrow, Monday)")
                return f"Got it — {detected}. What date would you like?"
            else:
                return ("Please choose a specialty:\n"
                        "• Cardiology  • Dermatology  • General\n"
                        "• Orthopedics  • Neurology  • Gynecology\n"
                        "• Pediatrics  • Ophthalmology  • ENT  • Psychiatry")

        if step == "awaiting_date":
            ctx["step"] = "awaiting_time"
            ctx["date"] = text
            doctor_id = ctx.get("doctor_id", "D003")
            normalized_date = self.appt_service._normalize_date(text)
            slots = self.appt_service.get_available_slots(doctor_id, normalized_date)
            slots_display = ", ".join(slots[:5]) if slots else "09:00, 10:30, 14:00, 15:30"
            return f"Available slots on {text}: {slots_display}. Which time works for you?"

        if step == "awaiting_time":
            doctor_id   = ctx.get("doctor_id", "D003")
            date_str    = ctx.get("date", "tomorrow")
            result      = self.appt_service.book_appointment(patient_id, doctor_id, date_str, text)
            specialty   = ctx.get("specialty", "")
            doctor_name = ctx.get("doctor_name", "")
            appt_id     = result.get("id", "APT-001") if result else "APT-001"
            fee         = result.get("fee", 500) if result else 500
            actual_date = result.get("date", date_str) if result else date_str
            actual_time = result.get("time_slot", text) if result else text
            ctx["step"] = ""
            ctx["specialty"] = ""
            ctx["date"] = ""
            ctx["doctor_id"] = ""
            return (f"✅ Appointment booked!\n"
                    f"Doctor: {doctor_name}\n"
                    f"Specialty: {specialty}\n"
                    f"Date: {actual_date} at {actual_time}\n"
                    f"Fee: ₹{fee}\n"
                    f"Confirmation ID: {appt_id}\n"
                    f"Is there anything else I can help you with?")

        # ── CANCEL FLOW ───────────────────────────────────────────────────────
        if step == "awaiting_cancel_id":
            ok = self.appt_service.cancel_appointment(text.strip())
            ctx["step"] = ""
            if ok:
                return f"✅ Appointment {text.strip()} cancelled successfully."
            return f"❌ Could not find appointment ID '{text.strip()}'. Please check and try again."

        # ── RESCHEDULE FLOW ───────────────────────────────────────────────────
        if step == "awaiting_reschedule_id":
            ctx["step"] = "awaiting_reschedule_date"
            ctx["reschedule_id"] = text.strip()
            return f"What new date would you like for appointment {text.strip()}?"

        if step == "awaiting_reschedule_date":
            ctx["step"] = "awaiting_reschedule_time"
            ctx["reschedule_date"] = text
            normalized_date = self.appt_service._normalize_date(text)
            slots = self.appt_service.get_available_slots(
                ctx.get("reschedule_doctor_id", "D003"), normalized_date)
            slots_display = ", ".join(slots[:5]) if slots else "09:00, 10:30, 14:00, 15:30"
            return f"Available slots on {text}: {slots_display}. Which time?"

        if step == "awaiting_reschedule_time":
            ok = self.appt_service.reschedule_appointment(
                ctx.get("reschedule_id"), ctx.get("reschedule_date"), text)
            ctx["step"] = ""
            if ok:
                return f"✅ Rescheduled to {ctx.get('reschedule_date')} at {text}. Confirmation sent!"
            return "❌ Could not reschedule. Please try again."

        # ── INTENT DETECTION ──────────────────────────────────────────────────

        # Check appointments
        if any(w in t for w in ["my appointment", "appointments", "what appointment",
                                  "upcoming", "scheduled", "do i have", "show"]):
            appts = self.appt_service.get_patient_appointments(patient_id)
            if not appts:
                return "You have no upcoming appointments. Would you like to book one?"
            lines = [
                f"• {a['date']} at {a['time_slot']} with {a['doctor_name']} "
                f"({a.get('specialty', '')}) — ID: {a['id']}"
                for a in appts[:3]
            ]
            return "Your upcoming appointments:\n" + "\n".join(lines)

        # Cancel
        if any(w in t for w in ["cancel", "remove", "delete"]):
            appts = self.appt_service.get_patient_appointments(patient_id)
            if not appts:
                return "You have no upcoming appointments to cancel."
            lines = [
                f"• ID: {a['id']} — {a['date']} at {a['time_slot']} with {a['doctor_name']}"
                for a in appts[:3]
            ]
            ctx["step"] = "awaiting_cancel_id"
            return ("Your appointments:\n" + "\n".join(lines) +
                    "\n\nPlease say the appointment ID you want to cancel.")

        # Reschedule
        if any(w in t for w in ["reschedule", "change", "move", "shift",
                                  "another time", "different date"]):
            appts = self.appt_service.get_patient_appointments(patient_id)
            if not appts:
                return "You have no upcoming appointments to reschedule."
            lines = [
                f"• ID: {a['id']} — {a['date']} at {a['time_slot']} with {a['doctor_name']}"
                for a in appts[:3]
            ]
            ctx["step"] = "awaiting_reschedule_id"
            return ("Your appointments:\n" + "\n".join(lines) +
                    "\n\nWhich appointment ID would you like to reschedule?")

        # Availability
        if any(w in t for w in ["available", "slot", "opening", "free", "availability"]):
            return "Available slots for tomorrow: 09:00, 10:30, 14:00, 15:30, 16:00. Would you like to book one?"

        # Show doctors
        if any(w in t for w in ["doctor", "doctors", "specialist", "which doctor"]):
            doctors = self.appt_service.get_all_doctors()
            lines = [
                f"• {d['name']} — {d['specialty']} (₹{d.get('fee', 500)})"
                for d in doctors
            ]
            return "Our doctors:\n" + "\n".join(lines) + "\n\nWhich specialty would you like?"

        # Book
        if any(w in t for w in ["book", "schedule", "appointment", "need",
                                  "want", "see a", "visit", "consult", "fix"]):
            ctx["step"] = "awaiting_specialty"
            return ("I can help book an appointment. Which specialty do you need?\n"
                    "• Cardiology  • Dermatology  • General\n"
                    "• Orthopedics  • Neurology  • Gynecology\n"
                    "• Pediatrics  • Ophthalmology  • ENT  • Psychiatry")

        # Greetings
        if any(w in t for w in ["hi", "hello", "hey", "good morning", "good afternoon",
                                  "good evening", "namaste", "vanakkam", "start"]):
            return ("Hello! I'm your 2Care appointment assistant. I can help you:\n"
                    "• 📅 Book an appointment\n"
                    "• ❌ Cancel an appointment\n"
                    "• 🔄 Reschedule an appointment\n"
                    "• 📋 Check your upcoming appointments\n"
                    "• 👨‍⚕️ View all doctors\n\n"
                    "How can I help you today?")

        # Default
        return ("I'm here to help! You can say:\n"
                "• 'Book an appointment'\n"
                "• 'Cancel my appointment'\n"
                "• 'Reschedule my appointment'\n"
                "• 'What appointments do I have?'\n"
                "• 'Show all doctors'")

    def build_outbound_message(self, patient_id: str, campaign_type: str,
                                appointment_id: Optional[str]) -> str:
        patient = self.patient_store.get(patient_id) or {}
        name = patient.get("name", "there")
        appts = self.appt_service.get_patient_appointments(patient_id)
        if campaign_type == "reminder" and appts:
            a = appts[0]
            return (f"Hello {name}! This is a reminder about your appointment with "
                    f"{a['doctor_name']} on {a['date']} at {a['time_slot']}. "
                    f"Would you like to confirm or reschedule?")
        elif campaign_type == "followup":
            return (f"Hello {name}! We're calling to follow up on your recent appointment. "
                    f"How are you feeling? Would you like to book a follow-up visit?")
        elif campaign_type == "vaccination":
            return (f"Hello {name}! This is a vaccination reminder. "
                    f"Please book your appointment at your earliest convenience.")
        return f"Hello {name}! This is 2Care calling. How can we assist you today?"