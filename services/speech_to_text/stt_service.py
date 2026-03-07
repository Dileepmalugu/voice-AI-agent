"""
STT Service - transcribes audio to text.
Uses OpenAI Whisper API if key available, else returns mock transcript.
"""
import os, base64, tempfile, logging
logger = logging.getLogger(__name__)

class STTService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY","")
        self.use_mock = not bool(self.api_key)
        if self.use_mock:
            logger.warning("STTService: No API key, mock mode active.")

    def transcribe_base64(self, audio_b64: str) -> str:
        if self.use_mock or not audio_b64:
            return "Book appointment with cardiologist tomorrow at 10 AM"
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            audio_bytes = base64.b64decode(audio_b64)
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
                f.write(audio_bytes); tmp = f.name
            with open(tmp, "rb") as af:
                result = client.audio.transcriptions.create(model="whisper-1", file=af)
            return result.text
        except Exception as e:
            logger.error(f"STT error: {e}")
            return ""
