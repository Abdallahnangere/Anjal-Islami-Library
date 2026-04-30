from __future__ import annotations

import os
import threading
import time

from fastapi import FastAPI
from fastapi import Request
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse
from fastapi.responses import JSONResponse
from fastapi.responses import RedirectResponse

from app.bootstrap import ensure_db
from app.i18n import detect_lang
from app.i18n import tr
from app.routers.hadith import router as hadith_router
from app.routers.hijri import router as hijri_router
from app.routers.meta import router as meta_router
from app.routers.prayer import router as prayer_router
from app.routers.quran import router as quran_router

ensure_db()

app = FastAPI(
    title=tr("service_name", "en"),
    version="1.1.0",
    description=tr("service_desc", "en"),
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.include_router(meta_router)
app.include_router(quran_router)
app.include_router(hadith_router)
app.include_router(hijri_router)
app.include_router(prayer_router)

_rate_lock = threading.Lock()
_rate_buckets: dict[str, tuple[float, int]] = {}


def _parse_api_keys() -> set[str]:
    raw = os.getenv("ANJAL_API_KEYS", "")
    return {part.strip() for part in raw.split(",") if part.strip()}


def _get_env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def _extract_api_key(request: Request) -> str | None:
    x_api_key = request.headers.get("X-API-Key")
    if x_api_key and x_api_key.strip():
        return x_api_key.strip()
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None
    parts = auth_header.strip().split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer" and parts[1].strip():
        return parts[1].strip()
    return None


@app.middleware("http")
async def v1_auth_and_rate_limit(request: Request, call_next):
    path = request.url.path
    lang = detect_lang(request)
    if not path.startswith("/v1"):
        return await call_next(request)

    configured_keys = _parse_api_keys()
    provided_key = _extract_api_key(request)
    if configured_keys and provided_key not in configured_keys:
        return JSONResponse(status_code=401, content={"ok": False, "lang": lang, "error": tr("unauthorized", lang)})

    window_sec = _get_env_int("ANJAL_RATE_LIMIT_WINDOW_SEC", 60)
    max_requests = _get_env_int("ANJAL_RATE_LIMIT_MAX_REQUESTS", 120)
    now = time.time()
    client_host = request.client.host if request.client else "unknown"
    identity = provided_key if provided_key else f"ip:{client_host}"

    with _rate_lock:
        start, count = _rate_buckets.get(identity, (now, 0))
        if now - start >= window_sec:
            start, count = now, 0
        count += 1
        _rate_buckets[identity] = (start, count)
        if count > max_requests:
            retry_after = max(1, int(window_sec - (now - start)))
            return JSONResponse(
                status_code=429,
                content={"ok": False, "lang": lang, "error": tr("rate_limit_exceeded", lang)},
                headers={"Retry-After": str(retry_after)},
            )

    return await call_next(request)


@app.get("/", response_class=HTMLResponse, tags=["home"])
def home(request: Request) -> str:
    lang = detect_lang(request)
    dir_attr = "rtl" if lang == "ar" else "ltr"
    title = tr("home_title", lang) if lang == "ar" else "Anjal Islamic Library API"
    subtitle = (
        tr("home_subtitle", lang)
        if lang == "ar"
        else "Versioned Islamic data infrastructure for building reliable year-round products: Quran, Hadith, Hijri, and Prayer Times."
    )
    docs_label = tr("docs", lang) if lang == "ar" else "Docs"
    meta_label = tr("meta", lang) if lang == "ar" else "Meta"
    language_switch = tr("english", lang) if lang == "ar" else tr("arabic", lang)
    switch_lang = "en" if lang == "ar" else "ar"
    return f"""
    <!doctype html>
    <html lang="{lang}" dir="{dir_attr}">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>{title}</title>
        <style>
          :root {{ --bg:#f7f9fc; --panel:#ffffff; --muted:#4e5b76; --text:#0f1728; --line:#d8e0ef; --accent:#1f5eff; }}
          * {{ box-sizing: border-box; }}
          body {{ margin:0; font-family: Inter, Segoe UI, Arial, sans-serif; line-height:1.55; background:var(--bg); color:var(--text); }}
          .wrap {{ max-width:1120px; margin:0 auto; padding:24px 18px 56px; }}
          .top {{ background:var(--panel); border-bottom:1px solid var(--line); }}
          .topin {{ max-width:1120px; margin:0 auto; padding:14px 18px; display:flex; justify-content:space-between; gap:12px; align-items:center; }}
          .brand {{ font-weight:700; }}
          .nav a {{ margin-inline-start:12px; font-size:14px; }}
          .hero {{ background:var(--panel); border:1px solid var(--line); border-radius:10px; padding:22px; }}
          h1 {{ margin:0 0 8px; font-size:34px; }}
          .subtitle,.meta,p,li {{ color:var(--muted); }}
          .meta {{ font-size:14px; }}
          .pill {{ display:inline-block; border:1px solid var(--line); border-radius:999px; padding:4px 10px; font-size:12px; margin:6px 6px 0 0; background:#eef3ff; }}
          .grid {{ margin-top:16px; display:grid; grid-template-columns:repeat(12,minmax(0,1fr)); gap:14px; }}
          .card {{ grid-column:span 12; border:1px solid var(--line); background:var(--panel); border-radius:10px; padding:16px; }}
          @media (min-width: 900px){{ .c4{{grid-column:span 4;}} .c6{{grid-column:span 6;}} .c8{{grid-column:span 8;}} }}
          h2{{margin:0 0 10px; font-size:18px;}} h3{{margin:14px 0 8px; font-size:15px;}}
          .footer {{ margin-top:16px; border:1px solid var(--line); background:var(--panel); border-radius:10px; padding:14px; font-size:13px; color:var(--muted); }}
          a {{ color: var(--accent); text-decoration: none; }}
          a:hover {{ text-decoration: underline; }}
          ul {{ margin:0; padding-left:18px; }}
          table{{ width:100%; border-collapse:collapse; font-size:14px; }}
          th,td{{ border:1px solid var(--line); padding:8px; text-align:left; vertical-align:top; }}
          th{{ background:#f1f5ff; color:#233156; }}
          pre{{ margin:8px 0 0; padding:10px; background:#f5f8ff; border:1px solid var(--line); border-radius:8px; overflow:auto; font-size:12px; color:#0e1a3a; }}
          code{{ font-family:Consolas, Menlo, monospace; }}
        </style>
      </head>
      <body>
        <header class="top">
          <div class="topin">
            <div class="brand">Anjal Islamic Library API</div>
            <nav class="nav">
              <a href="/docs?lang={lang}">{docs_label}</a>
              <a href="/v1/meta?lang={lang}">{meta_label}</a>
              <a href="https://github.com/Abdallahnangere/Anjal-Islamic-Library">GitHub</a>
              <a href="/?lang={switch_lang}">{language_switch}</a>
            </nav>
          </div>
        </header>
        <div class="wrap">
          <section class="hero">
            <h1>{title}</h1>
            <p class="subtitle">{subtitle}</p>
            <p class="meta">Maintainer: <strong>Abdallah Nangere</strong> · <a href="mailto:founder@ramadanbot.app">founder@ramadanbot.app</a> · <a href="tel:+2348164135836">+2348164135836</a></p>
            <p class="meta">Production endpoint: <a href="https://islamiclibrary.anjalventures.com">https://islamiclibrary.anjalventures.com</a> (HTTPS-only; HTTP returns 308 redirect).</p>
            <div>
              <span class="pill">API Version: v1</span>
              <span class="pill">FastAPI</span>
              <span class="pill">SQLite + FTS5</span>
              <span class="pill">Arabic + English</span>
              <span class="pill">Public Reuse Friendly</span>
            </div>
          </section>
          <section class="grid">
            <article class="card c4">
              <h2>About</h2>
              <p>This API is a reusable backend for Islamic applications and research tools. It standardizes references, search, and date/prayer lookup.</p>
              <ul>
                <li>Quran (Uthmani + English)</li>
                <li>Hadith (10 collections)</li>
                <li>Umm al-Qura Hijri conversion</li>
                <li>Nigeria-complete prayer times</li>
              </ul>
            </article>
            <article class="card c8">
              <h2>Coverage Summary</h2>
              <table>
                <tr><th>Dataset</th><th>Coverage</th><th>Rows</th><th>Primary Source</th></tr>
                <tr><td>Quran</td><td>114 Surahs, 6,236 Ayahs</td><td>6,236</td><td>AlQuran Cloud editions</td></tr>
                <tr><td>Hadith</td><td>Arabic+English merged collections</td><td>36,512</td><td>Hadith API open corpus</td></tr>
                <tr><td>Hijri</td><td>1343-01-01 AH to 1500-12-30 AH</td><td>55,991</td><td>Umm al-Qura table</td></tr>
                <tr><td>Prayer Times</td><td>All Nigeria entries + selected global cities</td><td>836</td><td>AlAdhan API snapshots</td></tr>
              </table>
            </article>
            <article class="card c4">
              <h2>Quick Start</h2>
              <pre><code>pip install -r requirements.txt
python scripts/build_db.py
uvicorn app.main:app --host 127.0.0.1 --port 8000</code></pre>
              <h3>Base URL</h3>
              <pre><code>/v1</code></pre>
            </article>
            <article class="card c8">
              <h2>Endpoint Matrix</h2>
              <table>
                <tr><th>Domain</th><th>Endpoint</th><th>Purpose</th></tr>
                <tr><td>Meta</td><td><code>GET /v1/health</code></td><td>Service health ping</td></tr>
                <tr><td>Meta</td><td><code>GET /v1/meta</code></td><td>Counts and metadata</td></tr>
                <tr><td>Quran</td><td><code>GET /v1/quran/ayah/{{surah}}/{{ayah}}</code></td><td>Direct ayah lookup</td></tr>
                <tr><td>Quran</td><td><code>GET /v1/quran/search?q=</code></td><td>Full-text search</td></tr>
                <tr><td>Hadith</td><td><code>GET /v1/hadith/{{collection}}/{{hadith_number}}</code></td><td>Canonical hadith lookup</td></tr>
                <tr><td>Hadith</td><td><code>GET /v1/hadith/search?q=</code></td><td>Full-text search</td></tr>
                <tr><td>Hijri</td><td><code>GET /v1/hijri/to-gregorian</code></td><td>Hijri to Gregorian</td></tr>
                <tr><td>Hijri</td><td><code>GET /v1/hijri/from-gregorian</code></td><td>Gregorian to Hijri</td></tr>
                <tr><td>Prayer</td><td><code>GET /v1/prayer/countries</code></td><td>Country list</td></tr>
                <tr><td>Prayer</td><td><code>GET /v1/prayer/cities?country=</code></td><td>Cities by country</td></tr>
                <tr><td>Prayer</td><td><code>GET /v1/prayer/times?country=&city=</code></td><td>Prayer times by location/date</td></tr>
                <tr><td>Prayer</td><td><code>GET /v1/prayer/search-city?q=</code></td><td>City search helper</td></tr>
              </table>
            </article>
            <article class="card c6">
              <h2>Request & Response Samples</h2>
              <pre><code>GET /v1/quran/ayah/1/1
{{"found":true,"data":{{"surah_number":1,"ayah_number_in_surah":1}}}}</code></pre>
              <pre><code>GET /v1/hijri/from-gregorian?date=2026-04-29
{{"found":true,"hijri_iso":"1447-11-12"}}</code></pre>
              <pre><code>GET /v1/prayer/search-city?q=Lagos
{{"query":"Lagos","count":2,"results":[{{"city":"Lagos Island"}}]}}</code></pre>
            </article>
            <article class="card c6">
              <h2>Governance, Licensing, and Usage</h2>
              <ul>
                <li>License: see <code>LICENSE</code> in repository.</li>
                <li>Attribution is recommended when redistributing transformed data.</li>
                <li>For production clients, enforce API keys and rate limiting at gateway level.</li>
                <li>Versioning policy: breaking changes move to next major path (e.g., <code>/v2</code>).</li>
                <li>Support contact: founder@ramadanbot.app</li>
              </ul>
              <h3>Developer Resources</h3>
              <ul>
                <li><a href="/docs?lang={lang}">Swagger Docs</a></li>
                <li><a href="/v1/meta?lang={lang}">Dataset Metadata</a></li>
                <li><a href="https://github.com/Abdallahnangere/Anjal-Islamic-Library">GitHub Repository</a></li>
              </ul>
            </article>
          </section>
          <section class="footer">
            <div><strong>Anjal Islamic Library API</strong> © 2026 Anjal Ventures. All rights reserved.</div>
            <div>Built by Abdallah Nangere for Ramadanbot and broader Islamic software ecosystem use.</div>
            <div>Primary contact: <a href="mailto:founder@ramadanbot.app">founder@ramadanbot.app</a> · <a href="tel:+2348164135836">+2348164135836</a></div>
          </section>
        </div>
      </body>
    </html>
    """


@app.get("/docs", include_in_schema=False)
def custom_docs(request: Request):
    lang = detect_lang(request)
    return get_swagger_ui_html(
        openapi_url=f"/openapi.json?lang={lang}",
        title=f"{tr('service_name', lang)} - {tr('docs_title', lang)}",
    )


@app.get("/docs/ar", include_in_schema=False)
def custom_docs_ar():
    return RedirectResponse(url="/docs?lang=ar")


@app.get("/docs/en", include_in_schema=False)
def custom_docs_en():
    return RedirectResponse(url="/docs?lang=en")


@app.get("/openapi.json", include_in_schema=False)
def openapi_endpoint(request: Request):
    lang = detect_lang(request)
    schema = get_openapi(
        title=tr("service_name", lang),
        version=app.version,
        description=tr("service_desc", lang),
        routes=app.routes,
    )
    return JSONResponse(schema)


@app.exception_handler(Exception)
def fallback_error_handler(request: Request, exc: Exception):
    lang = detect_lang(request)
    return JSONResponse(status_code=500, content={"ok": False, "lang": lang, "error": str(exc)})
