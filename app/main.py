from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.routers.hadith import router as hadith_router
from app.routers.hijri import router as hijri_router
from app.routers.meta import router as meta_router
from app.routers.prayer import router as prayer_router
from app.routers.quran import router as quran_router


app = FastAPI(
    title="Anjal Islamic Library API",
    version="1.0.0",
    description="Versioned Islamic data API (Quran, Hadith, Hijri, Prayer Times)",
)

app.include_router(meta_router)
app.include_router(quran_router)
app.include_router(hadith_router)
app.include_router(hijri_router)
app.include_router(prayer_router)


@app.exception_handler(Exception)
def fallback_error_handler(_, exc: Exception):
    return JSONResponse(status_code=500, content={"ok": False, "error": str(exc)})
