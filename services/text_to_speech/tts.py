"""
Text-to-Speech Service
Supports OpenAI TTS (fast) with language-aware voice selection.
"""
import os
from typing import Optional

import openai


# Language → voice mapping for OpenAI TTS
VOICE_MAP = {
    "en": "alloy",    # Neutral English voice
    "hi": "nova",     # Works well for Hindi
    "ta": "nova",     # Works well for Tamil
}


class TextToSpeechService:
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", "sk-..."))
        self.model = "tts-1"    # tts-1 is faster; tts-1-hd is higher quality

    async def synthesize(self, text: str, language: str = "en") -> bytes:
        """
        Convert text to speech audio bytes (MP3).
        
        Args:
            text:     Text to synthesize.
            language: ISO 639-1 code ("en", "hi", "ta").
        
        Returns:
            MP3 audio bytes.
        """
        if not text.strip():
            return b""

        voice = VOICE_MAP.get(language, "alloy")

        response = await self.client.audio.speech.create(
            model=self.model,
            voice=voice,
            input=text,
            response_format="mp3",
            speed=1.0,
        )

        # Collect streamed bytes
        audio_bytes = b""
        async for chunk in response.iter_bytes():
            audio_bytes += chunk

        return audio_bytes
