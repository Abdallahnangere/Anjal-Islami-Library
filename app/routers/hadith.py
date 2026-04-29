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
    book_number: int | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict:
    conn = get_conn()
    clauses = ["hadith_fts MATCH ?"]
    params: list[object] = [q]

    if collection:
        clauses.append("lower(h.collection_key) = lower(?)")
        params.append(collection)
    if book_number is not None:
        clauses.append("h.book_number = ?")
        params.append(book_number)

    where_sql = " AND ".join(clauses)
    rows = conn.execute(
        f"""
        SELECT h.* FROM hadith_fts f
        JOIN hadith_entries h ON h.id = f.rowid
        WHERE {where_sql}
        LIMIT ? OFFSET ?
        """,
        (*params, limit, offset),
    ).fetchall()
    conn.close()
    return {
        "query": q,
        "collection": collection,
        "book_number": book_number,
        "offset": offset,
        "count": len(rows),
        "results": [dict(r) for r in rows],
    }
