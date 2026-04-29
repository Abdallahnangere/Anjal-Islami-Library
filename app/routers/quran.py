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
def search_quran(
    q: str = Query(..., min_length=1),
    surah: int | None = None,
    juz: int | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict:
    conn = get_conn()
    clauses = ["quran_fts MATCH ?"]
    params: list[object] = [q]

    if surah is not None:
        clauses.append("qa.surah_number = ?")
        params.append(surah)
    if juz is not None:
        clauses.append("qa.juz = ?")
        params.append(juz)

    where_sql = " AND ".join(clauses)
    rows = conn.execute(
        f"""
        SELECT qa.* FROM quran_fts f
        JOIN quran_ayahs qa ON qa.id = f.rowid
        WHERE {where_sql}
        LIMIT ? OFFSET ?
        """,
        (*params, limit, offset),
    ).fetchall()
    conn.close()
    return {
        "query": q,
        "surah": surah,
        "juz": juz,
        "offset": offset,
        "count": len(rows),
        "results": [dict(r) for r in rows],
    }
