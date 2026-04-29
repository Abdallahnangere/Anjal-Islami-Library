# Anjal Islamic Library API

Versioned Islamic data API repository for year-round app usage and public developer access.

Maintainer: **Abdallah Nangere**  
Contact: **founder@ramadanbot.app** | **+2348164135836**

## Included Datasets

- Umm al-Qura Hijri dates (`1343-01-01 AH` to `1500-12-30 AH`)
- Quran (`quran-uthmani` Arabic + `en.sahih` English)
- Hadith (Arabic+English merged collections)
- Prayer times (all Nigeria entries + selected global countries/cities)

## API Version

- Current: `v1`
- Base URL (local): `http://127.0.0.1:8000`
- Production URL: `https://islamiclibrary.anjalventures.com`
- Note: Production is **HTTPS-only**. `http://` requests return `308 Permanent Redirect`.

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/build_db.py
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Swagger docs:
- `http://127.0.0.1:8000/docs`

## Vercel (Current Phase)

This repo is configured for Vercel Python runtime via:
- `api/index.py`
- `vercel.json`

On Vercel, the API writes `library.db` to `/tmp/anjal/library.db` on cold start if not already present.

## Endpoints (With Samples)

### Meta

Request:
```http
GET /v1/health
```
Response:
```json
{"ok": true, "service": "Anjal Islamic Library API", "version": "v1"}
```

Request:
```http
GET /v1/meta
```
Response (sample):
```json
{
  "service": "Anjal Islamic Library API",
  "version": "v1",
  "counts": {
    "quran_ayahs": 6236,
    "hadith_entries": 36512,
    "hijri_dates": 55991,
    "prayer_times": 836
  },
  "metadata": {
    "project_name": "Anjal Islamic Library API",
    "author": "Abdallah Nangere"
  }
}
```

### Quran

Request:
```http
GET /v1/quran/ayah/1/1
```
Response (sample):
```json
{
  "found": true,
  "data": {
    "surah_number": 1,
    "ayah_number_in_surah": 1,
    "text_english_sahih": "In the name of Allah, the Entirely Merciful, the Especially Merciful."
  }
}
```

Request:
```http
GET /v1/quran/search?q=mercy&limit=10
```
Response (shape):
```json
{
  "query": "mercy",
  "count": 10,
  "results": [{ "surah_number": 1, "ayah_number_in_surah": 1 }]
}
```

### Hadith

Request:
```http
GET /v1/hadith/bukhari/15
```
Response (sample):
```json
{
  "found": true,
  "data": {
    "collection_key": "bukhari",
    "hadith_number": 15,
    "book_number": "2",
    "hadith_ref_number": "8"
  }
}
```

Request:
```http
GET /v1/hadith/search?q=prayer&collection=bukhari&limit=10
```
Response (shape):
```json
{
  "query": "prayer",
  "collection": "bukhari",
  "count": 10,
  "results": [{ "collection_key": "bukhari", "hadith_number": 8 }]
}
```

### Hijri

Request:
```http
GET /v1/hijri/to-gregorian?year=1447&month=11&day=12
```
Response:
```json
{"found": true, "gregorian_iso": "2026-04-29"}
```

Request:
```http
GET /v1/hijri/from-gregorian?date=2026-04-29
```
Response:
```json
{"found": true, "hijri_iso": "1447-11-12"}
```

### Prayer

Request:
```http
GET /v1/prayer/countries
```
Response (shape):
```json
{
  "count": 22,
  "countries": ["Nigeria", "Saudi Arabia", "United States"]
}
```

Request:
```http
GET /v1/prayer/cities?country=Nigeria
```
Response (shape):
```json
{
  "country": "Nigeria",
  "count": 768,
  "cities": ["Aba North", "Aba South", "Abadam"]
}
```

Request:
```http
GET /v1/prayer/times?country=Nigeria&city=Lagos%20Island
```
Response (sample):
```json
{
  "found": true,
  "data": {
    "country": "Nigeria",
    "city": "Lagos Island",
    "date_gregorian": "29-04-2026",
    "fajr": "05:34",
    "dhuhr": "12:44",
    "asr": "16:01",
    "maghrib": "18:54",
    "isha": "19:53"
  }
}
```

Request:
```http
GET /v1/prayer/search-city?q=Lagos
```
Response (sample):
```json
{
  "query": "Lagos",
  "count": 2,
  "results": [
    { "country": "Nigeria", "city": "Lagos Island" },
    { "country": "Nigeria", "city": "Lagos Mainland" }
  ]
}
```

## Repository Structure

```text
app/
  main.py
  db.py
  routers/
scripts/
  build_db.py
data/
  source/     # source CSV datasets
  index/      # generated SQLite index (library.db)
```

## Notes

- Full-text search is indexed using SQLite FTS5 for Quran and Hadith.
- Rebuild the index whenever source datasets are updated:
  - `python scripts/build_db.py`
- Route note: keep `/v1/hadith/search` defined before `/v1/hadith/{collection}/{hadith_number}`.
- SQLite note: one connection is opened per request and closed immediately; this is acceptable for current scope.
