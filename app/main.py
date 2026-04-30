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
    title = tr("home_title", lang)
    subtitle = tr("home_subtitle", lang)
    docs_label = tr("docs", lang)
    meta_label = tr("meta", lang)
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
          .footer {{ margin-top:16px; border:1px solid var(--line); background:var(--panel); border-radius:10px; padding:14px; font-size:13px; color:var(--muted); }}
          a {{ color: var(--accent); text-decoration: none; }}
          a:hover {{ text-decoration: underline; }}
        </style>
      </head>
      <body>
        <header class="top">
          <div class="topin">
            <div class="brand">{title}</div>
            <nav class="nav">
              <a href="/docs?lang={lang}">{docs_label}</a>
              <a href="/v1/meta?lang={lang}">{meta_label}</a>
              <a href="https://github.com/Abdallahnangere/Anjal-Islami-Library">GitHub</a>
              <a href="/?lang={switch_lang}">{language_switch}</a>
            </nav>
          </div>
        </header>
        <div class="wrap">
          <section class="hero">
            <h1>{title}</h1>
            <p class="subtitle">{subtitle}</p>
            <p class="meta">Maintainer: <strong>Abdallah Nangere</strong> | <a href="mailto:founder@ramadanbot.app">founder@ramadanbot.app</a> | <a href="tel:+2348164135836">+2348164135836</a></p>
            <p class="meta">Production endpoint: <a href="https://islamiclibrary.anjalventures.com">https://islamiclibrary.anjalventures.com</a></p>
            <div>
              <span class="pill">API Version: v1.1</span>
              <span class="pill">FastAPI</span>
              <span class="pill">SQLite + FTS5</span>
              <span class="pill">Arabic + English</span>
            </div>
          </section>
          <section class="footer">
            <div><strong>{title}</strong> (c) 2026 Anjal Ventures.</div>
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
