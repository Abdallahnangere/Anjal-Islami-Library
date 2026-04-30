from __future__ import annotations

from fastapi import APIRouter
from fastapi import Request

from app.db import get_conn
from app.i18n import detect_lang
from app.i18n import tr


router = APIRouter(prefix="/v1", tags=["meta"])


@router.get("/health")
def health(request: Request) -> dict:
    lang = detect_lang(request)
    return {"ok": True, "lang": lang, "message": tr("health_ok", lang), "service": tr("service_name", lang), "version": "v1"}


@router.get("/meta")
def meta(request: Request) -> dict:
    lang = detect_lang(request)
    conn = get_conn()
    cur = conn.cursor()
    counts = {}
    for table in ["quran_ayahs", "hadith_entries", "hijri_dates", "prayer_times"]:
        counts[table] = cur.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"]
    m = cur.execute("SELECT key, value FROM metadata").fetchall()
    conn.close()
    meta_map = {row["key"]: row["value"] for row in m}
    return {"lang": lang, "service": tr("service_name", lang), "version": "v1", "counts": counts, "metadata": meta_map}
