import os

# Vercel serverless runtime can always write to /tmp.
os.environ.setdefault("ANJAL_DB_PATH", "/tmp/anjal/library.db")
# Runtime DB build from CSV is CPU-expensive; use packaged snapshot extraction.
os.environ.setdefault("ANJAL_DISABLE_RUNTIME_DB_BUILD", "1")

from app.main import app
