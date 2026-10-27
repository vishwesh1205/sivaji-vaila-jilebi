from langdetect import LangDetectException, detect

from ..config import settings


def detect_language(text: str) -> str:
    if not text:
        return "en"
    try:
        return detect(text)
    except LangDetectException:
        return "en"


def translate_text(text: str, language: str) -> str:
    if language.startswith("en") or not text:
        return text
    if not settings.enable_translation:
        return text
    # No external translation provider is called by default. This stub is
    # deliberately labelled so translated text is never mistaken for authoritative.
    return f"[MACHINE TRANSLATION – {settings.translation_provider} stub; officer verification required] {text}"
