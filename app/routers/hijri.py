from __future__ import annotations

from fastapi import APIRouter

from app.db import get_conn


router = APIRouter(prefix="/v1/hijri", tags=["hijri"])


@router.get("/to-gregorian")
def to_gregorian(year: int, month: int, day: int) -> dict:
    conn = get_conn()
    row = conn.execute(
        """
        SELECT gregorian_iso FROM hijri_dates
        WHERE hijri_year = ? AND hijri_month = ? AND hijri_day = ?
        """,
        (year, month, day),
    ).fetchone()
    conn.close()
    if not row:
        return {"found": False}
    return {"found": True, "gregorian_iso": row["gregorian_iso"]}


@router.get("/from-gregorian")
def from_gregorian(date: str) -> dict:
    conn = get_conn()
    row = conn.execute("SELECT hijri_iso FROM hijri_dates WHERE gregorian_iso = ?", (date,)).fetchone()
    conn.close()
    if not row:
        return {"found": False}
    return {"found": True, "hijri_iso": row["hijri_iso"]}
