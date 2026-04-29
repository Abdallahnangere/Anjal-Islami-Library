from __future__ import annotations

from fastapi import APIRouter, Query

from app.db import get_conn


router = APIRouter(prefix="/v1/hadith", tags=["hadith"])


@router.get("/{collection}/{hadith_number}")
def get_hadith(collection: str, hadith_number: int) -> dict:
    conn = get_conn()
    row = conn.execute(
        """
        SELECT * FROM hadith_entries
        WHERE lower(collection_key) = lower(?) AND hadith_number = ?
        """,
        (collection, hadith_number),
    ).fetchone()
    conn.close()
    if not row:
        return {"found": False}
    return {"found": True, "data": dict(row)}


@router.get("/search")
def search_hadith(
    q: str = Query(..., min_length=1),
    collection: str | None = None,
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    conn = get_conn()
    if collection:
        rows = conn.execute(
            """
            SELECT h.* FROM hadith_fts f
            JOIN hadith_entries h ON h.id = f.rowid
            WHERE hadith_fts MATCH ? AND lower(h.collection_key) = lower(?)
            LIMIT ?
            """,
            (q, collection, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT h.* FROM hadith_fts f
            JOIN hadith_entries h ON h.id = f.rowid
            WHERE hadith_fts MATCH ?
            LIMIT ?
            """,
            (q, limit),
        ).fetchall()
    conn.close()
    return {"query": q, "collection": collection, "count": len(rows), "results": [dict(r) for r in rows]}
