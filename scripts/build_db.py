from __future__ import annotations

import csv
import os
import sqlite3
import unicodedata
from dataclasses import dataclass


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "source")
DEFAULT_DB = os.path.join(ROOT, "data", "index", "library.db")
DB = os.getenv("ANJAL_DB_PATH", DEFAULT_DB)
IDX_DIR = os.path.dirname(DB)

MOJIBAKE_MARKERS = (
    "Ã",
    "Â",
    "â€™",
    "â€œ",
    "â€\x9d",
    "â€",
    "ï»¿",
    "Ð",
    "Ñ",
)


@dataclass
class NormalizationStats:
    fields_processed: int = 0
    bom_stripped: int = 0
    nfc_normalized: int = 0
    mojibake_repaired: int = 0


def _looks_like_mojibake(value: str) -> bool:
    return any(marker in value for marker in MOJIBAKE_MARKERS)


def _safe_repair_mojibake(value: str) -> tuple[str, bool]:
    if not value or not _looks_like_mojibake(value):
        return value, False
    for codec in ("latin-1", "cp1252"):
        try:
            repaired = value.encode(codec).decode("utf-8")
        except UnicodeError:
            continue
        if repaired != value and not _looks_like_mojibake(repaired):
            return repaired, True
    return value, False


def clean_text(value: str, stats: NormalizationStats) -> str:
    if value is None:
        return value
    stats.fields_processed += 1
    s = value.strip()
    if "\ufeff" in s:
        s = s.replace("\ufeff", "")
        stats.bom_stripped += 1
    repaired, repaired_changed = _safe_repair_mojibake(s)
    if repaired_changed:
        s = repaired
        stats.mojibake_repaired += 1
    nfc = unicodedata.normalize("NFC", s)
    if nfc != s:
        stats.nfc_normalized += 1
    s = nfc.strip()
    if "\ufeff" in s:
        s = s.replace("\ufeff", "")
        stats.bom_stripped += 1
    return s


