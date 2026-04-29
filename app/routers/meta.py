from __future__ import annotations

from fastapi import APIRouter

from app.db import get_conn


router = APIRouter(prefix="/v1", tags=["meta"])


@router.get("/health")
def health() -> dict:
    return {"ok": True, "service": "Anjal Islamic Library API", "version": "v1"}


@router.get("/meta")
def meta() -> dict:
    conn = get_conn()
    cur = conn.cursor()
    counts = {}
    for table in ["quran_ayahs", "hadith_entries", "hijri_dates", "prayer_times"]:
        counts[table] = cur.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"]
    m = cur.execute("SELECT key, value FROM metadata").fetchall()
    conn.close()
    meta_map = {row["key"]: row["value"] for row in m}
    return {"service": "Anjal Islamic Library API", "version": "v1", "counts": counts, "metadata": meta_map}
