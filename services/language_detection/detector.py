"""
Language Detection Service
Uses langdetect library with fallback to Unicode script detection.
"""
import unicodedata
from typing import Optional


class LanguageDetector:
    """
    Lightweight language detector.
    Priority order:
      1. Script-based heuristic (fast, no API)
      2. langdetect library
    """

    async def detect(self, text: str) -> str:
        """
        Detect language of text.
        Returns ISO 639-1 code: 'en', 'hi', or 'ta'.
        Defaults to 'en' on failure.
        """
        if not text.strip():
            return "en"

        # Fast script heuristic
        detected = self._script_heuristic(text)
        if detected:
            return detected

        # Fallback: langdetect
        try:
            from langdetect import detect as ld_detect
            lang = ld_detect(text)
            # Map to our 3 supported languages
            return self._normalize_lang(lang)
        except Exception:
            return "en"

    def _script_heuristic(self, text: str) -> Optional[str]:
        """
        Check Unicode script blocks for fast language detection.
        Devanagari → Hindi, Tamil script → Tamil.
        """
        devanagari_count = 0
        tamil_count = 0

        for char in text:
            cp = ord(char)
            if 0x0900 <= cp <= 0x097F:   # Devanagari (Hindi)
                devanagari_count += 1
            elif 0x0B80 <= cp <= 0x0BFF: # Tamil
                tamil_count += 1

        total = len(text)
        if devanagari_count / total > 0.2:
            return "hi"
        if tamil_count / total > 0.2:
            return "ta"
        return None

    def _normalize_lang(self, lang: str) -> str:
        """Map langdetect output to our supported languages."""
        mapping = {
            "en": "en",
            "hi": "hi",
            "ta": "ta",
            # Common false-positives for Hindi
            "mr": "hi",   # Marathi uses Devanagari
            "ne": "hi",   # Nepali uses Devanagari
        }
        return mapping.get(lang, "en")
