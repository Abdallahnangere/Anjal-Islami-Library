from __future__ import annotations

from fastapi import APIRouter, Query

from app.db import get_conn


router = APIRouter(prefix="/v1/prayer", tags=["prayer"])


@router.get("/countries")
def countries() -> dict:
    conn = get_conn()
    rows = conn.execute("SELECT DISTINCT country FROM prayer_times ORDER BY country").fetchall()
    conn.close()
    return {"count": len(rows), "countries": [r["country"] for r in rows]}


@router.get("/cities")
def cities(country: str) -> dict:
    conn = get_conn()
    rows = conn.execute(
        "SELECT city FROM prayer_times WHERE lower(country) = lower(?) ORDER BY city", (country,)
    ).fetchall()
    conn.close()
    return {"country": country, "count": len(rows), "cities": [r["city"] for r in rows]}


@router.get("/times")
def times(country: str, city: str, date_gregorian: str | None = None) -> dict:
    conn = get_conn()
    if date_gregorian:
        row = conn.execute(
            """
            SELECT * FROM prayer_times
            WHERE lower(country)=lower(?) AND lower(city)=lower(?) AND date_gregorian=?
            LIMIT 1
            """,
            (country, city, date_gregorian),
        ).fetchone()
    else:
        row = conn.execute(
            """
            SELECT * FROM prayer_times
            WHERE lower(country)=lower(?) AND lower(city)=lower(?)
            ORDER BY date_gregorian DESC
            LIMIT 1
            """,
            (country, city),
        ).fetchone()
    conn.close()
    if not row:
        return {"found": False}
    return {"found": True, "data": dict(row)}


@router.get("/search-city")
def search_city(q: str = Query(..., min_length=1), limit: int = Query(50, ge=1, le=200)) -> dict:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT country, city, timezone, fajr, dhuhr, asr, maghrib, isha, date_gregorian
        FROM prayer_times
        WHERE city LIKE ?
        ORDER BY country, city
        LIMIT ?
        """,
        (f"%{q}%", limit),
    ).fetchall()
    conn.close()
    return {"query": q, "count": len(rows), "results": [dict(r) for r in rows]}
