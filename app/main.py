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
          :root {
            --bg: #0b1020;
            --panel: #121a31;
            --muted: #b2bfdc;
            --text: #e8eeff;
            --line: #263252;
            --accent: #79a7ff;
            --accent2: #53d3b6;
          }
          * { box-sizing: border-box; }
          body {
            margin: 0;
            font-family: Inter, Segoe UI, Roboto, Arial, sans-serif;
            line-height: 1.55;
            background: radial-gradient(1200px 500px at 15% -10%, #1b2850 0%, var(--bg) 50%),
                        radial-gradient(1000px 400px at 100% 0%, #12343f 0%, transparent 45%),
                        var(--bg);
            color: var(--text);
          }
          .wrap { max-width: 1080px; margin: 0 auto; padding: 28px 20px 56px; }
          .hero {
            border: 1px solid var(--line);
            background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));
            border-radius: 12px;
            padding: 24px;
          }
          h1 { margin: 0 0 8px; font-size: 36px; }
          .subtitle { margin: 0; color: var(--muted); font-size: 16px; }
          .meta { margin-top: 12px; color: var(--muted); font-size: 14px; }
          .badges { margin-top: 14px; display: flex; gap: 8px; flex-wrap: wrap; }
          .badge {
            border: 1px solid var(--line);
            background: rgba(121,167,255,0.12);
            color: #d9e5ff;
            border-radius: 999px;
            padding: 5px 10px;
            font-size: 12px;
          }
          .grid {
            margin-top: 18px;
            display: grid;
            grid-template-columns: repeat(12, minmax(0, 1fr));
            gap: 14px;
          }
          .card {
            grid-column: span 12;
            border: 1px solid var(--line);
            background: var(--panel);
            border-radius: 10px;
            padding: 16px;
          }
          @media (min-width: 860px) {
            .c6 { grid-column: span 6; }
            .c4 { grid-column: span 4; }
            .c8 { grid-column: span 8; }
          }
          h2 { margin: 0 0 10px; font-size: 18px; }
          p { margin: 0 0 10px; color: var(--muted); }
          a { color: var(--accent); text-decoration: none; }
          a:hover { text-decoration: underline; }
          ul { margin: 0; padding-left: 18px; color: var(--muted); }
          li { margin: 6px 0; }
          pre {
            margin: 10px 0 0;
            padding: 12px;
            background: #0a1227;
            border: 1px solid var(--line);
            border-radius: 8px;
            overflow-x: auto;
            color: #dfe8ff;
            font-size: 13px;
          }
          code { font-family: Consolas, Menlo, Monaco, monospace; }
          .quick a {
            display: inline-block;
            margin: 6px 8px 0 0;
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 8px 10px;
            background: #101a35;
            color: #dfe8ff;
          }
          .quick a:hover { background: #132145; text-decoration: none; }
          .foot { margin-top: 16px; color: var(--muted); font-size: 13px; }
        </style>
      </head>
      <body>
        <div class="wrap">
          <section class="hero">
            <h1>Anjal Islamic Library API</h1>
            <p class="subtitle">A versioned, searchable Islamic data API for Quran, Hadith, Hijri conversion, and Prayer Times.</p>
            <p class="meta">Maintainer: <strong>Abdallah Nangere</strong> · <a href="mailto:founder@ramadanbot.app">founder@ramadanbot.app</a> · <a href="tel:+2348164135836">+2348164135836</a></p>
            <div class="badges">
              <span class="badge">Version: v1</span>
              <span class="badge">SQLite + FTS5</span>
              <span class="badge">Arabic + English</span>
              <span class="badge">Nigeria + Global Prayer Coverage</span>
            </div>
          </section>

          <section class="grid">
            <article class="card c6">
              <h2>About</h2>
              <p>This API is designed as a reusable library backend for apps built by Anjal Ventures and the wider developer community. It packages curated datasets into stable endpoints.</p>
              <ul>
                <li>Quran: Uthmani Arabic + Sahih English</li>
                <li>Hadith: merged Arabic/English collections</li>
                <li>Hijri: Umm al-Qura conversion table</li>
                <li>Prayer Times: all Nigeria entries plus selected major countries</li>
              </ul>
            </article>

            <article class="card c6">
              <h2>Docs & Quick Links</h2>
              <p>Use interactive docs for full schemas, try-it-out calls, and parameter details.</p>
              <div class="quick">
                <a href="/docs">Open Swagger Docs</a>
                <a href="/v1/health">Health</a>
                <a href="/v1/meta">Meta</a>
                <a href="/v1/prayer/countries">Prayer Countries</a>
                <a href="/v1/quran/ayah/1/1">Quran 1:1</a>
                <a href="/v1/hadith/bukhari/15">Bukhari 15</a>
              </div>
            </article>

            <article class="card c4">
              <h2>Setup</h2>
              <pre><code>pip install -r requirements.txt
python scripts/build_db.py
uvicorn app.main:app --host 127.0.0.1 --port 8000</code></pre>
            </article>

            <article class="card c8">
              <h2>Request Samples</h2>
              <pre><code>GET /v1/quran/search?q=mercy&amp;limit=5
GET /v1/hadith/search?q=prayer&amp;collection=bukhari&amp;limit=5
GET /v1/hijri/from-gregorian?date=2026-04-29
GET /v1/prayer/times?country=Nigeria&amp;city=Lagos%20Island</code></pre>
            </article>
          </section>
          <p class="foot">Base path: <code>/v1</code></p>
        </div>
      </body>
    </html>
    """


@app.exception_handler(Exception)
def fallback_error_handler(_, exc: Exception):
    return JSONResponse(status_code=500, content={"ok": False, "error": str(exc)})
