# Contributing to Anjal Islamic Library API

Thanks for contributing.

## Scope

Contributions are welcome for:
- endpoint improvements
- performance and indexing
- dataset quality fixes
- docs and usage examples
- test coverage

## Development Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/build_db.py
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Branch and PR Process

1. Fork the repository
2. Create a feature branch: `feat/your-change` or `fix/your-change`
3. Keep commits small and clear
4. Open a PR with:
   - problem statement
   - changes made
   - endpoint/sample output proof

## Data Change Rules

- Do not overwrite source files without documenting source and date.
- Keep schema backward-compatible for `v1`.
- If an endpoint contract must change, add a new path version (`/v2`).

## API and Quality Expectations

- Keep deterministic response shapes.
- Avoid breaking field names in existing endpoints.
- For search features, include limits and safe defaults.
- Validate with `/docs` and at least one direct endpoint call.

## Security and Abuse Controls

When proposing production changes, include guidance for:
- API keys / auth strategy
- rate limiting at edge/reverse-proxy
- abuse and scraping controls

## Contact

- Maintainer: Abdallah Nangere
- Email: founder@ramadanbot.app
