from __future__ import annotations

from fastapi import APIRouter
from fastapi import Request

from app.db import get_conn
from app.i18n import detect_lang
from app.i18n import tr


router = APIRouter(prefix="/v1/hijri", tags=["hijri"])


@router.get("/to-gregorian")
def to_gregorian(request: Request, year: int, month: int, day: int) -> dict:
    lang = detect_lang(request)
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
        return {"found": False, "lang": lang, "message": tr("not_found", lang)}
    return {"found": True, "lang": lang, "gregorian_iso": row["gregorian_iso"]}


@router.get("/from-gregorian")
def from_gregorian(request: Request, date: str) -> dict:
    lang = detect_lang(request)
    conn = get_conn()
    row = conn.execute("SELECT hijri_iso FROM hijri_dates WHERE gregorian_iso = ?", (date,)).fetchone()
    conn.close()
    if not row:
        return {"found": False, "lang": lang, "message": tr("not_found", lang)}
    return {"found": True, "lang": lang, "hijri_iso": row["hijri_iso"]}
