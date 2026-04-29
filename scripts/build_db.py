from __future__ import annotations

import csv
import os
import sqlite3


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "source")
IDX_DIR = os.path.join(ROOT, "data", "index")
DB = os.path.join(IDX_DIR, "library.db")


def clean_text(value: str) -> str:
    if value is None:
        return value
    s = value.replace("\ufeff", "").strip()
    # Heuristic mojibake repair for UTF-8 text decoded as Latin-1/CP1252.
    if any(ch in s for ch in ("Ø", "Ù", "ï»¿")):
        try:
            repaired = s.encode("latin-1").decode("utf-8")
            s = repaired.replace("\ufeff", "").strip()
        except Exception:
            pass
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


def load_csv(conn: sqlite3.Connection, filename: str, table: str) -> int:
    path = os.path.join(SRC, filename)
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows:
        return 0
    cols = list(rows[0].keys())
    placeholders = ", ".join(["?"] * len(cols))
    sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"
    data = [tuple(clean_text(r[c]) if isinstance(r[c], str) else r[c] for c in cols) for r in rows]
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


def add_metadata(conn: sqlite3.Connection, stats: dict[str, int]) -> None:
    rows = [
        ("project_name", "Anjal Islamic Library API"),
        ("api_version", "v1"),
        ("author", "Abdallah Nangere"),
        ("contact_email", "founder@ramadanbot.app"),
        ("contact_phone", "+2348164135836"),
        ("quran_rows", str(stats["quran_ayahs"])),
        ("hadith_rows", str(stats["hadith_entries"])),
        ("hijri_rows", str(stats["hijri_dates"])),
        ("prayer_rows", str(stats["prayer_times"])),
    ]
    conn.executemany("INSERT INTO metadata (key, value) VALUES (?, ?)", rows)
    conn.commit()


def main() -> None:
    os.makedirs(IDX_DIR, exist_ok=True)
    conn = sqlite3.connect(DB)

    init_db(conn)
    counts: dict[str, int] = {}
    counts["quran_surahs"] = load_csv(conn, "surahs_ar_en.csv", "quran_surahs")
    counts["quran_ayahs"] = load_csv(conn, "ayahs_ar_en.csv", "quran_ayahs")
    counts["hadith_collections"] = load_csv(conn, "collections_summary.csv", "hadith_collections")
    counts["hadith_entries"] = load_csv(conn, "hadith_all_collections_ar_en.csv", "hadith_entries")
    counts["hijri_dates"] = load_csv(conn, "ummalqura_1343_1500.csv", "hijri_dates")
    counts["prayer_times"] = load_csv(
        conn, "prayer_times_selected_plus_all_nigeria.csv", "prayer_times"
    )
    build_fts(conn)
    add_metadata(conn, counts)
    conn.close()
    print("Database built:", DB)
    for k, v in counts.items():
        print(f"{k}: {v}")


if __name__ == "__main__":
    main()
