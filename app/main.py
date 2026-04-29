from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse

from app.bootstrap import ensure_db
from app.routers.hadith import router as hadith_router
from app.routers.hijri import router as hijri_router
from app.routers.meta import router as meta_router
from app.routers.prayer import router as prayer_router
from app.routers.quran import router as quran_router

ensure_db()


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


@app.get("/", response_class=HTMLResponse, tags=["home"])
def home() -> str:
    return """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Anjal Islamic Library API</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 40px; line-height: 1.5; color: #111; }
          h1 { margin-bottom: 8px; }
          p { margin-top: 0; }
          .links a { display: inline-block; margin: 6px 8px 6px 0; color: #0b57d0; text-decoration: none; }
          .links a:hover { text-decoration: underline; }
          code { background: #f5f5f5; padding: 2px 6px; border-radius: 4px; }
        </style>
      </head>
      <body>
        <h1>Anjal Islamic Library API</h1>
        <p>Versioned Islamic data API for Quran, Hadith, Hijri, and Prayer Times.</p>
        <p>Maintainer: <strong>Abdallah Nangere</strong></p>
        <p>Contact: <a href="mailto:founder@ramadanbot.app">founder@ramadanbot.app</a> | <a href="tel:+2348164135836">+2348164135836</a></p>
        <div class="links">
          <a href="/docs">API Docs</a>
          <a href="/v1/health">Health</a>
          <a href="/v1/meta">Meta</a>
          <a href="/v1/prayer/countries">Prayer Countries</a>
          <a href="/v1/quran/ayah/1/1">Quran 1:1</a>
          <a href="/v1/hadith/bukhari/15">Bukhari 15</a>
        </div>
        <p>Base path: <code>/v1</code></p>
      </body>
    </html>
    """


@app.exception_handler(Exception)
def fallback_error_handler(_, exc: Exception):
    return JSONResponse(status_code=500, content={"ok": False, "error": str(exc)})
