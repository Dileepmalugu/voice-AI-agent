"""
2Care.ai - Real-Time Multilingual Voice AI Agent
Main FastAPI Backend Server
"""

import time, json, uuid, asyncio, logging
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
from agent.reasoning.agent_engine import AgentEngine
from memory.session_memory.session_store import SessionStore
from memory.persistent_memory.patient_store import PatientStore
from services.speech_to_text.stt_service import STTService
from services.text_to_speech.tts_service import TTSService
from services.language_detection.lang_detector import LanguageDetector
from scheduler.appointment_engine.appointment_service import AppointmentService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="2Care.ai Voice AI Agent", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

frontend_path = Path(__file__).parent.parent / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")

# Services
session_store = SessionStore()
patient_store = PatientStore()
stt_service   = STTService()
tts_service   = TTSService()
lang_detector = LanguageDetector()
appt_service  = AppointmentService()
agent_engine  = AgentEngine(appt_service, session_store, patient_store)

class TextRequest(BaseModel):
    text: str
    session_id: Optional[str] = None
    patient_id: Optional[str] = None
    language: Optional[str] = None

@app.get("/")
def health():
    return {"status": "running", "service": "2Care.ai Voice AI Agent"}

@app.get("/health")
def detailed_health():
    return {"status": "healthy", "services": {"stt":"ready","tts":"ready","agent":"ready","memory":"ready","scheduler":"ready"}}

@app.post("/api/chat")
async def chat(req: TextRequest):
    start = time.time()
    session_id = req.session_id or str(uuid.uuid4())
    patient_id = req.patient_id or "guest"
    t1 = time.time()
    language = req.language or lang_detector.detect(req.text)
    lat_lang = int((time.time()-t1)*1000)
    t2 = time.time()
    response = await agent_engine.process(req.text, session_id, patient_id, language)
    lat_agent = int((time.time()-t2)*1000)
    total = int((time.time()-start)*1000)
    return {"session_id":session_id,"response":response,"language_detected":language,"latency_ms":{"language_detection":lat_lang,"agent_reasoning":lat_agent,"total":total}}

@app.get("/api/appointments/{patient_id}")
def get_appointments(patient_id: str):
    return appt_service.get_patient_appointments(patient_id)

@app.get("/api/doctors")
def get_doctors():
    return appt_service.get_all_doctors()

@app.get("/api/availability/{doctor_id}/{date}")
def get_availability(doctor_id: str, date: str):
    return {"doctor_id":doctor_id,"date":date,"available_slots":appt_service.get_available_slots(doctor_id, date)}

@app.delete("/api/appointments/{appointment_id}")
def cancel_appointment(appointment_id: str):
    result = appt_service.cancel_appointment(appointment_id)
    if not result:
        raise HTTPException(status_code=404, detail="Appointment not found")
    return {"message":"Appointment cancelled","appointment_id":appointment_id}

@app.websocket("/ws/voice/{session_id}")
async def voice_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()
    logger.info(f"[WS] Connected: {session_id}")
    try:
        while True:
            raw = await websocket.receive_text()
            msg = json.loads(raw)
            msg_type = msg.get("type")
            if msg_type == "ping":
                await websocket.send_text(json.dumps({"type":"pong"})); continue
            pipeline_start = time.time()
            patient_id = msg.get("patient_id","guest")
            breakdown = {}
            if msg_type == "audio":
                t0 = time.time()
                transcript = stt_service.transcribe_base64(msg.get("data",""))
                breakdown["stt_ms"] = int((time.time()-t0)*1000)
                user_text = transcript
            elif msg_type == "text":
                user_text = msg.get("data","")
            else:
                continue
            if not user_text.strip(): continue
            t1 = time.time()
            language = lang_detector.detect(user_text)
            breakdown["lang_ms"] = int((time.time()-t1)*1000)
            await websocket.send_text(json.dumps({"type":"transcript","text":user_text,"language":language}))
            t2 = time.time()
            response_text = await agent_engine.process(user_text, session_id, patient_id, language)
            breakdown["agent_ms"] = int((time.time()-t2)*1000)
            await websocket.send_text(json.dumps({"type":"response","text":response_text,"latency_agent_ms":breakdown["agent_ms"]}))
            t3 = time.time()
            audio_out = tts_service.synthesize_base64(response_text, language)
            breakdown["tts_ms"] = int((time.time()-t3)*1000)
            await websocket.send_text(json.dumps({"type":"audio","data":audio_out}))
            breakdown["total_ms"] = int((time.time()-pipeline_start)*1000)
            await websocket.send_text(json.dumps({"type":"latency","total_ms":breakdown["total_ms"],"breakdown":breakdown,"target_met":breakdown["total_ms"]<450}))
            logger.info(f"[WS] {session_id} | {breakdown}")
    except WebSocketDisconnect:
        logger.info(f"[WS] Disconnected: {session_id}")
    except Exception as e:
        logger.error(f"[WS] Error: {e}")
        try: await websocket.send_text(json.dumps({"type":"error","message":str(e)}))
        except: pass

@app.get("/ui", response_class=HTMLResponse)
async def serve_ui():
    ui_path = Path(__file__).parent.parent / "frontend" / "index.html"
    return ui_path.read_text(encoding="utf-8") if ui_path.exists() else HTMLResponse("<h2>Frontend not found</h2>")