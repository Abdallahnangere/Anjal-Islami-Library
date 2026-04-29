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

## Endpoints

- `GET /v1/health`
- `GET /v1/meta`

Quran:
- `GET /v1/quran/ayah/{surah}/{ayah}`
- `GET /v1/quran/search?q=mercy&limit=10`

Hadith:
- `GET /v1/hadith/{collection}/{hadith_number}`
- `GET /v1/hadith/search?q=prayer&collection=bukhari&limit=10`

Hijri:
- `GET /v1/hijri/to-gregorian?year=1447&month=10&day=11`
- `GET /v1/hijri/from-gregorian?date=2026-04-29`

Prayer:
- `GET /v1/prayer/countries`
- `GET /v1/prayer/cities?country=Nigeria`
- `GET /v1/prayer/times?country=Nigeria&city=Lagos`
- `GET /v1/prayer/search-city?q=Abuja`

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
