import os

# Vercel serverless runtime can always write to /tmp.
os.environ.setdefault("ANJAL_DB_PATH", "/tmp/anjal/library.db")

from app.main import app
