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
    return """
    <!doctype html>
    <html lang="en">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>At-Tibyan Centre | Website and Islamic Knowledge Platform</title>
        <style>
          :root{
            --bg:#f8fbf9;
            --panel:#ffffff;
            --line:#d9e7de;
            --text:#0f1e17;
            --muted:#4e5f57;
            --green:#119b52;
            --deep:#1b144a;
            --accent:#2f7dff;
          }
          *{box-sizing:border-box}
          body{margin:0;font-family:Inter,Segoe UI,Arial,sans-serif;background:var(--bg);color:var(--text);line-height:1.55}
          .wrap{max-width:1220px;margin:0 auto;padding:20px}
          .top{position:sticky;top:0;background:rgba(255,255,255,.95);backdrop-filter:blur(8px);border-bottom:1px solid var(--line);z-index:10}
          .topin{max-width:1220px;margin:0 auto;padding:10px 20px;display:flex;align-items:center;justify-content:space-between;gap:12px}
          .brand{display:flex;align-items:center;gap:10px;font-weight:800}
          .brand img{width:44px;height:44px;border-radius:999px;object-fit:cover;border:2px solid var(--deep)}
          .nav a{margin-left:14px;text-decoration:none;color:var(--deep);font-weight:600;font-size:14px}
          .hero{margin-top:16px;display:grid;grid-template-columns:1.1fr 1fr;gap:14px}
          .card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px}
          .headline h1{margin:0 0 8px;font-size:36px;line-height:1.15}
          .headline p{color:var(--muted);margin:8px 0}
          .badges span{display:inline-block;margin:6px 6px 0 0;padding:5px 10px;border-radius:999px;border:1px solid var(--line);background:#eef9f2;font-size:12px}
          .media{position:relative;min-height:380px;overflow:hidden}
          .media img,.media video{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;border-radius:10px}
          .media .overlay{position:absolute;inset:auto 10px 10px 10px;background:rgba(27,20,74,.86);color:#fff;padding:10px 12px;border-radius:8px;font-size:13px}
          .slides{position:absolute;inset:0}
          .slides img{opacity:0;transition:opacity .8s}
          .slides img.active{opacity:1}
          .grid{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:14px;margin-top:14px}
          .c4{grid-column:span 4}.c6{grid-column:span 6}.c8{grid-column:span 8}.c12{grid-column:span 12}
          h2{margin:0 0 10px;font-size:20px}
          h3{margin:0 0 10px;font-size:16px}
          ul{margin:0;padding-left:18px;color:var(--muted)}
          table{width:100%;border-collapse:collapse;font-size:14px}
          th,td{border:1px solid var(--line);padding:8px;text-align:left;vertical-align:top}
          th{background:#f0f9f4}
          .tabs{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px}
          .tabbtn{border:1px solid var(--line);background:#fff;padding:8px 12px;border-radius:8px;cursor:pointer;font-weight:600}
          .tabbtn.active{background:var(--deep);color:#fff;border-color:var(--deep)}
          .tab{display:none}
          .tab.active{display:block}
          .row{display:grid;grid-template-columns:1fr 1fr;gap:10px}
          .field label{display:block;font-size:12px;color:var(--muted);margin-bottom:4px}
          .field input,.field select{width:100%;padding:9px;border-radius:8px;border:1px solid var(--line);background:#fff}
          button.action{padding:10px 12px;border:0;border-radius:8px;background:var(--green);color:#fff;font-weight:700;cursor:pointer}
          .output{
            margin-top:10px;
            min-height:420px;
            background:#fbfefc;
            border:1px solid var(--line);
            border-radius:10px;
            padding:14px;
            box-shadow:inset 0 0 0 1px #f1f6f3;
            display:flex;
            flex-direction:column;
            gap:8px;
            max-width:760px;
            aspect-ratio:1.414/1;
          }
          .output h4{margin:0;font-size:15px;color:var(--deep)}
          .output .line{height:1px;background:#e4eee8}
          .out-muted{color:var(--muted);font-size:14px}
          .out-ar{font-size:22px;line-height:1.9;text-align:right;direction:rtl}
          .out-en{font-size:16px;line-height:1.7}
          .mono{font-family:Consolas,Monaco,monospace}
          .progress{height:10px;background:#ecf2ee;border-radius:999px;overflow:hidden}
          .bar{height:100%;background:linear-gradient(90deg,var(--green),var(--deep));width:0%}
          .tree{display:grid;grid-template-columns:repeat(5,1fr);gap:8px}
          .leaf{padding:8px;border:1px solid var(--line);border-radius:8px;text-align:center;background:#fff}
          .leaf.done{background:#eaf8ef;border-color:#b8dfc5}
          .footer{margin:14px 0 40px;padding:14px;border:1px solid var(--line);background:var(--panel);border-radius:10px;color:var(--muted)}
          .muted{color:var(--muted)}
          @media (max-width:980px){
            .hero{grid-template-columns:1fr}
            .row{grid-template-columns:1fr}
            .c4,.c6,.c8,.c12{grid-column:span 12}
          }
        </style>
      </head>
      <body>
        <header class="top">
          <div class="topin">
            <div class="brand">
              <img src="/static/attibyan-logo.png" onerror="this.style.display='none'" alt="At-Tibyan Logo">
              <span>AT-TIBYAN CENTRE FOR SUNNAH AND ISLAMIC SCIENCES</span>
            </div>
            <nav class="nav">
              <a href="#about">About</a>
              <a href="#platform">Platform</a>
              <a href="#study-tools">Study Tools</a>
              <a href="#timings">Timings</a>
            </nav>
          </div>
        </header>

        <div class="wrap">
          <section class="hero">
            <article class="card headline">
              <h1>At-Tibyan Centre Website and Islamic Knowledge Platform</h1>
              <p id="about">At-Tibyan Centre is a structured digital learning and research platform focused on preserving, organizing, and presenting authentic Islamic knowledge in ways that are useful for students, teachers, institutions, and independent researchers.</p>
              <p>Our vision is to make beneficial knowledge consistently available beyond seasonal usage by providing reliable access to Qur'an study, hadith study, date conversion references, and prayer-time guidance through a focused and well-curated experience.</p>
              <p>The platform experience is intentionally designed for direct learning outcomes: search with precision, read with context, compare references, and quickly retrieve trusted content without technical complexity.</p>
              <div class="badges">
                <span>Quran 6,236 Ayahs</span><span>10 Hadith Collections</span><span>Umm al-Qura Hijri</span><span>Prayer Time Datasets</span><span>Arabic + English</span><span>Student and Research Focused</span>
              </div>
            </article>
            <article class="card media">
              <div class="slides">
                <img src="/static/hero-1.png" class="active" alt="Hero 1">
                <img src="/static/hero-2.png" alt="Hero 2">
                <img src="/static/hero-3.png" alt="Hero 3">
              </div>
              <video id="heroVideo" controls style="display:none" poster="/static/hero-1.png">
                <source src="/static/hero.mp4" type="video/mp4">
              </video>
              <div class="overlay">Featured session media from At-Tibyan Centre.</div>
            </article>
          </section>

          <section class="grid" id="platform">
            <article class="card c6">
              <h2>Platform Vision and Learning Impact</h2>
              <p class="muted">This website is built as a long-term Islamic knowledge platform that supports deep study, structured revision, teaching preparation, and everyday personal practice.</p>
              <p class="muted">It unifies key knowledge domains in one coherent interface so users can move from reading to reflection to verification with minimal friction.</p>
              <ul>
                <li>The complete Qur'an (114 Surahs, 6,236 Ayahs) with Arabic and English support.</li>
                <li>10 Hadith collections including Bukhari, Muslim, Abu Dawud, Tirmidhi, Nasai, Ibn Majah, Malik, Nawawi, and more.</li>
                <li>Hijri date conversion based on Umm al-Qura calendar standards.</li>
                <li>Prayer time datasets with regional and global coverage.</li>
                <li>Consistent search and reference access for study circles, classroom instruction, and academic projects.</li>
              </ul>
            </article>
            <article class="card c6" id="timings">
              <h2>Live Hijri / Gregorian + Prayer Progress</h2>
              <p><strong>Gregorian:</strong> <span id="gregNow">-</span></p>
              <p><strong>Hijri:</strong> <span id="hijriNow">-</span></p>
              <div class="row">
                <div class="field"><label>Country</label><input id="prCountry" value="Nigeria"></div>
                <div class="field"><label>City</label><input id="prCity" value="Lagos Island"></div>
              </div>
              <div style="margin-top:8px"><button class="action" onclick="loadPrayerWidget()">Load Prayer Widget</button></div>
              <p id="nextPrayer" class="muted" style="margin-top:8px">Next prayer: -</p>
              <div class="progress"><div id="dayBar" class="bar"></div></div>
              <div class="tree" id="tree" style="margin-top:10px"></div>
            </article>
          </section>

          <section class="card" id="study-tools">
            <h2>Interactive Study Studio</h2>
            <p class="muted">Use the tools below as a learner-facing study workspace. Results are rendered in a structured reading panel for concentration and review.</p>
            <div class="tabs">
              <button class="tabbtn active" data-tab="quran">Qur'an Study</button>
              <button class="tabbtn" data-tab="hadith">Hadith Study</button>
              <button class="tabbtn" data-tab="hijri">Date Conversion</button>
              <button class="tabbtn" data-tab="prayer">Prayer Planner</button>
            </div>

            <div id="tab-quran" class="tab active">
              <h3>Qur'an Reading Panel</h3>
              <div class="row">
                <div class="field"><label>Surah</label><select id="surah"></select></div>
                <div class="field"><label>Ayah</label><input id="ayah" type="number" min="1" value="1"></div>
              </div>
              <div style="margin-top:8px"><button class="action" onclick="fetchQuran()">Load Ayah</button></div>
              <div id="quranOut" class="output"><h4>Qur'an Output</h4><div class="line"></div><div class="out-muted">Select a Surah and Ayah to begin.</div></div>
            </div>

            <div id="tab-hadith" class="tab">
              <h3>Hadith Reading Panel</h3>
              <div class="row">
                <div class="field">
                  <label>Collection</label>
                  <select id="hadithCollection">
                    <option>bukhari</option><option>muslim</option><option>abudawud</option><option>tirmidhi</option><option>nasai</option>
                    <option>ibnmajah</option><option>malik</option><option>nawawi</option><option>riyadussalihin</option><option>qudsi</option>
                  </select>
                </div>
                <div class="field"><label>Hadith Number</label><input id="hadithNumber" type="number" min="1" value="15"></div>
              </div>
              <div style="margin-top:8px"><button class="action" onclick="fetchHadith()">Load Hadith</button></div>
              <div id="hadithOut" class="output"><h4>Hadith Output</h4><div class="line"></div><div class="out-muted">Select a collection and hadith number to begin.</div></div>
            </div>

            <div id="tab-hijri" class="tab">
              <h3>Hijri / Gregorian Reference</h3>
              <div class="row">
                <div class="field"><label>Gregorian (YYYY-MM-DD)</label><input id="gregDate" value=""></div>
                <div class="field"><label>Hijri (Y-M-D)</label><input id="hijriDateParts" value="1447-11-12"></div>
              </div>
              <div style="margin-top:8px;display:flex;gap:8px;flex-wrap:wrap">
                <button class="action" onclick="fromGregorian()">Gregorian -> Hijri</button>
                <button class="action" onclick="toGregorian()">Hijri -> Gregorian</button>
              </div>
              <div id="hijriOut" class="output"><h4>Date Output</h4><div class="line"></div><div class="out-muted">Choose direction and load conversion.</div></div>
            </div>

            <div id="tab-prayer" class="tab">
              <h3>Prayer Schedule Panel</h3>
              <div class="row">
                <div class="field"><label>Country</label><input id="prCountry2" value="Nigeria"></div>
                <div class="field"><label>City</label><input id="prCity2" value="Lagos Island"></div>
              </div>
              <div style="margin-top:8px"><button class="action" onclick="fetchPrayer()">Load Prayer Schedule</button></div>
              <div id="prayerOut" class="output"><h4>Prayer Output</h4><div class="line"></div><div class="out-muted">Enter location and load schedule.</div></div>
            </div>
          </section>

          <section class="card">
            <h2>Coverage Summary</h2>
            <table>
              <tr><th>Dataset</th><th>Coverage</th><th>Rows</th><th>Primary Source</th></tr>
              <tr><td>Quran</td><td>114 Surahs, 6,236 Ayahs</td><td>6,236</td><td>AlQuran Cloud editions</td></tr>
              <tr><td>Hadith</td><td>Arabic + English merged collections</td><td>36,512</td><td>Hadith API open corpus</td></tr>
              <tr><td>Hijri</td><td>1343-01-01 AH to 1500-12-30 AH</td><td>55,991</td><td>Umm al-Qura table</td></tr>
              <tr><td>Prayer Times</td><td>All Nigeria entries + selected global cities</td><td>836</td><td>AlAdhan API snapshots</td></tr>
            </table>
          </section>

          <section class="footer">
            <div><strong>AT-TIBYAN CENTRE FOR SUNNAH AND ISLAMIC SCIENCES</strong></div>
            <div>Built as a robust website and Islamic knowledge platform for sustained learning, research, and guided spiritual practice.</div>
          </section>
        </div>

        <script>
          const apiBase = "/v1";

          // slideshow
          const slides = [...document.querySelectorAll('.slides img')];
          let sIndex = 0;
          setInterval(() => {
            if (document.getElementById('heroVideo').style.display === 'block') return;
            slides[sIndex].classList.remove('active');
            sIndex = (sIndex + 1) % slides.length;
            slides[sIndex].classList.add('active');
          }, 2800);

          // optional video in hero
          const hv = document.getElementById("heroVideo");
          hv.addEventListener("error", () => {});
          fetch("/static/hero.mp4", { method: "HEAD" }).then(r => {
            if (r.ok) {
              document.querySelector('.slides').style.display = "none";
              hv.style.display = "block";
            }
          }).catch(() => {});

          // tabs
          const btns = [...document.querySelectorAll('.tabbtn')];
          btns.forEach(b => b.onclick = () => {
            btns.forEach(x => x.classList.remove('active'));
            b.classList.add('active');
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.getElementById('tab-' + b.dataset.tab).classList.add('active');
          });

          // surah dropdown
          const surahSelect = document.getElementById("surah");
          for (let i = 1; i <= 114; i++) {
            const o = document.createElement("option");
            o.value = i;
            o.textContent = "Surah " + i;
            surahSelect.appendChild(o);
          }

          function escapeHtml(v) {
            return String(v ?? "").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;");
          }

          async function fetchQuran() {
            const s = surahSelect.value;
            const a = document.getElementById("ayah").value || "1";
            const out = document.getElementById("quranOut");
            out.innerHTML = "<h4>Qur'an Output</h4><div class='line'></div><div class='out-muted'>Loading...</div>";
            const r = await fetch(`${apiBase}/quran/ayah/${s}/${a}?lang=en`);
            const j = await r.json();
            if (!j.found || !j.data) {
              out.innerHTML = "<h4>Qur'an Output</h4><div class='line'></div><div class='out-muted'>No ayah found for the selected reference.</div>";
              return;
            }
            out.innerHTML = `
              <h4>Surah ${escapeHtml(j.data.surah_number)} - Ayah ${escapeHtml(j.data.ayah_number_in_surah)}</h4>
              <div class='line'></div>
              <div class='out-ar'>${escapeHtml(j.data.text_arabic_uthmani || "")}</div>
              <div class='line'></div>
              <div class='out-en'>${escapeHtml(j.data.text_english_sahih || "")}</div>
              <div class='out-muted mono'>Juz ${escapeHtml(j.data.juz)} | Page ${escapeHtml(j.data.page)}</div>
            `;
          }

          async function fetchHadith() {
            const c = document.getElementById("hadithCollection").value;
            const n = document.getElementById("hadithNumber").value || "1";
            const out = document.getElementById("hadithOut");
            out.innerHTML = "<h4>Hadith Output</h4><div class='line'></div><div class='out-muted'>Loading...</div>";
            const r = await fetch(`${apiBase}/hadith/${c}/${n}?lang=en`);
            const j = await r.json();
            if (!j.found || !j.data) {
              out.innerHTML = "<h4>Hadith Output</h4><div class='line'></div><div class='out-muted'>No hadith found for this reference.</div>";
              return;
            }
            out.innerHTML = `
              <h4>${escapeHtml(j.data.collection_name)} - Hadith ${escapeHtml(j.data.hadith_number)}</h4>
              <div class='line'></div>
              <div class='out-ar'>${escapeHtml(j.data.text_arabic || "")}</div>
              <div class='line'></div>
              <div class='out-en'>${escapeHtml(j.data.text_english || "")}</div>
              <div class='out-muted mono'>Book ${escapeHtml(j.data.book_number)} | Ref ${escapeHtml(j.data.hadith_ref_number)}</div>
            `;
          }

          async function fromGregorian() {
            const d = document.getElementById("gregDate").value;
            const out = document.getElementById("hijriOut");
            out.innerHTML = "<h4>Date Output</h4><div class='line'></div><div class='out-muted'>Loading...</div>";
            const r = await fetch(`${apiBase}/hijri/from-gregorian?date=${encodeURIComponent(d)}&lang=en`);
            const j = await r.json();
            out.innerHTML = j.found
              ? `<h4>Gregorian to Hijri</h4><div class='line'></div><div class='out-en'><strong>${escapeHtml(d)}</strong> corresponds to <strong>${escapeHtml(j.hijri_iso)}</strong>.</div>`
              : "<h4>Date Output</h4><div class='line'></div><div class='out-muted'>Date not found in current table range.</div>";
          }

          async function toGregorian() {
            const p = (document.getElementById("hijriDateParts").value || "").split("-");
            const y = p[0], m = p[1], d = p[2];
            const out = document.getElementById("hijriOut");
            out.innerHTML = "<h4>Date Output</h4><div class='line'></div><div class='out-muted'>Loading...</div>";
            const r = await fetch(`${apiBase}/hijri/to-gregorian?year=${y}&month=${m}&day=${d}&lang=en`);
            const j = await r.json();
            out.innerHTML = j.found
              ? `<h4>Hijri to Gregorian</h4><div class='line'></div><div class='out-en'><strong>${escapeHtml(y)}-${escapeHtml(m)}-${escapeHtml(d)}</strong> corresponds to <strong>${escapeHtml(j.gregorian_iso)}</strong>.</div>`
              : "<h4>Date Output</h4><div class='line'></div><div class='out-muted'>Date not found in current table range.</div>";
          }

          async function fetchPrayer() {
            const country = document.getElementById("prCountry2").value;
            const city = document.getElementById("prCity2").value;
            const out = document.getElementById("prayerOut");
            out.innerHTML = "<h4>Prayer Output</h4><div class='line'></div><div class='out-muted'>Loading...</div>";
            const r = await fetch(`${apiBase}/prayer/times?country=${encodeURIComponent(country)}&city=${encodeURIComponent(city)}&lang=en`);
            const j = await r.json();
            if (!j.found || !j.data) {
              out.innerHTML = "<h4>Prayer Output</h4><div class='line'></div><div class='out-muted'>No prayer record found for this location.</div>";
              return;
            }
            const d = j.data;
            out.innerHTML = `
              <h4>${escapeHtml(d.city)}, ${escapeHtml(d.country)}</h4>
              <div class='line'></div>
              <div class='out-en'>Date: <strong>${escapeHtml(d.date_gregorian)}</strong> | Hijri: <strong>${escapeHtml(d.date_hijri)}</strong></div>
              <div class='out-en'>Fajr: <strong>${escapeHtml(d.fajr)}</strong> | Dhuhr: <strong>${escapeHtml(d.dhuhr)}</strong> | Asr: <strong>${escapeHtml(d.asr)}</strong></div>
              <div class='out-en'>Maghrib: <strong>${escapeHtml(d.maghrib)}</strong> | Isha: <strong>${escapeHtml(d.isha)}</strong></div>
              <div class='out-muted mono'>Timezone: ${escapeHtml(d.timezone || "-")} | Method: ${escapeHtml(d.method || "-")}</div>
            `;
          }

          function timeToMin(t) {
            const m = /^([0-2]?\\d):([0-5]\\d)$/.exec((t || "").trim());
            if (!m) return null;
            return (parseInt(m[1], 10) * 60) + parseInt(m[2], 10);
          }

          async function loadPrayerWidget() {
            const c = document.getElementById("prCountry").value;
            const city = document.getElementById("prCity").value;
            const res = await fetch(`${apiBase}/prayer/times?country=${encodeURIComponent(c)}&city=${encodeURIComponent(city)}&lang=en`);
            const json = await res.json();
            const now = new Date();
            document.getElementById("gregNow").textContent = now.toISOString().slice(0,10) + " " + now.toLocaleTimeString();
            const h = await fetch(`${apiBase}/hijri/from-gregorian?date=${now.toISOString().slice(0,10)}&lang=en`);
            const hj = await h.json();
            document.getElementById("hijriNow").textContent = hj.hijri_iso || "Not found";

            if (!json.found || !json.data) return;
            const pt = json.data;
            const names = ["fajr","dhuhr","asr","maghrib","isha"];
            const mins = names.map(n => timeToMin(pt[n]));
            const current = now.getHours() * 60 + now.getMinutes();
            let nextIdx = mins.findIndex(v => v !== null && v > current);
            if (nextIdx === -1) nextIdx = 0;
            const nextName = names[nextIdx];
            let diff = mins[nextIdx] - current;
            if (diff < 0) diff += 24*60;
            const hh = Math.floor(diff / 60), mm = diff % 60;
            document.getElementById("nextPrayer").textContent = `Next prayer: ${nextName.toUpperCase()} in ${hh}h ${mm}m`;

            const complete = mins.filter(v => v !== null && v <= current).length;
            const pct = Math.round((complete / 5) * 100);
            document.getElementById("dayBar").style.width = pct + "%";

            const tree = document.getElementById("tree");
            tree.innerHTML = "";
            names.forEach((n, i) => {
              const d = document.createElement("div");
              d.className = "leaf" + (i < complete ? " done" : "");
              d.textContent = n.toUpperCase();
              tree.appendChild(d);
            });
          }

          // defaults
          document.getElementById("gregDate").value = new Date().toISOString().slice(0,10);
          loadPrayerWidget();
        </script>
      </body>
    </html>
    """


@app.get("/developers", response_class=HTMLResponse, include_in_schema=False)
def developers_page() -> str:
    return """
    <!doctype html>
    <html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Developers | At-Tibyan Centre API</title>
    <style>body{font-family:Inter,Segoe UI,Arial,sans-serif;background:#f8fbf9;padding:20px;color:#10201a}pre{background:#fff;border:1px solid #d9e7de;padding:10px;border-radius:8px;overflow:auto}a{color:#1b144a}</style></head>
    <body>
      <h1>Developers Guide</h1>
      <p>Interactive docs: <a href="/docs">/docs</a> | Homepage: <a href="/">/</a></p>
      <h2>Install</h2>
      <pre>python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python scripts/build_db.py
uvicorn app.main:app --host 127.0.0.1 --port 8000</pre>
      <h2>PowerShell UTF-8</h2>
      <pre>chcp 65001
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()</pre>
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
