"""
TTS Service - converts text to speech audio (base64).
Uses OpenAI TTS if key available, else returns empty string (mock).
"""
import os, base64, tempfile, logging
logger = logging.getLogger(__name__)

VOICE_MAP = {"en":"nova","hi":"nova","ta":"nova"}  # OpenAI TTS voices

class TTSService:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY","")
        self.use_mock = not bool(self.api_key)
        if self.use_mock:
            logger.warning("TTSService: No API key, mock mode active (no audio output).")

    def synthesize_base64(self, text: str, language: str = "en") -> str:
        if self.use_mock or not text:
            return ""
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            voice = VOICE_MAP.get(language, "nova")
            resp = client.audio.speech.create(model="tts-1", voice=voice, input=text, response_format="mp3")
            return base64.b64encode(resp.content).decode()
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return ""
