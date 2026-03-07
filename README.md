# 2Care.ai — Real-Time Multilingual Voice AI Agent

A real-time clinical appointment booking system using voice AI.  
**Target latency: < 450ms from speech end to first audio response.**

## Architecture

```
User Speech
  → WebSocket (real-time)
  → STT (Whisper / OpenAI)
  → Language Detection (Unicode heuristic + langdetect)
  → AI Agent (GPT-4o / Mock)
  → Tool Orchestration (book / cancel / reschedule)
  → Appointment Service (in-memory / PostgreSQL)
  → TTS (OpenAI TTS)
  → Audio Response
```

## Project Structure

```
voice-ai-agent/
├── backend/main.py              # FastAPI server + WebSocket pipeline
├── agent/reasoning/             # LLM agent engine
├── memory/
│   ├── session_memory/          # Redis session store (conversation context)
│   └── persistent_memory/       # Patient preferences & history
├── services/
│   ├── speech_to_text/          # Whisper STT
│   ├── text_to_speech/          # OpenAI TTS
│   └── language_detection/      # EN / HI / TA detection
├── scheduler/appointment_engine/ # Booking logic & validation
├── frontend/index.html          # Web UI
├── docker-compose.yml
└── requirements.txt
```

## Quick Start

### Option 1 — Docker (Recommended)
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
docker-compose up --build
```
Open: http://localhost:8000/ui

### Option 2 — Local Python
```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # Add OPENAI_API_KEY

# Optional: start Redis
docker run -d -p 6379:6379 redis:7-alpine

cd voice-ai-agent
uvicorn backend.main:app --reload --port 8000
```
Open: http://localhost:8000/ui

### No API Key? (Mock Mode)
The system runs fully without an API key using built-in mock responses.  
All latency measurement and WebSocket pipeline still work.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | / | Health check |
| POST | /api/chat | Text chat (no audio) |
| GET | /api/doctors | List all doctors |
| GET | /api/availability/{doctor_id}/{date} | Available slots |
| GET | /api/appointments/{patient_id} | Patient appointments |
| DELETE | /api/appointments/{id} | Cancel appointment |
| WS | /ws/voice/{session_id} | Real-time voice pipeline |
| GET | /ui | Web interface |

## Latency Breakdown

| Stage | Target |
|-------|--------|
| STT (Whisper) | ~120ms |
| Language Detection | ~5ms |
| Agent Reasoning (GPT-4o) | ~200ms |
| TTS | ~100ms |
| **Total** | **< 450ms** |

## Supported Languages

- **English** — Auto-detected
- **Hindi (हिंदी)** — Devanagari Unicode detection
- **Tamil (தமிழ்)** — Tamil Unicode detection

## Memory Design

- **Session Memory**: Redis key `session:{id}`, TTL 1 hour. Stores last 10 conversation turns.
- **Persistent Memory**: Redis key `patient:{id}`. Stores name, language preference, last doctor, preferred hospital.
- **Fallback**: Both stores degrade gracefully to in-memory Python dicts if Redis is unavailable.

## Trade-offs & Known Limitations

- TTS/STT require OpenAI API key for production use; mock mode has no audio output.
- In-memory appointment store resets on restart; swap for PostgreSQL in production.
- Language detection is heuristic-based for Hindi/Tamil (Unicode ranges); very short texts may misclassify.
- No authentication on REST endpoints (add OAuth2/JWT for production).