def init_db(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.executescript(
        """
        DROP TABLE IF EXISTS metadata;
        DROP TABLE IF EXISTS quran_surahs;
        DROP TABLE IF EXISTS quran_ayahs;
        DROP TABLE IF EXISTS hadith_entries;
        DROP TABLE IF EXISTS hadith_collections;
        DROP TABLE IF EXISTS hijri_dates;
        DROP TABLE IF EXISTS prayer_times;
        DROP TABLE IF EXISTS quran_fts;
        DROP TABLE IF EXISTS hadith_fts;

        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE quran_surahs (
            surah_number INTEGER PRIMARY KEY,
            name_arabic TEXT NOT NULL,
            name_english TEXT NOT NULL,
            name_english_translation TEXT NOT NULL,
            revelation_type TEXT NOT NULL,
            ayah_count INTEGER NOT NULL
        );

        CREATE TABLE quran_ayahs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ayah_global_number INTEGER NOT NULL,
            surah_number INTEGER NOT NULL,
            ayah_number_in_surah INTEGER NOT NULL,
            juz INTEGER,
            manzil INTEGER,
            page INTEGER,
            ruku INTEGER,
            hizb_quarter INTEGER,
            sajda TEXT,
            text_arabic_uthmani TEXT NOT NULL,
            text_english_sahih TEXT NOT NULL
        );

        CREATE TABLE hadith_collections (
            collection_key TEXT PRIMARY KEY,
            collection_name TEXT NOT NULL,
            arabic_edition TEXT,
            english_edition TEXT,
            arabic_count INTEGER,
            english_count INTEGER,
            merged_count INTEGER,
            arabic_author TEXT,
            english_author TEXT
        );

        CREATE TABLE hadith_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            collection_key TEXT NOT NULL,
            collection_name TEXT NOT NULL,
            hadith_number INTEGER NOT NULL,
            arabic_number TEXT,
            book_number TEXT,
            hadith_ref_number TEXT,
            text_arabic TEXT NOT NULL,
            text_english TEXT NOT NULL,
            grades TEXT
        );

        CREATE TABLE hijri_dates (
            rjd INTEGER PRIMARY KEY,
            hijri_year INTEGER NOT NULL,
            hijri_month INTEGER NOT NULL,
            hijri_day INTEGER NOT NULL,
            hijri_iso TEXT NOT NULL,
            gregorian_year INTEGER NOT NULL,
            gregorian_month INTEGER NOT NULL,
            gregorian_day INTEGER NOT NULL,
            gregorian_iso TEXT NOT NULL
        );

        CREATE TABLE prayer_times (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_gregorian TEXT NOT NULL,
            date_hijri TEXT NOT NULL,
            country TEXT NOT NULL,
            city TEXT NOT NULL,
            timezone TEXT,
            method TEXT,
            fajr TEXT,
            sunrise TEXT,
            dhuhr TEXT,
            asr TEXT,
            maghrib TEXT,
            isha TEXT
        );

        CREATE INDEX idx_quran_ref ON quran_ayahs(surah_number, ayah_number_in_surah);
        CREATE INDEX idx_hadith_ref ON hadith_entries(collection_key, hadith_number);
        CREATE INDEX idx_hijri_greg ON hijri_dates(gregorian_iso);
        CREATE INDEX idx_hijri_hijri ON hijri_dates(hijri_year, hijri_month, hijri_day);
        CREATE INDEX idx_prayer_country_city ON prayer_times(country, city);
        """
    )
    conn.commit()


def load_csv(
    conn: sqlite3.Connection, filename: str, table: str, normalization: NormalizationStats
) -> int:
    path = os.path.join(SRC, filename)
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows:
        return 0
    cols = list(rows[0].keys())
    placeholders = ", ".join(["?"] * len(cols))
    sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"
    data = [
        tuple(clean_text(r[c], normalization) if isinstance(r[c], str) else r[c] for c in cols)
        for r in rows
    ]
    conn.executemany(sql, data)
    conn.commit()
    return len(rows)


def build_fts(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE VIRTUAL TABLE quran_fts USING fts5(
          text_arabic_uthmani,
          text_english_sahih,
          content='quran_ayahs',
          content_rowid='id',
          tokenize='unicode61 remove_diacritics 2'
        );
        INSERT INTO quran_fts(rowid, text_arabic_uthmani, text_english_sahih)
        SELECT id, text_arabic_uthmani, text_english_sahih FROM quran_ayahs;

        CREATE VIRTUAL TABLE hadith_fts USING fts5(
          text_arabic,
          text_english,
          content='hadith_entries',
          content_rowid='id',
          tokenize='unicode61 remove_diacritics 2'
        );
        INSERT INTO hadith_fts(rowid, text_arabic, text_english)
        SELECT id, text_arabic, text_english FROM hadith_entries;
        """
    )
    conn.commit()


def add_metadata(
    conn: sqlite3.Connection, stats: dict[str, int], normalization: NormalizationStats
) -> None:
    rows = [
        ("project_name", clean_text("Anjal Islamic Library API", normalization)),
        ("api_version", clean_text("v1", normalization)),
        ("author", clean_text("Abdallah Nangere", normalization)),
        ("contact_email", clean_text("founder@ramadanbot.app", normalization)),
        ("contact_phone", clean_text("+2348164135836", normalization)),
        ("quran_rows", clean_text(str(stats["quran_ayahs"]), normalization)),
        ("hadith_rows", clean_text(str(stats["hadith_entries"]), normalization)),
        ("hijri_rows", clean_text(str(stats["hijri_dates"]), normalization)),
        ("prayer_rows", clean_text(str(stats["prayer_times"]), normalization)),
    ]
    conn.executemany("INSERT INTO metadata (key, value) VALUES (?, ?)", rows)
    conn.commit()


def main() -> None:
    os.makedirs(IDX_DIR, exist_ok=True)
    conn = sqlite3.connect(DB)

    normalization = NormalizationStats()
    init_db(conn)
    counts: dict[str, int] = {}
    counts["quran_surahs"] = load_csv(conn, "surahs_ar_en.csv", "quran_surahs", normalization)
    counts["quran_ayahs"] = load_csv(conn, "ayahs_ar_en.csv", "quran_ayahs", normalization)
    counts["hadith_collections"] = load_csv(
        conn, "collections_summary.csv", "hadith_collections", normalization
    )
    counts["hadith_entries"] = load_csv(
        conn, "hadith_all_collections_ar_en.csv", "hadith_entries", normalization
    )
    counts["hijri_dates"] = load_csv(conn, "ummalqura_1343_1500.csv", "hijri_dates", normalization)
    counts["prayer_times"] = load_csv(
        conn, "prayer_times_selected_plus_all_nigeria.csv", "prayer_times", normalization
    )
    build_fts(conn)
    add_metadata(conn, counts, normalization)
    conn.close()
    print("Database built:", DB)
    for k, v in counts.items():
        print(f"{k}: {v}")
    print("normalization.fields_processed:", normalization.fields_processed)
    print("normalization.bom_stripped:", normalization.bom_stripped)
    print("normalization.nfc_normalized:", normalization.nfc_normalized)
    print("normalization.mojibake_repaired:", normalization.mojibake_repaired)


if __name__ == "__main__":
    main()
