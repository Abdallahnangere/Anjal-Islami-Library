from __future__ import annotations

import os
import shutil

from scripts.build_db import DB as DEFAULT_DB_PATH
from scripts.build_db import main as build_db


def ensure_db() -> str:
    db_path = os.getenv("ANJAL_DB_PATH", DEFAULT_DB_PATH)
    db_dir = os.path.dirname(db_path)
    os.makedirs(db_dir, exist_ok=True)

    if os.path.exists(db_path):
        return db_path

    # If default db already exists, copy it to target path.
    if db_path != DEFAULT_DB_PATH and os.path.exists(DEFAULT_DB_PATH):
        shutil.copyfile(DEFAULT_DB_PATH, db_path)
        return db_path

    # Build from source CSVs.
    build_db()

    if db_path != DEFAULT_DB_PATH and os.path.exists(DEFAULT_DB_PATH):
        shutil.copyfile(DEFAULT_DB_PATH, db_path)

    return db_path
