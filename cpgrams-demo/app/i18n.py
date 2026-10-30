from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

I18N_DIR = Path(__file__).resolve().parent / "i18n"
SUPPORTED_LANGUAGES = {"en", "hi", "ta"}
DEFAULT_LANGUAGE = "en"


@lru_cache(maxsize=1)
def languages() -> list[dict]:
    with open(I18N_DIR / "languages.json", encoding="utf-8") as handle:
        return json.load(handle)


def language_codes() -> set[str]:
    return {item["code"] for item in languages()}


def language_info(code: str) -> dict:
    return next((item for item in languages() if item["code"] == code), languages()[0])


def normalise_language(code: str | None) -> str:
    code = (code or "").strip().lower()
    return code if code in language_codes() else DEFAULT_LANGUAGE


@lru_cache(maxsize=32)
def catalog(code: str) -> dict[str, str]:
    code = normalise_language(code)
    path = I18N_DIR / f"{code}.json"
    if not path.exists():
        code = DEFAULT_LANGUAGE
        path = I18N_DIR / f"{code}.json"
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def translate(key: str, lang: str = DEFAULT_LANGUAGE) -> str:
    lang = normalise_language(lang)
    value = catalog(lang).get(key)
    if value:
        return value
    return catalog(DEFAULT_LANGUAGE).get(key, key)


def fallback_active(lang: str) -> bool:
    code = (lang or "").strip().lower()
    return code in language_codes() and code not in SUPPORTED_LANGUAGES
