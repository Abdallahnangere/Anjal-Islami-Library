from __future__ import annotations

import json
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
from fastapi.staticfiles import StaticFiles

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
    version="1.2.0",
    description=tr("service_desc", "en"),
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "static")), name="static")

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


@app.middleware("http")
async def enforce_utf8_content_type(request: Request, call_next):
    response = await call_next(request)
    content_type = response.headers.get("content-type", "")
    if content_type.startswith("application/json") and "charset=" not in content_type.lower():
        response.headers["content-type"] = "application/json; charset=utf-8"
    if content_type.startswith("text/html") and "charset=" not in content_type.lower():
        response.headers["content-type"] = "text/html; charset=utf-8"
    return response


@app.get("/", response_class=HTMLResponse, tags=["home"])
def home() -> str:
    gallery_dir = os.path.join(os.path.dirname(__file__), "static", "gallery")
    gallery_images: list[str] = []
    if os.path.isdir(gallery_dir):
        for name in sorted(os.listdir(gallery_dir)):
            lower = name.lower()
            if lower.endswith((".jpg", ".jpeg", ".png", ".webp")):
                gallery_images.append(f"/static/gallery/{name}")
    if not gallery_images:
        gallery_images = ["/static/hero-1.png", "/static/hero-2.png", "/static/hero-3.png"]
    gallery_json = json.dumps(gallery_images)

    html = """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>At-Tibyan Centre | Premium Learning Studio</title>
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Manrope:wght@400;500;600;700;800&family=Noto+Naskh+Arabic:wght@500;600;700&display=swap" rel="stylesheet">
        <style>
          :root{
            --bg:#f3f6f2;
            --ink:#14231d;
            --muted:#5f7268;
            --line:#d5dfd8;
            --panel:#ffffff;
            --panel-soft:#fbfdfb;
            --brand:#2f6e56;
            --brand-deep:#1d4b3b;
            --accent:#b88c4a;
            --shadow:0 20px 40px rgba(21,45,36,.08);
          }
          *{box-sizing:border-box}
          html{scroll-behavior:smooth}
          body{
            margin:0;
            color:var(--ink);
            background:
              radial-gradient(70rem 40rem at -10% -10%, #eaf6ee 0%, rgba(234,246,238,0) 70%),
              radial-gradient(65rem 35rem at 110% -10%, #f2ece2 0%, rgba(242,236,226,0) 70%),
              var(--bg);
            font-family:"Manrope","Trebuchet MS",sans-serif;
            line-height:1.6;
          }
          .ambient{
            position:fixed;
            inset:0;
            pointer-events:none;
            z-index:-1;
            background:
              radial-gradient(42rem 20rem at 20% 10%, rgba(47,110,86,.09), transparent 70%),
              radial-gradient(42rem 22rem at 85% 15%, rgba(184,140,74,.08), transparent 70%);
            animation:drift 18s ease-in-out infinite alternate;
          }
          @keyframes drift{
            from{transform:translateY(-8px)}
            to{transform:translateY(8px)}
          }
          .top{
            position:sticky;
            top:0;
            backdrop-filter:blur(10px);
            background:rgba(243,246,242,.86);
            border-bottom:1px solid rgba(213,223,216,.8);
            z-index:20;
          }
          .topin{
            max-width:1240px;
            margin:0 auto;
            padding:11px 18px;
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap:18px;
          }
          .brand{
            display:flex;
            align-items:center;
            gap:11px;
            font-weight:800;
            letter-spacing:.02em;
          }
          .brand img{
            width:46px;
            height:46px;
            border-radius:999px;
            border:2px solid rgba(29,75,59,.25);
            object-fit:cover;
            box-shadow:0 8px 14px rgba(20,35,29,.12);
          }
          .brand small{
            display:block;
            font-size:11px;
            color:var(--muted);
            font-weight:600;
          }
          .nav{
            display:flex;
            flex-wrap:wrap;
            gap:8px;
            align-items:center;
          }
          .nav a{
            text-decoration:none;
            color:var(--ink);
            font-weight:700;
            font-size:13px;
            padding:8px 12px;
            border-radius:999px;
            transition:all .2s ease;
          }
          .nav a:hover{
            background:#e7efe9;
            color:var(--brand-deep);
          }
          .wrap{
            max-width:1240px;
            margin:0 auto;
            padding:18px 18px 48px;
          }
          .hero{
            display:grid;
            grid-template-columns:1.1fr .9fr;
            gap:14px;
            align-items:stretch;
          }
          .card{
            background:var(--panel);
            border:1px solid var(--line);
            border-radius:18px;
            box-shadow:var(--shadow);
          }
          .hero-copy{
            padding:26px;
            position:relative;
            overflow:hidden;
          }
          .hero-copy:before{
            content:"";
            position:absolute;
            width:280px;
            height:280px;
            border-radius:999px;
            right:-90px;
            top:-90px;
            background:radial-gradient(circle, rgba(47,110,86,.15), rgba(47,110,86,0));
          }
          .eyebrow{
            display:inline-flex;
            align-items:center;
            gap:8px;
            border:1px solid #d8e4db;
            padding:6px 10px;
            border-radius:999px;
            color:var(--brand-deep);
            font-size:12px;
            font-weight:800;
            letter-spacing:.03em;
            text-transform:uppercase;
            background:#f5faf7;
          }
          h1,h2,h3{
            margin:0;
            font-family:"Fraunces","Georgia",serif;
            letter-spacing:.01em;
          }
          h1{
            margin-top:14px;
            font-size:clamp(1.95rem,4.3vw,3rem);
            line-height:1.16;
          }
          .lead{
            margin:13px 0 0;
            color:var(--muted);
            font-size:15px;
            max-width:60ch;
          }
          .hero-actions{
            margin-top:20px;
            display:flex;
            flex-wrap:wrap;
            gap:10px;
          }
          .btn{
            border:1px solid transparent;
            border-radius:12px;
            padding:10px 14px;
            font-weight:800;
            font-size:13px;
            cursor:pointer;
            text-decoration:none;
            transition:transform .18s ease, box-shadow .18s ease, background .18s ease;
            display:inline-flex;
            align-items:center;
            gap:8px;
          }
          .btn:hover{transform:translateY(-1px)}
          .btn.primary{
            color:#fff;
            background:linear-gradient(135deg,var(--brand),var(--brand-deep));
            box-shadow:0 10px 18px rgba(29,75,59,.22);
          }
          .btn.ghost{
            border-color:#d4dfd7;
            color:var(--ink);
            background:#f8fbf9;
          }
          .hero-badges{
            margin-top:18px;
            display:flex;
            flex-wrap:wrap;
            gap:8px;
          }
          .hero-badges span{
            background:#f4f9f6;
            border:1px solid #d7e5dc;
            border-radius:999px;
            padding:5px 10px;
            font-size:12px;
            color:#335648;
            font-weight:700;
          }
          .hero-media{
            position:relative;
            min-height:430px;
            overflow:hidden;
          }
          .gallery-frame{
            position:absolute;
            inset:0;
            overflow:hidden;
          }
          .slides{
            position:absolute;
            inset:0;
          }
          .slides img{
            width:100%;
            height:100%;
            object-fit:cover;
          }
          .slides img{
            position:absolute;
            inset:0;
            opacity:0;
            transform:scale(1.03);
            transition:opacity .9s ease, transform 1.6s ease;
          }
          .slides img.active{
            opacity:1;
            transform:scale(1);
          }
          .gallery-strip{
            position:absolute;
            inset:auto 14px 46px 14px;
            display:flex;
            gap:8px;
            overflow-x:auto;
            padding-bottom:4px;
            scrollbar-width:none;
          }
          .gallery-strip::-webkit-scrollbar{display:none}
          .gallery-thumb{
            flex:0 0 auto;
            width:74px;
            height:50px;
            object-fit:cover;
            border-radius:8px;
            border:2px solid rgba(255,255,255,.45);
            opacity:.75;
            cursor:pointer;
            transition:all .22s ease;
          }
          .gallery-thumb.active{
            opacity:1;
            border-color:#fff;
            transform:translateY(-2px);
            box-shadow:0 8px 14px rgba(0,0,0,.22);
          }
          .gallery-progress{
            position:absolute;
            left:14px;
            right:14px;
            bottom:14px;
            height:5px;
            border-radius:999px;
            overflow:hidden;
            background:rgba(255,255,255,.35);
          }
          .gallery-progress span{
            display:block;
            height:100%;
            width:0%;
            background:linear-gradient(90deg,#f7f1de,#b88c4a,#f0f7f2);
            transition:width .4s ease;
          }
          .hero-counter{
            position:absolute;
            top:12px;
            right:12px;
            background:rgba(255,255,255,.86);
            color:#234235;
            border:1px solid rgba(35,66,53,.15);
            border-radius:999px;
            padding:6px 11px;
            font-size:12px;
            font-weight:800;
            backdrop-filter:blur(3px);
          }
          .hero-prayer{
            margin-top:16px;
            border:1px solid #d6e1da;
            border-radius:14px;
            background:#f9fcfa;
            padding:12px;
          }
          .hero-prayer-head{
            display:flex;
            justify-content:space-between;
            align-items:center;
            gap:8px;
            font-size:13px;
            font-weight:800;
            color:#28473b;
          }
          .hero-prayer-sub{
            margin-top:6px;
            font-size:13px;
            color:#4a6156;
          }
          .prayer-tree{
            margin-top:9px;
            display:grid;
            grid-template-columns:repeat(5,minmax(0,1fr));
            gap:7px;
          }
          .prayer-node{
            border:1px solid #d5e0d9;
            border-radius:10px;
            padding:8px 6px;
            text-align:center;
            background:#fff;
            color:#4f665a;
            font-size:11px;
            font-weight:700;
          }
          .prayer-node.done{
            border-color:#8cc2a3;
            background:#e9f7ef;
            color:#245440;
          }
          .prayer-node.next{
            border-color:#c49d5b;
            background:#fbf5e7;
            color:#6b4d23;
          }
          .insight-strip{
            margin-top:14px;
            display:grid;
            grid-template-columns:repeat(4,minmax(0,1fr));
            gap:12px;
          }
          .metric{
            background:var(--panel-soft);
            border:1px solid var(--line);
            border-radius:14px;
            padding:14px;
          }
          .metric .label{
            color:var(--muted);
            font-size:12px;
            font-weight:700;
            text-transform:uppercase;
            letter-spacing:.05em;
          }
          .metric strong{
            margin-top:8px;
            display:block;
            font-size:29px;
            color:var(--brand-deep);
            font-family:"Fraunces","Georgia",serif;
          }
          .grid{
            margin-top:14px;
            display:grid;
            grid-template-columns:320px 1fr;
            gap:14px;
            align-items:start;
          }
          .rail{
            padding:14px;
            position:sticky;
            top:88px;
          }
          .studio-rail-title{
            font-size:12px;
            color:var(--muted);
            text-transform:uppercase;
            font-weight:800;
            letter-spacing:.06em;
          }
          .mode-list{
            margin-top:10px;
            display:grid;
            gap:8px;
          }
          .mode-card{
            border:1px solid #d7e2db;
            background:#fff;
            padding:11px;
            border-radius:12px;
            text-align:left;
            cursor:pointer;
            transition:border-color .2s ease, transform .2s ease, box-shadow .2s ease;
          }
          .mode-card:hover{
            transform:translateY(-1px);
            border-color:#b8cfbf;
          }
          .mode-card.active{
            border-color:#98c2a8;
            box-shadow:0 8px 16px rgba(33,78,60,.12);
            background:#f4faf6;
          }
          .mode-card b{
            display:block;
            color:var(--ink);
            font-size:13px;
          }
          .mode-card span{
            color:var(--muted);
            font-size:12px;
          }
          .aux-card{
            margin-top:12px;
            border:1px solid #d6e1da;
            border-radius:12px;
            padding:12px;
            background:#fbfdfc;
          }
          .aux-card h4{
            margin:0 0 8px;
            font-size:14px;
            color:var(--brand-deep);
          }
          .aux-card textarea{
            width:100%;
            min-height:96px;
            resize:vertical;
            border:1px solid #ccd9d1;
            border-radius:10px;
            padding:10px;
            font:inherit;
            background:#fff;
          }
          .mini-btn{
            margin-top:8px;
            padding:8px 10px;
            border:0;
            border-radius:10px;
            background:#2f6e56;
            color:#fff;
            font-weight:700;
            font-size:12px;
            cursor:pointer;
          }
          .list{
            margin:8px 0 0;
            padding:0;
            list-style:none;
            display:grid;
            gap:8px;
          }
          .list li{
            border:1px solid #d9e4dd;
            background:#fff;
            border-radius:10px;
            padding:8px 9px;
            font-size:12px;
            color:#405249;
          }
          .list .line-1{
            font-weight:700;
            color:#1f3229;
          }
          .workspace{
            padding:18px;
          }
          .workspace-head{
            display:flex;
            justify-content:space-between;
            gap:10px;
            align-items:flex-end;
          }
          .workspace-head p{
            margin:6px 0 0;
            color:var(--muted);
            font-size:14px;
          }
          .panel{
            display:none;
            margin-top:14px;
            border:1px solid #d7e2db;
            border-radius:14px;
            padding:14px;
            background:#fcfefd;
            animation:fadePanel .3s ease;
          }
          .panel.active{display:block}
          @keyframes fadePanel{
            from{opacity:0; transform:translateY(8px)}
            to{opacity:1; transform:translateY(0)}
          }
          .panel h3{
            font-size:24px;
            margin:0 0 5px;
          }
          .panel p{
            margin:0;
            color:var(--muted);
            font-size:14px;
          }
          .controls{
            margin-top:12px;
            display:grid;
            grid-template-columns:repeat(12,minmax(0,1fr));
            gap:9px;
          }
          .field{
            grid-column:span 6;
          }
          .field.full{grid-column:span 12}
          .field.third{grid-column:span 4}
          .field label{
            display:block;
            margin-bottom:5px;
            font-size:12px;
            color:var(--muted);
            font-weight:700;
            text-transform:uppercase;
            letter-spacing:.04em;
          }
          .field input,.field select{
            width:100%;
            padding:10px 11px;
            border-radius:10px;
            border:1px solid #cfdad2;
            background:#fff;
            color:var(--ink);
            font:inherit;
          }
          .field input:focus,.field select:focus,.aux-card textarea:focus{
            outline:none;
            border-color:#8ebaa0;
            box-shadow:0 0 0 3px rgba(142,186,160,.18);
          }
          .action-row{
            margin-top:10px;
            display:flex;
            flex-wrap:wrap;
            gap:8px;
          }
          .studio-btn{
            padding:9px 12px;
            border-radius:10px;
            border:1px solid transparent;
            font-weight:700;
            font-size:13px;
            cursor:pointer;
            transition:all .2s ease;
          }
          .studio-btn.primary{
            background:linear-gradient(135deg,var(--brand),var(--brand-deep));
            color:#fff;
            box-shadow:0 8px 14px rgba(29,75,59,.2);
          }
          .studio-btn.subtle{
            background:#f3f8f5;
            border-color:#cfddd5;
            color:#2e4a3d;
          }
          .studio-btn:hover{transform:translateY(-1px)}
          .lookup-toggle{
            margin-top:12px;
            display:inline-flex;
            background:#eef4f0;
            border:1px solid #d0ddd5;
            border-radius:999px;
            padding:4px;
            gap:4px;
          }
          .lookup-toggle button{
            border:0;
            border-radius:999px;
            padding:7px 11px;
            font-size:12px;
            font-weight:700;
            cursor:pointer;
            background:transparent;
            color:#335346;
          }
          .lookup-toggle button.active{
            background:#2f6e56;
            color:#fff;
          }
          .lookup-pane{display:none}
          .lookup-pane.active{display:block}
          .search-results{
            margin-top:9px;
            display:grid;
            gap:7px;
          }
          .search-item{
            border:1px solid #d3dfd7;
            border-radius:10px;
            background:#fff;
            padding:9px;
          }
          .search-item b{
            font-size:13px;
            color:#28483b;
          }
          .search-item p{
            margin:5px 0 0;
            color:#4f6359;
            font-size:13px;
          }
          .search-item button{
            margin-top:6px;
            border:0;
            background:#1d4b3b;
            color:#fff;
            border-radius:8px;
            padding:6px 9px;
            font-size:11px;
            font-weight:700;
            cursor:pointer;
          }
          .studio-output{
            margin-top:12px;
            border:1px solid #d7e3db;
            border-radius:12px;
            background:#fff;
            min-height:220px;
            overflow:hidden;
          }
          .out-head{
            display:flex;
            justify-content:space-between;
            align-items:center;
            gap:8px;
            padding:10px 12px;
            border-bottom:1px solid #e4ece7;
            background:#f8fcf9;
          }
          .out-head h4{
            margin:0;
            font-size:14px;
            color:#244538;
          }
          .copy-btn{
            border:1px solid #ccdad2;
            background:#fff;
            padding:6px 9px;
            border-radius:8px;
            font-size:11px;
            font-weight:700;
            cursor:pointer;
          }
          .download-card-btn{
            border:1px solid #cad8d1;
            background:#f4faf7;
            color:#285142;
            padding:8px 10px;
            border-radius:9px;
            font-size:12px;
            font-weight:800;
            cursor:pointer;
            transition:all .2s ease;
          }
          .download-card-btn:hover{
            transform:translateY(-1px);
            border-color:#98c2a8;
            background:#e9f6ee;
          }
          .out-body{
            padding:12px;
            color:#2d4238;
            display:grid;
            gap:10px;
          }
          .out-muted{color:#6a7c72;font-size:13px}
          .out-ar{
            font-family:"Noto Naskh Arabic","Amiri",serif;
            font-size:24px;
            line-height:1.95;
            direction:rtl;
            text-align:right;
          }
          .out-en{
            font-size:15px;
            line-height:1.75;
          }
          .chips{
            display:flex;
            flex-wrap:wrap;
            gap:7px;
          }
          .chips span{
            border:1px solid #d4e1d8;
            background:#f5faf7;
            border-radius:999px;
            padding:4px 9px;
            font-size:11px;
            color:#3c5b4f;
            font-weight:700;
          }
          .coverage{
            margin-top:14px;
            padding:18px;
          }
          table{
            width:100%;
            border-collapse:collapse;
            font-size:14px;
            margin-top:10px;
          }
          th,td{
            border:1px solid #d6e1da;
            padding:9px;
            text-align:left;
            vertical-align:top;
          }
          th{
            background:#f0f7f3;
            color:#26463a;
            font-family:"Fraunces","Georgia",serif;
            font-weight:600;
          }
          .link-grid{
            margin-top:14px;
            display:grid;
            grid-template-columns:repeat(3,minmax(0,1fr));
            gap:12px;
          }
          .link-card{
            padding:14px;
            border:1px solid #d8e2db;
            border-radius:12px;
            background:#fff;
            text-decoration:none;
            color:inherit;
            transition:transform .2s ease, box-shadow .2s ease, border-color .2s ease;
          }
          .link-card:hover{
            transform:translateY(-2px);
            border-color:#acc7b6;
            box-shadow:0 12px 22px rgba(24,57,45,.1);
          }
          .link-card b{
            color:#1f3f33;
          }
          .link-card p{
            margin:6px 0 0;
            color:#60756a;
            font-size:13px;
          }
          .footer{
            margin-top:14px;
            padding:14px;
            border:1px solid #d6e1da;
            border-radius:12px;
            background:#f9fcfa;
            color:#536a5f;
            font-size:13px;
          }
          .site-footer{
            margin-top:18px;
            border:1px solid #d2e0d7;
            border-radius:16px;
            background:#f7fbf8;
            box-shadow:var(--shadow);
            overflow:hidden;
          }
          .site-footer-main{
            padding:18px;
            display:grid;
            grid-template-columns:1.2fr 1fr 1fr;
            gap:14px;
          }
          .site-footer-brand{
            display:flex;
            gap:10px;
            align-items:flex-start;
          }
          .site-footer-brand img{
            width:50px;
            height:50px;
            border-radius:999px;
            object-fit:cover;
            border:2px solid rgba(47,110,86,.22);
          }
          .site-footer-brand strong{
            display:block;
            color:#1d4435;
            font-size:14px;
            line-height:1.4;
          }
          .site-footer-brand p{
            margin:4px 0 0;
            color:#5f7469;
            font-size:12px;
          }
          .site-footer h4{
            margin:0 0 8px;
            font-size:13px;
            color:#28493d;
            text-transform:uppercase;
            letter-spacing:.05em;
          }
          .site-footer-links{
            display:grid;
            gap:7px;
          }
          .site-footer-links a{
            text-decoration:none;
            color:#38584a;
            font-size:13px;
            font-weight:700;
          }
          .site-footer-links a:hover{color:#1d4b3b}
          .site-footer-copy{
            border-top:1px solid #d7e3db;
            padding:11px 18px;
            display:flex;
            justify-content:space-between;
            gap:10px;
            flex-wrap:wrap;
            color:#5d7468;
            font-size:12px;
            background:#f3f9f5;
          }
          .reveal{
            opacity:0;
            transform:translateY(18px);
          }
          .reveal.show{
            opacity:1;
            transform:translateY(0);
            transition:all .65s ease;
          }
          @media (max-width:1100px){
            .hero{grid-template-columns:1fr}
            .insight-strip{grid-template-columns:repeat(2,minmax(0,1fr))}
            .grid{grid-template-columns:1fr}
            .rail{position:relative;top:0}
            .link-grid{grid-template-columns:1fr}
          }
          @media (max-width:780px){
            .topin{padding:10px 12px}
            .brand span{font-size:12px}
            .wrap{padding:14px 12px 40px}
            .hero-copy{padding:18px}
            .controls{grid-template-columns:repeat(6,minmax(0,1fr))}
            .field{grid-column:span 6}
            .field.third{grid-column:span 2}
            .metric strong{font-size:24px}
            .hero-media{min-height:300px}
            .gallery-strip{inset:auto 10px 42px 10px}
            .gallery-thumb{width:64px;height:44px}
            .prayer-tree{grid-template-columns:repeat(3,minmax(0,1fr))}
            .site-footer-main{grid-template-columns:1fr 1fr}
          }
          @media (max-width:580px){
            .insight-strip{grid-template-columns:1fr}
            .field.third{grid-column:span 6}
            .nav a{padding:7px 9px;font-size:12px}
            .hero-media{min-height:270px}
            .prayer-tree{grid-template-columns:repeat(2,minmax(0,1fr))}
            .site-footer-main{grid-template-columns:1fr}
          }
        </style>
      </head>
      <body>
        <div class="ambient"></div>
        <header class="top">
          <div class="topin">
            <div class="brand">
              <img src="/static/attibyan-logo.png" onerror="this.style.display='none'" alt="At-Tibyan Logo">
              <div>
                <span>AT-TIBYAN CENTRE FOR SUNNAH AND ISLAMIC SCIENCES</span>
                <small>Premium Islamic Learning Studio and Knowledge Platform</small>
              </div>
            </div>
            <nav class="nav">
              <a href="#studio">Learning Studio</a>
              <a href="#coverage">Coverage</a>
              <a href="/docs">API Docs</a>
              <a href="/developers">Developers</a>
            </nav>
          </div>
        </header>

        <div class="wrap">
          <section class="hero reveal">
            <article class="card hero-copy">
              <span class="eyebrow">Calm, Reliable, Research-Grade</span>
              <h1>A modern and intelligent Islamic Learning Studio built for deep study, teaching, and reflection.</h1>
              <p class="lead">This platform is entirely designed around learning flow: discover trusted references, compare sources fast, keep structured notes, and build consistent study momentum with a focused premium interface.</p>
              <div class="hero-actions">
                <a class="btn primary" href="#studio">Open Learning Studio</a>
                <a class="btn ghost" href="/docs">Explore API Reference</a>
              </div>
              <div class="hero-badges">
                <span>Qur'an 6,236 Ayahs</span>
                <span>Hadith 10 Collections</span>
                <span>Umm al-Qura Hijri Range</span>
                <span>Prayer Snapshot Intelligence</span>
                <span>Arabic + English</span>
              </div>
              <section class="hero-prayer">
                <div class="hero-prayer-head">
                  <span>Damaturu Daily Prayer Progress</span>
                  <span id="damClock">--:--:--</span>
                </div>
                <div class="hero-prayer-sub" id="damNext">Loading Damaturu prayer countdown...</div>
                <div class="prayer-tree" id="damTree"></div>
              </section>
            </article>
            <article class="card hero-media">
              <div class="gallery-frame">
                <div class="slides" id="heroSlides"></div>
              </div>
              <span class="hero-counter" id="heroSlideIndex">1 / 1</span>
              <div class="gallery-strip" id="heroThumbs"></div>
              <div class="gallery-progress"><span id="heroProgress"></span></div>
            </article>
          </section>

          <section class="insight-strip reveal">
            <article class="metric"><div class="label">Qur'an Ayahs</div><strong data-counter="quran_ayahs">6,236</strong></article>
            <article class="metric"><div class="label">Hadith Entries</div><strong data-counter="hadith_entries">36,512</strong></article>
            <article class="metric"><div class="label">Hijri Mapping Rows</div><strong data-counter="hijri_dates">55,991</strong></article>
            <article class="metric"><div class="label">Prayer Locations</div><strong data-counter="prayer_times">836</strong></article>
          </section>

          <section class="grid reveal" id="studio">
            <aside class="card rail">
              <div class="studio-rail-title">Learning Studio Modules</div>
              <div class="mode-list">
                <button class="mode-card active" data-panel="quran">
                  <b>Qur'an Studio</b>
                  <span>Dual lookup, keyword exploration, random reflection.</span>
                </button>
                <button class="mode-card" data-panel="hadith">
                  <b>Hadith Studio</b>
                  <span>Collection navigation and searchable hadith retrieval.</span>
                </button>
                <button class="mode-card" data-panel="hijri">
                  <b>Date Conversion Lab</b>
                  <span>Two-way Gregorian/Hijri references with today sync.</span>
                </button>
                <button class="mode-card" data-panel="prayer">
                  <b>Prayer Planner</b>
                  <span>Snapshot schedules, city finder, next prayer insight.</span>
                </button>
              </div>

              <div class="aux-card">
                <h4>Study Notebook</h4>
                <textarea id="noteInput" placeholder="Capture reflections, memorization goals, or class points..."></textarea>
                <button class="mini-btn" id="saveNoteBtn">Save Note</button>
                <ul class="list" id="notesList">
                  <li>No notes yet.</li>
                </ul>
              </div>

              <div class="aux-card">
                <h4>Recent Activity</h4>
                <ul class="list" id="recentList">
                  <li>No lookups yet.</li>
                </ul>
              </div>
            </aside>

            <section class="card workspace">
              <div class="workspace-head">
                <div>
                  <h2>Interactive Learning Studio</h2>
                  <p>Built for premium study flow: quick lookup, context-rich reading, and structured progress in one calm workspace.</p>
                </div>
                <span class="eyebrow" id="todayBadge">Today: --</span>
              </div>

              <article class="panel active" id="panel-quran">
                <h3>Qur'an Studio</h3>
                <p>Two-way Surah lookup, exact ayah retrieval, and targeted keyword exploration.</p>

                <div class="lookup-toggle">
                  <button type="button" class="active" data-quran-mode="name">Lookup by Surah Name</button>
                  <button type="button" data-quran-mode="number">Lookup by Surah Number</button>
                </div>

                <div id="lookupByName" class="lookup-pane active">
                  <div class="controls">
                    <div class="field">
                      <label>Surah Name</label>
                      <select id="surahNameSelect"></select>
                    </div>
                    <div class="field">
                      <label>Ayah</label>
                      <input id="surahNameAyah" type="number" min="1" value="1">
                    </div>
                  </div>
                  <div class="action-row">
                    <button class="studio-btn primary" id="loadByNameBtn">Load Ayah</button>
                    <button class="studio-btn subtle" id="randomAyahBtn">Random Ayah</button>
                  </div>
                </div>

                <div id="lookupByNumber" class="lookup-pane">
                  <div class="controls">
                    <div class="field">
                      <label>Surah Number</label>
                      <input id="surahNumberInput" type="number" min="1" max="114" value="1">
                    </div>
                    <div class="field">
                      <label>Ayah</label>
                      <input id="surahNumberAyah" type="number" min="1" value="1">
                    </div>
                  </div>
                  <div class="action-row">
                    <button class="studio-btn primary" id="loadByNumberBtn">Load Ayah</button>
                  </div>
                </div>

                <div class="controls">
                  <div class="field">
                    <label>Keyword Search in Qur'an</label>
                    <input id="quranKeyword" placeholder="e.g. mercy, patience, prayer">
                  </div>
                  <div class="field">
                    <label>Optional Surah Filter</label>
                    <input id="quranKeywordSurah" type="number" min="1" max="114" placeholder="Leave blank for all Surahs">
                  </div>
                </div>
                <div class="action-row">
                  <button class="studio-btn subtle" id="searchQuranBtn">Search Qur'an Keywords</button>
                </div>
                <div class="search-results" id="quranSearchResults"></div>

                <article class="studio-output" id="quranOutput"></article>
              </article>

              <article class="panel" id="panel-hadith">
                <h3>Hadith Studio</h3>
                <p>Navigate canonical collections and discover references by number or keyword.</p>
                <div class="controls">
                  <div class="field">
                    <label>Collection</label>
                    <select id="hadithCollectionSelect"></select>
                  </div>
                  <div class="field">
                    <label>Hadith Number</label>
                    <input id="hadithNumberInput" type="number" min="1" value="15">
                  </div>
                </div>
                <div class="action-row">
                  <button class="studio-btn primary" id="loadHadithBtn">Load Hadith</button>
                </div>

                <div class="controls">
                  <div class="field">
                    <label>Search Hadith Keywords</label>
                    <input id="hadithKeyword" placeholder="e.g. prayer, intention, fasting">
                  </div>
                  <div class="field">
                    <label>Collection Filter</label>
                    <select id="hadithSearchCollection">
                      <option value="">All collections</option>
                    </select>
                  </div>
                </div>
                <div class="action-row">
                  <button class="studio-btn subtle" id="searchHadithBtn">Search Hadith</button>
                </div>
                <div class="search-results" id="hadithSearchResults"></div>

                <article class="studio-output" id="hadithOutput"></article>
              </article>

              <article class="panel" id="panel-hijri">
                <h3>Date Conversion Lab</h3>
                <p>Convert Gregorian and Hijri dates instantly, with quick access to today's mapping.</p>
                <div class="controls">
                  <div class="field full">
                    <label>Gregorian Date</label>
                    <input id="gregorianInput" type="date">
                  </div>
                </div>
                <div class="action-row">
                  <button class="studio-btn primary" id="gregToHijriBtn">Gregorian -> Hijri</button>
                  <button class="studio-btn subtle" id="loadTodayHijriBtn">Use Today</button>
                </div>
                <div class="controls">
                  <div class="field third">
                    <label>Hijri Year</label>
                    <input id="hijriYearInput" type="number" min="1300" value="1447">
                  </div>
                  <div class="field third">
                    <label>Hijri Month</label>
                    <input id="hijriMonthInput" type="number" min="1" max="12" value="11">
                  </div>
                  <div class="field third">
                    <label>Hijri Day</label>
                    <input id="hijriDayInput" type="number" min="1" max="30" value="12">
                  </div>
                </div>
                <div class="action-row">
                  <button class="studio-btn subtle" id="hijriToGregBtn">Hijri -> Gregorian</button>
                </div>
                <article class="studio-output" id="hijriOutput"></article>
              </article>

              <article class="panel" id="panel-prayer">
                <h3>Prayer Planner</h3>
                <p>Get prayer schedules by location, optional date targeting, and quick city discovery.</p>
                <div class="controls">
                  <div class="field">
                    <label>Country</label>
                    <input id="prayerCountryInput" value="Nigeria">
                  </div>
                  <div class="field">
                    <label>City</label>
                    <input id="prayerCityInput" value="Lagos Island">
                  </div>
                  <div class="field full">
                    <label>Optional Date (Gregorian)</label>
                    <input id="prayerDateInput" type="date">
                  </div>
                </div>
                <div class="action-row">
                  <button class="studio-btn primary" id="loadPrayerBtn">Load Prayer Schedule</button>
                </div>

                <div class="controls">
                  <div class="field">
                    <label>City Finder Keyword</label>
                    <input id="citySearchQuery" placeholder="e.g. Lagos, Abuja, London">
                  </div>
                  <div class="field">
                    <label>Country Filter (Optional)</label>
                    <input id="citySearchCountry" placeholder="e.g. Nigeria">
                  </div>
                </div>
                <div class="action-row">
                  <button class="studio-btn subtle" id="searchCityBtn">Find Matching Cities</button>
                </div>
                <div class="search-results" id="citySearchResults"></div>

                <article class="studio-output" id="prayerOutput"></article>
              </article>
            </section>
          </section>

          <section class="card coverage reveal" id="coverage">
            <h2>Platform Coverage Snapshot</h2>
            <table>
              <tr><th>Dataset</th><th>Coverage</th><th>Rows</th><th>Source</th></tr>
              <tr><td>Qur'an</td><td>114 Surahs, 6,236 Ayahs</td><td>6,236</td><td>AlQuran Cloud editions</td></tr>
              <tr><td>Hadith</td><td>10 merged Arabic + English collections</td><td>36,512</td><td>Hadith API open corpus</td></tr>
              <tr><td>Hijri</td><td>1343-01-01 AH to 1500-12-30 AH</td><td>55,991</td><td>Umm al-Qura table</td></tr>
              <tr><td>Prayer</td><td>All Nigeria entries + selected global cities</td><td>836</td><td>AlAdhan snapshots</td></tr>
            </table>
          </section>

          <section class="link-grid reveal">
            <a class="link-card" href="/docs">
              <b>Interactive API Documentation</b>
              <p>Full endpoint explorer with request/response schemas.</p>
            </a>
            <a class="link-card" href="/developers">
              <b>Developer Quickstart</b>
              <p>Setup instructions for local development and integration.</p>
            </a>
            <a class="link-card" href="/v1/meta">
              <b>Live Dataset Metadata</b>
              <p>Versioned counts and metadata from the active database.</p>
            </a>
          </section>

          <footer class="site-footer reveal">
            <div class="site-footer-main">
              <div class="site-footer-brand">
                <img src="/static/attibyan-logo.png" alt="At-Tibyan Logo">
                <div>
                  <strong>AT-TIBYAN CENTRE FOR SUNNAH AND ISLAMIC SCIENCES</strong>
                  <p>Purpose-built for reliable Islamic learning, calm study flow, and trustworthy digital references across Qur'an, Hadith, Hijri, and Prayer data.</p>
                </div>
              </div>
              <div>
                <h4>Navigate</h4>
                <nav class="site-footer-links">
                  <a href="#studio">Learning Studio</a>
                  <a href="#coverage">Coverage Snapshot</a>
                  <a href="/docs">API Documentation</a>
                  <a href="/developers">Developers Guide</a>
                </nav>
              </div>
              <div>
                <h4>Study Tabs</h4>
                <nav class="site-footer-links">
                  <a href="#studio" onclick="activatePanel('quran')">Qur'an Studio</a>
                  <a href="#studio" onclick="activatePanel('hadith')">Hadith Studio</a>
                  <a href="#studio" onclick="activatePanel('hijri')">Date Conversion Lab</a>
                  <a href="#studio" onclick="activatePanel('prayer')">Prayer Planner</a>
                </nav>
              </div>
            </div>
            <div class="site-footer-copy">
              <span id="copyrightText">Copyright © At-Tibyan Centre. All rights reserved.</span>
              <span>Official site: <strong>attibyancenter.com</strong></span>
            </div>
          </footer>
        </div>

        <script>
          const API_BASE = "/v1";
          const galleryImages = __GALLERY_IMAGES__;
          const STORE_KEYS = {
            recent: "attibyan_recent_v3",
            notes: "attibyan_notes_v3"
          };
          const state = {
            surahs: [],
            surahMap: new Map(),
            collections: [],
            recent: [],
            notes: [],
            latestExport: { quran: null, hadith: null },
            logoImage: null,
            damaturu: { schedule: null, timer: null }
          };

          function loadStore(key, fallback) {
            try {
              const raw = localStorage.getItem(key);
              if (!raw) return fallback;
              const parsed = JSON.parse(raw);
              return Array.isArray(parsed) ? parsed : fallback;
            } catch {
              return fallback;
            }
          }

          function saveStore(key, value) {
            try {
              localStorage.setItem(key, JSON.stringify(value));
            } catch {}
          }

          function escapeHtml(value) {
            return String(value ?? "")
              .replaceAll("&", "&amp;")
              .replaceAll("<", "&lt;")
              .replaceAll(">", "&gt;");
          }

          function toSafeFilename(value) {
            return String(value || "study-card")
              .toLowerCase()
              .replace(/[^a-z0-9]+/g, "-")
              .replace(/^-+|-+$/g, "")
              .slice(0, 64) || "study-card";
          }

          function wrapCanvasText(ctx, text, maxWidth) {
            const words = String(text || "").split(/\\s+/).filter(Boolean);
            if (!words.length) return [];
            const lines = [];
            let line = words[0];
            for (let i = 1; i < words.length; i += 1) {
              const test = `${line} ${words[i]}`;
              if (ctx.measureText(test).width <= maxWidth) {
                line = test;
              } else {
                lines.push(line);
                line = words[i];
              }
            }
            lines.push(line);
            return lines;
          }

          async function getLogoImage() {
            if (state.logoImage) return state.logoImage;
            const logo = await new Promise((resolve) => {
              const img = new Image();
              img.onload = () => resolve(img);
              img.onerror = () => resolve(null);
              img.src = "/static/attibyan-logo.png";
            });
            state.logoImage = logo;
            return logo;
          }

          async function downloadStudyCard(kind) {
            const data = state.latestExport[kind];
            if (!data) return;

            const canvas = document.createElement("canvas");
            canvas.width = 1080;
            canvas.height = 1080;
            const ctx = canvas.getContext("2d");
            if (!ctx) return;

            const W = 1080;
            const H = 1080;
            const gradient = ctx.createLinearGradient(0, 0, canvas.width, canvas.height);
            gradient.addColorStop(0, "#edf3ef");
            gradient.addColorStop(1, "#e7eee9");
            ctx.fillStyle = gradient;
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            ctx.strokeStyle = "rgba(47,110,86,.22)";
            ctx.lineWidth = 3;
            ctx.strokeRect(30, 30, W - 60, H - 60);

            const logo = await getLogoImage();
            if (logo) {
              const size = 72;
              ctx.save();
              ctx.beginPath();
              ctx.arc(72 + (size / 2), 72 + (size / 2), size / 2, 0, Math.PI * 2);
              ctx.closePath();
              ctx.clip();
              ctx.drawImage(logo, 72, 72, size, size);
              ctx.restore();
            }

            const nowStamp = new Date().toLocaleString();
            ctx.fillStyle = "#1f4a3a";
            ctx.font = "700 20px Fraunces, Georgia, serif";
            ctx.fillText("AT-TIBYAN CENTRE FOR SUNNAH AND ISLAMIC SCIENCES", 166, 98);
            ctx.fillStyle = "#4d655a";
            ctx.font = "600 15px Manrope, sans-serif";
            ctx.fillText(data.subtitle || "Islamic Knowledge Study Card", 166, 132);

            ctx.fillStyle = "#36554a";
            ctx.font = "700 13px Manrope, sans-serif";
            ctx.fillText(nowStamp, W - 290, 98);
            ctx.fillText("attibyancenter.com", W - 290, 128);

            ctx.fillStyle = "#2f6e56";
            ctx.font = "700 20px Fraunces, Georgia, serif";
            ctx.fillText(data.title || "Study Reflection", 72, 194);

            const textWidth = W - 144;
            let cursorY = 270;

            if (data.arabic) {
              ctx.fillStyle = "#203d31";
              ctx.font = "600 50px 'Noto Naskh Arabic', serif";
              ctx.textAlign = "right";
              ctx.direction = "rtl";
              const arabicLines = wrapCanvasText(ctx, data.arabic, textWidth);
              arabicLines.slice(0, 4).forEach((line) => {
                ctx.fillText(line, W - 72, cursorY);
                cursorY += 66;
              });
              ctx.direction = "ltr";
              ctx.textAlign = "left";
              cursorY += 24;
            }

            ctx.fillStyle = "#264538";
            ctx.font = "500 22px Manrope, sans-serif";
            const enLines = wrapCanvasText(ctx, data.english || "", textWidth);
            enLines.slice(0, 8).forEach((line) => {
              ctx.fillText(line, 72, cursorY);
              cursorY += 38;
            });

            ctx.fillStyle = "#3d5b4f";
            ctx.font = "600 15px Manrope, sans-serif";
            if (data.meta) {
              ctx.fillText(data.meta, 72, H - 170);
            }

            ctx.fillStyle = "#1f4a3a";
            ctx.font = "700 19px Manrope, sans-serif";
            ctx.fillText("Get yours at attibyancenter.com", 72, H - 124);

            ctx.fillStyle = "#5a6f64";
            ctx.font = "500 14px Manrope, sans-serif";
            ctx.fillText(`Generated ${nowStamp}`, 72, H - 90);
            ctx.fillText("Copyright © At-Tibyan Centre. All rights reserved.", 72, H - 58);

            const link = document.createElement("a");
            link.download = `${toSafeFilename(kind)}-${Date.now()}.png`;
            link.href = canvas.toDataURL("image/png");
            document.body.appendChild(link);
            link.click();
            link.remove();
          }

          function showOutput(targetId, title, bodyHtml) {
            const el = document.getElementById(targetId);
            el.innerHTML = `
              <div class="out-head">
                <h4>${escapeHtml(title)}</h4>
                <button class="copy-btn" type="button">Copy</button>
              </div>
              <div class="out-body">${bodyHtml}</div>
            `;
            const copyBtn = el.querySelector(".copy-btn");
            copyBtn.onclick = async () => {
              try {
                await navigator.clipboard.writeText(el.innerText.trim());
                copyBtn.textContent = "Copied";
                setTimeout(() => copyBtn.textContent = "Copy", 1000);
              } catch {}
            };
          }

          function loadingOutput(targetId, title) {
            showOutput(targetId, title, "<div class='out-muted'>Loading...</div>");
          }

          function addRecent(type, detail) {
            const stamp = new Date().toLocaleString();
            state.recent.unshift({ type, detail, stamp });
            state.recent = state.recent.slice(0, 12);
            saveStore(STORE_KEYS.recent, state.recent);
            renderRecent();
          }

          function renderRecent() {
            const host = document.getElementById("recentList");
            if (!state.recent.length) {
              host.innerHTML = "<li>No lookups yet.</li>";
              return;
            }
            host.innerHTML = state.recent
              .map((item) => `
                <li>
                  <div class="line-1">${escapeHtml(item.type)}: ${escapeHtml(item.detail)}</div>
                  <div>${escapeHtml(item.stamp)}</div>
                </li>
              `).join("");
          }

          function renderNotes() {
            const host = document.getElementById("notesList");
            if (!state.notes.length) {
              host.innerHTML = "<li>No notes yet.</li>";
              return;
            }
            host.innerHTML = state.notes.map((note, idx) => `
              <li>
                <div class="line-1">${escapeHtml(note.text)}</div>
                <div>${escapeHtml(note.stamp)}</div>
                <button class="mini-btn" style="margin-top:6px;padding:6px 8px;font-size:11px;background:#6d7f75" data-note-del="${idx}">Delete</button>
              </li>
            `).join("");
            host.querySelectorAll("[data-note-del]").forEach((btn) => {
              btn.onclick = () => {
                const i = Number(btn.getAttribute("data-note-del"));
                state.notes.splice(i, 1);
                saveStore(STORE_KEYS.notes, state.notes);
                renderNotes();
              };
            });
          }

          function activatePanel(panel) {
            document.querySelectorAll(".mode-card").forEach((el) => {
              el.classList.toggle("active", el.getAttribute("data-panel") === panel);
            });
            document.querySelectorAll(".panel").forEach((el) => {
              el.classList.toggle("active", el.id === `panel-${panel}`);
            });
          }

          function setQuranMode(mode) {
            document.querySelectorAll("[data-quran-mode]").forEach((btn) => {
              btn.classList.toggle("active", btn.getAttribute("data-quran-mode") === mode);
            });
            document.getElementById("lookupByName").classList.toggle("active", mode === "name");
            document.getElementById("lookupByNumber").classList.toggle("active", mode === "number");
          }

          function formatNum(value) {
            return Number(value || 0).toLocaleString();
          }

          function animateCounter(el, target) {
            const limit = Number(target || 0);
            if (!Number.isFinite(limit)) return;
            const frames = 24;
            let tick = 0;
            const step = limit / frames;
            const timer = setInterval(() => {
              tick += 1;
              const val = Math.round(Math.min(limit, step * tick));
              el.textContent = formatNum(val);
              if (tick >= frames) clearInterval(timer);
            }, 22);
          }

          async function loadMetaCounters() {
            try {
              const res = await fetch(`${API_BASE}/meta?lang=en`);
              const data = await res.json();
              const counts = data.counts || {};
              document.querySelectorAll("[data-counter]").forEach((el) => {
                const key = el.getAttribute("data-counter");
                animateCounter(el, counts[key]);
              });
            } catch {}
          }

          async function loadTodayBadge() {
            const now = new Date();
            const iso = now.toISOString().slice(0, 10);
            let text = `Today: ${iso}`;
            try {
              const res = await fetch(`${API_BASE}/hijri/from-gregorian?date=${iso}&lang=en`);
              const data = await res.json();
              if (data.found && data.hijri_iso) {
                text = `Today: ${iso} | ${data.hijri_iso} AH`;
              }
            } catch {}
            document.getElementById("todayBadge").textContent = text;
          }

          async function loadSurahCatalog() {
            const select = document.getElementById("surahNameSelect");
            select.innerHTML = "";
            try {
              const res = await fetch(`${API_BASE}/quran/surahs?lang=en`);
              const data = await res.json();
              const surahs = Array.isArray(data.surahs) ? data.surahs : [];
              state.surahs = surahs;
              state.surahMap = new Map(surahs.map((s) => [Number(s.surah_number), s]));
              surahs.forEach((s) => {
                const opt = document.createElement("option");
                opt.value = String(s.surah_number);
                opt.textContent = `${s.surah_number}. ${s.name_english} (${s.name_arabic})`;
                select.appendChild(opt);
              });
              if (!surahs.length) {
                const opt = document.createElement("option");
                opt.textContent = "No surah catalog available";
                select.appendChild(opt);
              }
            } catch {
              for (let i = 1; i <= 114; i += 1) {
                const opt = document.createElement("option");
                opt.value = String(i);
                opt.textContent = `Surah ${i}`;
                select.appendChild(opt);
              }
            }
          }

          async function loadHadithCollections() {
            const refSelect = document.getElementById("hadithCollectionSelect");
            const searchSelect = document.getElementById("hadithSearchCollection");
            refSelect.innerHTML = "";
            searchSelect.innerHTML = "<option value=''>All collections</option>";
            try {
              const res = await fetch(`${API_BASE}/hadith/collections?lang=en`);
              const data = await res.json();
              const collections = Array.isArray(data.collections) ? data.collections : [];
              state.collections = collections;
              collections.forEach((c) => {
                const key = c.collection_key;
                const name = c.collection_name;
                const refOpt = document.createElement("option");
                refOpt.value = key;
                refOpt.textContent = `${name} (${key})`;
                refSelect.appendChild(refOpt);
                const searchOpt = document.createElement("option");
                searchOpt.value = key;
                searchOpt.textContent = `${name} (${key})`;
                searchSelect.appendChild(searchOpt);
              });
              if (!collections.length) throw new Error("empty");
            } catch {
              const fallback = ["abudawud","bukhari","dehlawi","ibnmajah","malik","muslim","nasai","nawawi","qudsi","tirmidhi"];
              fallback.forEach((key) => {
                const refOpt = document.createElement("option");
                refOpt.value = key;
                refOpt.textContent = key;
                refSelect.appendChild(refOpt);
                const searchOpt = document.createElement("option");
                searchOpt.value = key;
                searchOpt.textContent = key;
                searchSelect.appendChild(searchOpt);
              });
            }
          }

          function selectedSurahByName() {
            const surah = Number(document.getElementById("surahNameSelect").value);
            const ayah = Number(document.getElementById("surahNameAyah").value || 1);
            return { surah, ayah };
          }

          function selectedSurahByNumber() {
            const surah = Number(document.getElementById("surahNumberInput").value || 1);
            const ayah = Number(document.getElementById("surahNumberAyah").value || 1);
            return { surah, ayah };
          }

          function validateSurahAyah(surah, ayah) {
            if (!Number.isInteger(surah) || surah < 1 || surah > 114) {
              return "Surah number must be between 1 and 114.";
            }
            if (!Number.isInteger(ayah) || ayah < 1) {
              return "Ayah must be a positive integer.";
            }
            const surahInfo = state.surahMap.get(surah);
            if (surahInfo && Number.isInteger(Number(surahInfo.ayah_count)) && ayah > Number(surahInfo.ayah_count)) {
              return `Surah ${surah} has ${surahInfo.ayah_count} ayahs.`;
            }
            return "";
          }

          async function loadQuranAyah(surah, ayah, sourceLabel) {
            const problem = validateSurahAyah(surah, ayah);
            if (problem) {
              showOutput("quranOutput", "Qur'an Result", `<div class='out-muted'>${escapeHtml(problem)}</div>`);
              return;
            }
            loadingOutput("quranOutput", "Qur'an Result");
            try {
              const res = await fetch(`${API_BASE}/quran/ayah/${surah}/${ayah}?lang=en`);
              const data = await res.json();
              if (!data.found || !data.data) {
                showOutput("quranOutput", "Qur'an Result", "<div class='out-muted'>No ayah found for this reference.</div>");
                return;
              }
              const d = data.data;
              const surahInfo = state.surahMap.get(Number(d.surah_number));
              state.latestExport.quran = {
                title: `Surah ${d.surah_number} - Ayah ${d.ayah_number_in_surah}`,
                subtitle: "Qur'an Reflection Card",
                arabic: d.text_arabic_uthmani || "",
                english: d.text_english_sahih || "",
                meta: `Juz ${d.juz || "-"} | Page ${d.page || "-"} | ${surahInfo ? surahInfo.name_english : "Qur'an"}`
              };
              showOutput("quranOutput", `Surah ${d.surah_number} · Ayah ${d.ayah_number_in_surah}`, `
                <div class="chips">
                  <span>${escapeHtml(sourceLabel)}</span>
                  <span>Juz ${escapeHtml(d.juz)}</span>
                  <span>Page ${escapeHtml(d.page)}</span>
                  <span>${escapeHtml((surahInfo && surahInfo.revelation_type) || "Reference")}</span>
                </div>
                <div class="out-ar">${escapeHtml(d.text_arabic_uthmani || "")}</div>
                <div class="out-en">${escapeHtml(d.text_english_sahih || "")}</div>
                <div><button type="button" class="download-card-btn" onclick="downloadStudyCard('quran')">Download Image</button></div>
              `);
              addRecent("Qur'an", `Surah ${surah}, Ayah ${ayah}`);
            } catch {
              showOutput("quranOutput", "Qur'an Result", "<div class='out-muted'>Unable to load ayah right now.</div>");
            }
          }

          async function searchQuranKeywords() {
            const q = document.getElementById("quranKeyword").value.trim();
            const surah = document.getElementById("quranKeywordSurah").value.trim();
            const host = document.getElementById("quranSearchResults");
            if (!q) {
              host.innerHTML = "<div class='out-muted'>Enter a keyword first.</div>";
              return;
            }
            host.innerHTML = "<div class='out-muted'>Searching Qur'an...</div>";
            try {
              const params = new URLSearchParams({ q, limit: "8" });
              if (surah) params.set("surah", surah);
              const res = await fetch(`${API_BASE}/quran/search?${params.toString()}&lang=en`);
              const data = await res.json();
              const results = Array.isArray(data.results) ? data.results : [];
              if (!results.length) {
                host.innerHTML = "<div class='out-muted'>No keyword matches found.</div>";
                return;
              }
              host.innerHTML = results.map((r) => `
                <div class="search-item">
                  <b>Surah ${escapeHtml(r.surah_number)} · Ayah ${escapeHtml(r.ayah_number_in_surah)}</b>
                  <p>${escapeHtml((r.text_english_sahih || "").slice(0, 190))}</p>
                  <button type="button" data-quran-go="${escapeHtml(r.surah_number)}:${escapeHtml(r.ayah_number_in_surah)}">Open Ayah</button>
                </div>
              `).join("");
              host.querySelectorAll("[data-quran-go]").forEach((btn) => {
                btn.onclick = () => {
                  const [s, a] = btn.getAttribute("data-quran-go").split(":").map(Number);
                  loadQuranAyah(s, a, "Keyword Search");
                };
              });
              addRecent("Qur'an Search", q);
            } catch {
              host.innerHTML = "<div class='out-muted'>Search request failed.</div>";
            }
          }

          function randomAyah() {
            if (!state.surahs.length) {
              loadQuranAyah(1, 1, "Random Picker");
              return;
            }
            const surah = state.surahs[Math.floor(Math.random() * state.surahs.length)];
            const maxAyah = Number(surah.ayah_count) || 1;
            const ayah = 1 + Math.floor(Math.random() * maxAyah);
            loadQuranAyah(Number(surah.surah_number), ayah, "Random Picker");
          }

          async function loadHadith() {
            const collection = document.getElementById("hadithCollectionSelect").value;
            const number = Number(document.getElementById("hadithNumberInput").value || 1);
            if (!collection || !Number.isInteger(number) || number < 1) {
              showOutput("hadithOutput", "Hadith Result", "<div class='out-muted'>Provide a valid collection and hadith number.</div>");
              return;
            }
            loadingOutput("hadithOutput", "Hadith Result");
            try {
              const res = await fetch(`${API_BASE}/hadith/${encodeURIComponent(collection)}/${number}?lang=en`);
              const data = await res.json();
              if (!data.found || !data.data) {
                showOutput("hadithOutput", "Hadith Result", "<div class='out-muted'>No hadith found for this reference.</div>");
                return;
              }
              const d = data.data;
              state.latestExport.hadith = {
                title: `${d.collection_name || d.collection_key || "Hadith"} - Hadith ${d.hadith_number}`,
                subtitle: "Hadith Reflection Card",
                arabic: d.text_arabic || "",
                english: d.text_english || "",
                meta: `Collection ${d.collection_key || "-"} | Book ${d.book_number || "-"} | Ref ${d.hadith_ref_number || "-"}`
              };
              showOutput("hadithOutput", `${escapeHtml(d.collection_name)} · Hadith ${escapeHtml(d.hadith_number)}`, `
                <div class="chips">
                  <span>Collection: ${escapeHtml(d.collection_key)}</span>
                  <span>Book: ${escapeHtml(d.book_number || "-")}</span>
                  <span>Ref: ${escapeHtml(d.hadith_ref_number || "-")}</span>
                </div>
                <div class="out-ar">${escapeHtml(d.text_arabic || "")}</div>
                <div class="out-en">${escapeHtml(d.text_english || "")}</div>
                <div><button type="button" class="download-card-btn" onclick="downloadStudyCard('hadith')">Download Image</button></div>
              `);
              addRecent("Hadith", `${collection} #${number}`);
            } catch {
              showOutput("hadithOutput", "Hadith Result", "<div class='out-muted'>Unable to load hadith right now.</div>");
            }
          }

          async function searchHadith() {
            const keyword = document.getElementById("hadithKeyword").value.trim();
            const collection = document.getElementById("hadithSearchCollection").value.trim();
            const host = document.getElementById("hadithSearchResults");
            if (!keyword) {
              host.innerHTML = "<div class='out-muted'>Enter a hadith keyword first.</div>";
              return;
            }
            host.innerHTML = "<div class='out-muted'>Searching hadith...</div>";
            try {
              const params = new URLSearchParams({ q: keyword, limit: "8" });
              if (collection) params.set("collection", collection);
              const res = await fetch(`${API_BASE}/hadith/search?${params.toString()}&lang=en`);
              const data = await res.json();
              const results = Array.isArray(data.results) ? data.results : [];
              if (!results.length) {
                host.innerHTML = "<div class='out-muted'>No hadith matches found.</div>";
                return;
              }
              host.innerHTML = results.map((r) => `
                <div class="search-item">
                  <b>${escapeHtml(r.collection_name)} · ${escapeHtml(r.hadith_number)}</b>
                  <p>${escapeHtml((r.text_english || "").slice(0, 190))}</p>
                  <button type="button" data-hadith-go="${escapeHtml(r.collection_key)}:${escapeHtml(r.hadith_number)}">Open Hadith</button>
                </div>
              `).join("");
              host.querySelectorAll("[data-hadith-go]").forEach((btn) => {
                btn.onclick = () => {
                  const [collectionKey, hadithNum] = btn.getAttribute("data-hadith-go").split(":");
                  document.getElementById("hadithCollectionSelect").value = collectionKey;
                  document.getElementById("hadithNumberInput").value = hadithNum;
                  loadHadith();
                };
              });
              addRecent("Hadith Search", keyword + (collection ? ` (${collection})` : ""));
            } catch {
              host.innerHTML = "<div class='out-muted'>Search request failed.</div>";
            }
          }

          async function convertGregorianToHijri() {
            const date = document.getElementById("gregorianInput").value;
            if (!date) {
              showOutput("hijriOutput", "Date Conversion", "<div class='out-muted'>Select a Gregorian date first.</div>");
              return;
            }
            loadingOutput("hijriOutput", "Date Conversion");
            try {
              const res = await fetch(`${API_BASE}/hijri/from-gregorian?date=${encodeURIComponent(date)}&lang=en`);
              const data = await res.json();
              if (!data.found) {
                showOutput("hijriOutput", "Date Conversion", "<div class='out-muted'>Date not found in table range.</div>");
                return;
              }
              showOutput("hijriOutput", "Gregorian -> Hijri", `
                <div class="out-en"><strong>${escapeHtml(date)}</strong> corresponds to <strong>${escapeHtml(data.hijri_iso)}</strong>.</div>
              `);
              addRecent("Date Conversion", `${date} -> ${data.hijri_iso}`);
            } catch {
              showOutput("hijriOutput", "Date Conversion", "<div class='out-muted'>Conversion failed.</div>");
            }
          }

          async function convertHijriToGregorian() {
            const y = Number(document.getElementById("hijriYearInput").value);
            const m = Number(document.getElementById("hijriMonthInput").value);
            const d = Number(document.getElementById("hijriDayInput").value);
            if (!y || !m || !d) {
              showOutput("hijriOutput", "Date Conversion", "<div class='out-muted'>Provide Hijri year, month, and day.</div>");
              return;
            }
            loadingOutput("hijriOutput", "Date Conversion");
            try {
              const res = await fetch(`${API_BASE}/hijri/to-gregorian?year=${y}&month=${m}&day=${d}&lang=en`);
              const data = await res.json();
              if (!data.found) {
                showOutput("hijriOutput", "Date Conversion", "<div class='out-muted'>Date not found in table range.</div>");
                return;
              }
              showOutput("hijriOutput", "Hijri -> Gregorian", `
                <div class="out-en"><strong>${escapeHtml(`${y}-${m}-${d}`)}</strong> corresponds to <strong>${escapeHtml(data.gregorian_iso)}</strong>.</div>
              `);
              addRecent("Date Conversion", `${y}-${m}-${d} -> ${data.gregorian_iso}`);
            } catch {
              showOutput("hijriOutput", "Date Conversion", "<div class='out-muted'>Conversion failed.</div>");
            }
          }

          function toPrayerApiDate(iso) {
            if (!iso) return "";
            const parts = iso.split("-");
            if (parts.length !== 3) return iso;
            return `${parts[2]}-${parts[1]}-${parts[0]}`;
          }

          function minutesFromTime(value) {
            const m = /^([0-2]?\\d):([0-5]\\d)$/.exec((value || "").trim());
            if (!m) return null;
            return (Number(m[1]) * 60) + Number(m[2]);
          }

          function nowMinutesInTimezone(timeZone) {
            try {
              const parts = new Intl.DateTimeFormat("en-GB", {
                timeZone: timeZone || "Africa/Lagos",
                hour: "2-digit",
                minute: "2-digit",
                hour12: false
              }).formatToParts(new Date());
              const map = Object.fromEntries(parts.filter((p) => p.type !== "literal").map((p) => [p.type, p.value]));
              return (Number(map.hour) * 60) + Number(map.minute);
            } catch {
              const n = new Date();
              return (n.getHours() * 60) + n.getMinutes();
            }
          }

          async function loadPrayerSchedule() {
            const country = document.getElementById("prayerCountryInput").value.trim();
            const city = document.getElementById("prayerCityInput").value.trim();
            const dateIso = document.getElementById("prayerDateInput").value;
            if (!country || !city) {
              showOutput("prayerOutput", "Prayer Schedule", "<div class='out-muted'>Provide both country and city.</div>");
              return;
            }
            loadingOutput("prayerOutput", "Prayer Schedule");
            try {
              const normalizedDate = toPrayerApiDate(dateIso);
              let usedFallback = false;
              let data = null;

              if (normalizedDate) {
                const datedParams = new URLSearchParams({ country, city, lang: "en", date_gregorian: normalizedDate });
                const datedRes = await fetch(`${API_BASE}/prayer/times?${datedParams.toString()}`);
                const datedData = await datedRes.json();
                if (datedData.found && datedData.data) {
                  data = datedData;
                } else {
                  usedFallback = true;
                }
              }

              if (!data) {
                const latestParams = new URLSearchParams({ country, city, lang: "en" });
                const latestRes = await fetch(`${API_BASE}/prayer/times?${latestParams.toString()}`);
                const latestData = await latestRes.json();
                if (latestData.found && latestData.data) {
                  data = latestData;
                }
              }

              if (!data || !data.found || !data.data) {
                showOutput("prayerOutput", "Prayer Schedule", "<div class='out-muted'>No schedule found for this request.</div>");
                return;
              }

              const d = data.data;
              let nextPrayerLine = "Next prayer estimate unavailable for this snapshot.";
              const nowMin = nowMinutesInTimezone(d.timezone || "Africa/Lagos");
              const order = [["Fajr", d.fajr], ["Dhuhr", d.dhuhr], ["Asr", d.asr], ["Maghrib", d.maghrib], ["Isha", d.isha]];
              const mins = order.map(([name, time]) => [name, minutesFromTime(time)]);
              let next = mins.find(([, t]) => t !== null && t > nowMin);
              if (!next && mins[0] && mins[0][1] !== null) next = mins[0];
              if (next) {
                let diff = next[1] - nowMin;
                if (diff < 0) diff += 24 * 60;
                const h = Math.floor(diff / 60);
                const m = diff % 60;
                nextPrayerLine = `Next prayer: ${next[0]} in ${h}h ${m}m (${d.timezone || "local time"}).`;
              }
              const fallbackLine = usedFallback
                ? `<div class="out-muted">Requested date was unavailable. Showing latest available schedule for this city.</div>`
                : "";
              showOutput("prayerOutput", `${escapeHtml(d.city)}, ${escapeHtml(d.country)}`, `
                <div class="chips">
                  <span>Date: ${escapeHtml(d.date_gregorian)}</span>
                  <span>Hijri: ${escapeHtml(d.date_hijri)}</span>
                  <span>Timezone: ${escapeHtml(d.timezone || "-")}</span>
                </div>
                <div class="out-en"><strong>Fajr:</strong> ${escapeHtml(d.fajr)} | <strong>Dhuhr:</strong> ${escapeHtml(d.dhuhr)} | <strong>Asr:</strong> ${escapeHtml(d.asr)}</div>
                <div class="out-en"><strong>Maghrib:</strong> ${escapeHtml(d.maghrib)} | <strong>Isha:</strong> ${escapeHtml(d.isha)}</div>
                <div class="out-muted">${escapeHtml(nextPrayerLine)}</div>
                ${fallbackLine}
              `);
              addRecent("Prayer", `${country} - ${city}`);
            } catch {
              showOutput("prayerOutput", "Prayer Schedule", "<div class='out-muted'>Unable to load prayer schedule.</div>");
            }
          }

          async function searchCities() {
            const q = document.getElementById("citySearchQuery").value.trim();
            const country = document.getElementById("citySearchCountry").value.trim();
            const host = document.getElementById("citySearchResults");
            if (!q) {
              host.innerHTML = "<div class='out-muted'>Enter a city keyword first.</div>";
              return;
            }
            host.innerHTML = "<div class='out-muted'>Searching cities...</div>";
            try {
              const params = new URLSearchParams({ q, limit: "12", lang: "en" });
              if (country) params.set("country", country);
              const res = await fetch(`${API_BASE}/prayer/search-city?${params.toString()}`);
              const data = await res.json();
              const results = Array.isArray(data.results) ? data.results : [];
              if (!results.length) {
                host.innerHTML = "<div class='out-muted'>No cities found.</div>";
                return;
              }
              host.innerHTML = results.map((r) => `
                <div class="search-item">
                  <b>${escapeHtml(r.city)}, ${escapeHtml(r.country)}</b>
                  <p>Timezone: ${escapeHtml(r.timezone || "-")} | Fajr: ${escapeHtml(r.fajr || "-")} | Maghrib: ${escapeHtml(r.maghrib || "-")}</p>
                  <button type="button" data-city-pick="${escapeHtml(r.country)}|||${escapeHtml(r.city)}">Use this location</button>
                </div>
              `).join("");
              host.querySelectorAll("[data-city-pick]").forEach((btn) => {
                btn.onclick = () => {
                  const [pickedCountry, pickedCity] = btn.getAttribute("data-city-pick").split("|||");
                  document.getElementById("prayerCountryInput").value = pickedCountry;
                  document.getElementById("prayerCityInput").value = pickedCity;
                  loadPrayerSchedule();
                };
              });
              addRecent("City Search", q + (country ? ` (${country})` : ""));
            } catch {
              host.innerHTML = "<div class='out-muted'>City search failed.</div>";
            }
          }

          function getTimePartsInTimezone(timeZone) {
            const parts = new Intl.DateTimeFormat("en-GB", {
              timeZone: timeZone || "Africa/Lagos",
              year: "numeric",
              month: "2-digit",
              day: "2-digit",
              hour: "2-digit",
              minute: "2-digit",
              second: "2-digit",
              hour12: false
            }).formatToParts(new Date());
            const map = Object.fromEntries(parts.filter((p) => p.type !== "literal").map((p) => [p.type, p.value]));
            return {
              day: map.day,
              month: map.month,
              year: map.year,
              hour: Number(map.hour),
              minute: Number(map.minute),
              second: Number(map.second)
            };
          }

          function renderDamaturuTree() {
            const schedule = state.damaturu.schedule;
            if (!schedule) return;
            const tz = schedule.timezone || "Africa/Lagos";
            const now = getTimePartsInTimezone(tz);
            const nowMin = (now.hour * 60) + now.minute;
            document.getElementById("damClock").textContent = `${String(now.hour).padStart(2, "0")}:${String(now.minute).padStart(2, "0")}:${String(now.second).padStart(2, "0")}`;

            const prayers = [
              ["Fajr", schedule.fajr],
              ["Dhuhr", schedule.dhuhr],
              ["Asr", schedule.asr],
              ["Maghrib", schedule.maghrib],
              ["Isha", schedule.isha]
            ];
            const mins = prayers.map(([name, value]) => [name, minutesFromTime(value)]);

            let nextIdx = mins.findIndex(([, t]) => t !== null && t > nowMin);
            if (nextIdx === -1) nextIdx = 0;

            let diff = 0;
            if (mins[nextIdx] && mins[nextIdx][1] !== null) {
              diff = mins[nextIdx][1] - nowMin;
              if (diff < 0) diff += (24 * 60);
            }
            const hh = Math.floor(diff / 60);
            const mm = diff % 60;
            document.getElementById("damNext").textContent =
              `Next prayer in Damaturu: ${mins[nextIdx] ? mins[nextIdx][0] : "N/A"} in ${hh}h ${mm}m`;

            const tree = document.getElementById("damTree");
            tree.innerHTML = prayers.map(([name, time], idx) => {
              const tMin = minutesFromTime(time);
              const isDone = tMin !== null && tMin <= nowMin;
              const isNext = idx === nextIdx;
              const badge = isDone ? "✓" : isNext ? "⏳" : "•";
              const cls = `prayer-node${isDone ? " done" : ""}${isNext ? " next" : ""}`;
              return `<div class="${cls}">${name}<br>${escapeHtml(time || "--")}<br>${badge}</div>`;
            }).join("");
          }

          async function initDamaturuPrayer() {
            try {
              const params = new URLSearchParams({ country: "Nigeria", city: "Damaturu", lang: "en" });
              const res = await fetch(`${API_BASE}/prayer/times?${params.toString()}`);
              const data = await res.json();
              if (data.found && data.data) {
                state.damaturu.schedule = data.data;
                renderDamaturuTree();
                if (state.damaturu.timer) clearInterval(state.damaturu.timer);
                state.damaturu.timer = setInterval(renderDamaturuTree, 1000);
              } else {
                document.getElementById("damNext").textContent = "Damaturu prayer schedule unavailable.";
              }
            } catch {
              document.getElementById("damNext").textContent = "Unable to load Damaturu prayer schedule.";
            }
          }

          function bindInteractions() {
            document.querySelectorAll(".mode-card").forEach((btn) => {
              btn.onclick = () => activatePanel(btn.getAttribute("data-panel"));
            });

            document.querySelectorAll("[data-quran-mode]").forEach((btn) => {
              btn.onclick = () => setQuranMode(btn.getAttribute("data-quran-mode"));
            });

            document.getElementById("loadByNameBtn").onclick = () => {
              const { surah, ayah } = selectedSurahByName();
              loadQuranAyah(surah, ayah, "Surah Name Lookup");
            };
            document.getElementById("loadByNumberBtn").onclick = () => {
              const { surah, ayah } = selectedSurahByNumber();
              loadQuranAyah(surah, ayah, "Surah Number Lookup");
            };
            document.getElementById("randomAyahBtn").onclick = randomAyah;
            document.getElementById("searchQuranBtn").onclick = searchQuranKeywords;

            document.getElementById("loadHadithBtn").onclick = loadHadith;
            document.getElementById("searchHadithBtn").onclick = searchHadith;

            document.getElementById("gregToHijriBtn").onclick = convertGregorianToHijri;
            document.getElementById("hijriToGregBtn").onclick = convertHijriToGregorian;
            document.getElementById("loadTodayHijriBtn").onclick = async () => {
              const today = new Date().toISOString().slice(0, 10);
              document.getElementById("gregorianInput").value = today;
              await convertGregorianToHijri();
            };

            document.getElementById("loadPrayerBtn").onclick = loadPrayerSchedule;
            document.getElementById("searchCityBtn").onclick = searchCities;

            document.getElementById("saveNoteBtn").onclick = () => {
              const input = document.getElementById("noteInput");
              const text = input.value.trim();
              if (!text) return;
              state.notes.unshift({ text, stamp: new Date().toLocaleString() });
              state.notes = state.notes.slice(0, 20);
              saveStore(STORE_KEYS.notes, state.notes);
              input.value = "";
              renderNotes();
            };
          }

          function initHeroGallery() {
            const slidesHost = document.getElementById("heroSlides");
            const thumbsHost = document.getElementById("heroThumbs");
            const progress = document.getElementById("heroProgress");
            const counter = document.getElementById("heroSlideIndex");
            const images = Array.isArray(galleryImages) && galleryImages.length ? galleryImages : ["/static/hero-1.png"];

            slidesHost.innerHTML = "";
            thumbsHost.innerHTML = "";

            images.forEach((src, idx) => {
              const img = document.createElement("img");
              img.src = src;
              img.alt = `Gallery ${idx + 1}`;
              if (idx === 0) img.classList.add("active");
              slidesHost.appendChild(img);

              const thumb = document.createElement("img");
              thumb.src = src;
              thumb.alt = `Thumb ${idx + 1}`;
              thumb.className = "gallery-thumb" + (idx === 0 ? " active" : "");
              thumb.onclick = () => setSlide(idx);
              thumbsHost.appendChild(thumb);
            });

            const slideEls = [...slidesHost.querySelectorAll("img")];
            const thumbEls = [...thumbsHost.querySelectorAll(".gallery-thumb")];
            let index = 0;
            let timer = null;

            function setSlide(next) {
              index = (next + slideEls.length) % slideEls.length;
              slideEls.forEach((el, i) => el.classList.toggle("active", i === index));
              thumbEls.forEach((el, i) => el.classList.toggle("active", i === index));
              const pct = ((index + 1) / slideEls.length) * 100;
              progress.style.width = `${pct}%`;
              counter.textContent = `${index + 1} / ${slideEls.length}`;
              const activeThumb = thumbEls[index];
              if (activeThumb) {
                const targetLeft = activeThumb.offsetLeft - (thumbsHost.clientWidth / 2) + (activeThumb.clientWidth / 2);
                thumbsHost.scrollTo({ left: Math.max(0, targetLeft), behavior: "smooth" });
              }
            }

            function startAutoplay() {
              if (timer) clearInterval(timer);
              timer = setInterval(() => setSlide(index + 1), 4500);
            }

            setSlide(0);
            startAutoplay();
          }

          function initReveal() {
            const items = document.querySelectorAll(".reveal");
            const io = new IntersectionObserver((entries) => {
              entries.forEach((entry) => {
                if (!entry.isIntersecting) return;
                entry.target.classList.add("show");
                io.unobserve(entry.target);
              });
            }, { threshold: 0.15 });
            items.forEach((item) => io.observe(item));
          }

          async function init() {
            initHeroGallery();
            initDamaturuPrayer();
            initReveal();

            state.recent = loadStore(STORE_KEYS.recent, []);
            state.notes = loadStore(STORE_KEYS.notes, []);
            renderRecent();
            renderNotes();

            const todayIso = new Date().toISOString().slice(0, 10);
            document.getElementById("gregorianInput").value = todayIso;
            document.getElementById("prayerDateInput").value = "";
            document.getElementById("copyrightText").textContent =
              `Copyright © ${new Date().getFullYear()} At-Tibyan Centre. All rights reserved.`;

            bindInteractions();
            showOutput("quranOutput", "Qur'an Result", "<div class='out-muted'>Choose lookup mode, then load an ayah.</div>");
            showOutput("hadithOutput", "Hadith Result", "<div class='out-muted'>Select a collection and hadith number to begin.</div>");
            showOutput("hijriOutput", "Date Conversion", "<div class='out-muted'>Run a conversion request to see results.</div>");
            showOutput("prayerOutput", "Prayer Schedule", "<div class='out-muted'>Load a schedule for your selected location.</div>");

            await Promise.all([
              loadMetaCounters(),
              loadTodayBadge(),
              loadSurahCatalog(),
              loadHadithCollections()
            ]);
          }

          init();
        </script>
      </body>
    </html>
    """
    return html.replace("__GALLERY_IMAGES__", gallery_json)


