from __future__ import annotations

from fastapi import Request


SUPPORTED_LANGS = {"en", "ar"}

STRINGS: dict[str, dict[str, str]] = {
    "service_name": {"en": "Anjal Islamic Library API", "ar": "\u0648\u0627\u062c\u0647\u0629 \u062e\u0632\u0627\u0646\u0629 \u0623\u0646\u062c\u0644 \u0627\u0644\u0625\u0633\u0644\u0627\u0645\u064a\u0629"},
    "service_desc": {
        "en": "Versioned Islamic data API (Quran, Hadith, Hijri, Prayer Times)",
        "ar": "\u0648\u0627\u062c\u0647\u0629 \u0628\u064a\u0627\u0646\u0627\u062a \u0625\u0633\u0644\u0627\u0645\u064a\u0629 \u0628\u0625\u0635\u062f\u0627\u0631\u0627\u062a (\u0627\u0644\u0642\u0631\u0622\u0646\u060c \u0627\u0644\u062d\u062f\u064a\u062b\u060c \u0627\u0644\u0647\u062c\u0631\u064a\u060c \u0645\u0648\u0627\u0642\u064a\u062a \u0627\u0644\u0635\u0644\u0627\u0629)",
    },
    "health_ok": {"en": "service is healthy", "ar": "\u0627\u0644\u062e\u062f\u0645\u0629 \u062a\u0639\u0645\u0644 \u0628\u0634\u0643\u0644 \u0633\u0644\u064a\u0645"},
    "unauthorized": {"en": "unauthorized", "ar": "\u063a\u064a\u0631 \u0645\u0635\u0631\u062d"},
    "rate_limit_exceeded": {"en": "rate_limit_exceeded", "ar": "\u062a\u0645 \u062a\u062c\u0627\u0648\u0632 \u062d\u062f \u0627\u0644\u0637\u0644\u0628\u0627\u062a"},
    "not_found": {"en": "not found", "ar": "\u063a\u064a\u0631 \u0645\u0648\u062c\u0648\u062f"},
    "docs_title": {"en": "API Documentation", "ar": "\u062a\u0648\u062b\u064a\u0642 \u0627\u0644\u0648\u0627\u062c\u0647\u0629 \u0627\u0644\u0628\u0631\u0645\u062c\u064a\u0629"},
    "home_title": {"en": "Anjal Islamic Library API", "ar": "\u0648\u0627\u062c\u0647\u0629 \u062e\u0632\u0627\u0646\u0629 \u0623\u0646\u062c\u0644 \u0627\u0644\u0625\u0633\u0644\u0627\u0645\u064a\u0629"},
    "home_subtitle": {
        "en": "Versioned Islamic data infrastructure for reliable year-round products.",
        "ar": "\u0628\u0646\u064a\u0629 \u0628\u064a\u0627\u0646\u0627\u062a \u0625\u0633\u0644\u0627\u0645\u064a\u0629 \u0628\u0625\u0635\u062f\u0627\u0631\u0627\u062a \u0644\u0628\u0646\u0627\u0621 \u0645\u0646\u062a\u062c\u0627\u062a \u0645\u0648\u062b\u0648\u0642\u0629 \u0637\u0648\u0627\u0644 \u0627\u0644\u0639\u0627\u0645.",
    },
    "docs": {"en": "Docs", "ar": "\u0627\u0644\u062a\u0648\u062b\u064a\u0642"},
    "meta": {"en": "Meta", "ar": "\u0627\u0644\u0628\u064a\u0627\u0646\u0627\u062a \u0627\u0644\u0648\u0635\u0641\u064a\u0629"},
    "arabic": {"en": "Arabic", "ar": "\u0627\u0644\u0639\u0631\u0628\u064a\u0629"},
    "english": {"en": "English", "ar": "\u0627\u0644\u0625\u0646\u062c\u0644\u064a\u0632\u064a\u0629"},
}


def normalize_lang(value: str | None) -> str:
    if not value:
        return "en"
    v = value.strip().lower()
    if v.startswith("ar"):
        return "ar"
    return "en"


def detect_lang(request: Request, explicit: str | None = None) -> str:
    if explicit:
        lang = normalize_lang(explicit)
        return lang if lang in SUPPORTED_LANGS else "en"

    q = request.query_params.get("lang")
    if q:
        lang = normalize_lang(q)
        return lang if lang in SUPPORTED_LANGS else "en"

    header = request.headers.get("accept-language", "")
    if header:
        first = header.split(",")[0]
        lang = normalize_lang(first)
        return lang if lang in SUPPORTED_LANGS else "en"
    return "en"


def tr(key: str, lang: str) -> str:
    bucket = STRINGS.get(key, {})
    return bucket.get(lang) or bucket.get("en") or key
