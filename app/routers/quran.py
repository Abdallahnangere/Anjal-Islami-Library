from __future__ import annotations

from fastapi import APIRouter, Query

from app.db import get_conn


router = APIRouter(prefix="/v1/quran", tags=["quran"])


@router.get("/ayah/{surah}/{ayah}")
def get_ayah(surah: int, ayah: int) -> dict:
    conn = get_conn()
    row = conn.execute(
        """SELECT * FROM quran_ayahs WHERE surah_number = ? AND ayah_number_in_surah = ?""",
        (surah, ayah),
    ).fetchone()
    conn.close()
    if not row:
        return {"found": False}
    return {"found": True, "data": dict(row)}


@router.get("/search")
def search_quran(q: str = Query(..., min_length=1), limit: int = Query(20, ge=1, le=100)) -> dict:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT qa.* FROM quran_fts f
        JOIN quran_ayahs qa ON qa.id = f.rowid
        WHERE quran_fts MATCH ?
        LIMIT ?
        """,
        (q, limit),
    ).fetchall()
    conn.close()
    return {"query": q, "count": len(rows), "results": [dict(r) for r in rows]}
