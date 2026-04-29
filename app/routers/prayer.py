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
def cities(
    country: str,
    q: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    conn = get_conn()
    if q:
        rows = conn.execute(
            """
            SELECT city FROM prayer_times
            WHERE lower(country) = lower(?) AND city LIKE ?
            ORDER BY city
            LIMIT ? OFFSET ?
            """,
            (country, f"%{q}%", limit, offset),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT city FROM prayer_times
            WHERE lower(country) = lower(?)
            ORDER BY city
            LIMIT ? OFFSET ?
            """,
            (country, limit, offset),
        ).fetchall()
    conn.close()
    return {
        "country": country,
        "query": q,
        "offset": offset,
        "count": len(rows),
        "cities": [r["city"] for r in rows],
    }


@router.get("/times")
def times(country: str, city: str, date_gregorian: str | None = None) -> dict:
    conn = get_conn()
    requested_date = date_gregorian
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
        return {"found": False, "requested_date_gregorian": requested_date, "effective_date_gregorian": None}
    row_data = dict(row)
    return {
        "found": True,
        "requested_date_gregorian": requested_date,
        "effective_date_gregorian": row_data.get("date_gregorian"),
        "data": row_data,
    }


@router.get("/search-city")
def search_city(
    q: str = Query(..., min_length=1),
    country: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> dict:
    conn = get_conn()
    if country:
        rows = conn.execute(
            """
            SELECT country, city, timezone, fajr, dhuhr, asr, maghrib, isha, date_gregorian
            FROM prayer_times
            WHERE city LIKE ? AND lower(country) = lower(?)
            ORDER BY country, city
            LIMIT ? OFFSET ?
            """,
            (f"%{q}%", country, limit, offset),
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT country, city, timezone, fajr, dhuhr, asr, maghrib, isha, date_gregorian
            FROM prayer_times
            WHERE city LIKE ?
            ORDER BY country, city
            LIMIT ? OFFSET ?
            """,
            (f"%{q}%", limit, offset),
        ).fetchall()
    conn.close()
    return {
        "query": q,
        "country": country,
        "offset": offset,
        "count": len(rows),
        "results": [dict(r) for r in rows],
    }
