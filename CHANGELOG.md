# Changelog

All notable changes to this project are documented in this file.

## [1.0.0] - 2026-04-29

### Added
- Initial `v1` API with Quran, Hadith, Hijri, and Prayer endpoints.
- SQLite indexing pipeline (`scripts/build_db.py`) with FTS5 search for Quran and Hadith.
- Root landing page with developer-oriented documentation sections.
- Vercel serverless entrypoint (`api/index.py`) and runtime routing (`vercel.json`).
- Metadata endpoint and structured dataset counts.

### Changed
- Improved ingestion normalization for Arabic text handling.
- Expanded README with endpoint request/response examples and HTTPS-only production guidance.

### Fixed
- Serverless filesystem crash by honoring writable `ANJAL_DB_PATH` path.
