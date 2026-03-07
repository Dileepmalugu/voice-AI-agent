"""Language detection — uses langdetect with Unicode heuristics as fast pre-check."""
import re, logging
logger = logging.getLogger(__name__)

class LanguageDetector:
    HINDI_RANGE  = re.compile(r'[\u0900-\u097F]')
    TAMIL_RANGE  = re.compile(r'[\u0B80-\u0BFF]')

    def detect(self, text: str) -> str:
        if self.HINDI_RANGE.search(text):  return "hi"
        if self.TAMIL_RANGE.search(text):  return "ta"
        try:
            from langdetect import detect
            lang = detect(text)
            if lang in ("hi","ta","en"): return lang
        except Exception: pass
        return "en"
