from __future__ import annotations

import gzip
import os
import shutil
import threading

from scripts.build_db import main as build_db


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUNDLED_DB_PATH = os.path.join(ROOT_DIR, "data", "index", "library.db")
BUNDLED_DB_GZ_PATH = os.path.join(ROOT_DIR, "data", "index", "library.db.gz")

_BOOTSTRAP_LOCK = threading.Lock()
_INITIALIZED_PATH: str | None = None


def _truthy_env(name: str) -> bool:
    value = os.getenv(name, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _extract_gzip(src_gz: str, dst: str) -> None:
    tmp_dst = f"{dst}.tmp"
    with gzip.open(src_gz, "rb") as fin, open(tmp_dst, "wb") as fout:
        shutil.copyfileobj(fin, fout)
    os.replace(tmp_dst, dst)


def _hydrate_db_file(db_path: str) -> None:
    # 1) Direct bundled DB copy (fastest path when available).
    if os.path.exists(BUNDLED_DB_PATH):
        shutil.copyfile(BUNDLED_DB_PATH, db_path)
        return

    # 2) Bundled compressed snapshot extraction.
    if os.path.exists(BUNDLED_DB_GZ_PATH):
        _extract_gzip(BUNDLED_DB_GZ_PATH, db_path)
        return

    # 3) Optional runtime build fallback (expensive; disabled on Vercel by default).
    if _truthy_env("ANJAL_DISABLE_RUNTIME_DB_BUILD"):
        raise RuntimeError(
            "Database snapshot missing and runtime build disabled. "
            "Provide data/index/library.db.gz or unset ANJAL_DISABLE_RUNTIME_DB_BUILD."
        )

    build_db()
    if not os.path.exists(db_path):
        # build_db writes to ANJAL_DB_PATH; this guard keeps failure explicit.
        raise RuntimeError(f"Database build completed but file missing at {db_path}")


def ensure_db() -> str:
    global _INITIALIZED_PATH

    db_path = os.getenv("ANJAL_DB_PATH", BUNDLED_DB_PATH)
    if _INITIALIZED_PATH == db_path and os.path.exists(db_path):
        return db_path
    if os.path.exists(db_path):
        _INITIALIZED_PATH = db_path
        return db_path

    with _BOOTSTRAP_LOCK:
        if _INITIALIZED_PATH == db_path and os.path.exists(db_path):
            return db_path
        if os.path.exists(db_path):
            _INITIALIZED_PATH = db_path
            return db_path

        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        _hydrate_db_file(db_path)
        _INITIALIZED_PATH = db_path
        return db_path