@app.get("/developers", response_class=HTMLResponse, include_in_schema=False)
def developers_page() -> str:
    return """
    <!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Developers | At-Tibyan Centre API</title>
    <link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&family=Manrope:wght@400;600;700&display=swap" rel="stylesheet">
    <style>
      :root{--bg:#f3f6f2;--ink:#15241d;--line:#d7e2db;--panel:#fff;--muted:#5b7065;--brand:#2f6e56}
      *{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:"Manrope","Trebuchet MS",sans-serif}
      .wrap{max-width:980px;margin:0 auto;padding:24px 16px 38px}
      .hero,.card{background:var(--panel);border:1px solid var(--line);border-radius:14px}
      .hero{padding:18px}.hero h1{margin:0;font-family:"Fraunces","Georgia",serif}
      .hero p{color:var(--muted)}a{color:var(--brand);font-weight:700;text-decoration:none}
      .grid{margin-top:12px;display:grid;gap:12px}
      .card{padding:14px}h2{margin:0 0 8px;font-family:"Fraunces","Georgia",serif}
      pre{margin:0;background:#f7fbf8;border:1px solid #dce7e0;border-radius:10px;padding:10px;overflow:auto}
      code{font-family:Consolas,monospace}
    </style></head><body>
      <div class="wrap">
        <section class="hero">
          <h1>Developers Guide</h1>
          <p>Use the resources below to run and integrate the At-Tibyan API platform.</p>
          <p><a href="/">Homepage</a> · <a href="/docs">Interactive Docs</a> · <a href="/v1/meta">Live Metadata</a></p>
        </section>
        <section class="grid">
          <article class="card">
            <h2>Local Install</h2>
            <pre><code>python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python scripts/build_db.py
uvicorn app.main:app --host 127.0.0.1 --port 8000</code></pre>
          </article>
          <article class="card">
            <h2>UTF-8 for PowerShell</h2>
            <pre><code>chcp 65001
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()</code></pre>
          </article>
          <article class="card">
            <h2>Example Calls</h2>
            <pre><code>GET /v1/quran/surahs
GET /v1/quran/ayah/1/1
GET /v1/hadith/collections
GET /v1/hadith/bukhari/15
GET /v1/hijri/from-gregorian?date=2026-05-02
GET /v1/prayer/times?country=Nigeria&city=Lagos%20Island</code></pre>
          </article>
        </section>
      </div>
    </body></html>
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
