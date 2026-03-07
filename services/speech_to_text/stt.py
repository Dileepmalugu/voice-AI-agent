"""
Speech-to-Text Service
Uses OpenAI Whisper API (cloud) or local Whisper model.
"""
import io
import os
from typing import Optional

import openai


class SpeechToTextService:
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", "sk-..."))
        self.use_local = os.getenv("USE_LOCAL_WHISPER", "false").lower() == "true"

        if self.use_local:
            import whisper
            self.local_model = whisper.load_model("base")

    async def transcribe(self, audio_bytes: bytes, language: Optional[str] = None) -> str:
        """
        Transcribe audio bytes to text.
        
        Args:
            audio_bytes: Raw audio (WAV, MP3, WebM, etc.)
            language:    ISO 639-1 language hint (optional; auto-detect if None)
        
        Returns:
            Transcribed text string.
        """
        if not audio_bytes:
            return ""

        if self.use_local:
            return await self._transcribe_local(audio_bytes, language)
        else:
            return await self._transcribe_openai(audio_bytes, language)

    async def _transcribe_openai(self, audio_bytes: bytes, language: Optional[str]) -> str:
        """Use OpenAI Whisper API."""
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.webm"

        kwargs = {"model": "whisper-1", "file": audio_file}
        if language:
            kwargs["language"] = language   # e.g. "en", "hi", "ta"

        transcript = await self.client.audio.transcriptions.create(**kwargs)
        return transcript.text.strip()

    async def _transcribe_local(self, audio_bytes: bytes, language: Optional[str]) -> str:
        """Use local Whisper model (runs synchronously in thread pool)."""
        import asyncio
        import tempfile
        import functools

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name

        loop = asyncio.get_event_loop()
        opts = {"language": language} if language else {}
        result = await loop.run_in_executor(
            None,
            functools.partial(self.local_model.transcribe, tmp_path, **opts),
        )
        return result["text"].strip()
