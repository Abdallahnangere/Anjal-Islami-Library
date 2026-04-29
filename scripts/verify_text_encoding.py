from __future__ import annotations

import argparse
import os
import sqlite3


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB = os.path.join(ROOT, "data", "index", "library.db")
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
    "\ufeff",
)


def _get_tables(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name NOT LIKE 'sqlite_%'
          AND name NOT LIKE '%_fts%'
          AND name NOT LIKE '%_idx%'
        ORDER BY name
        """
    ).fetchall()
    return [r[0] for r in rows]


def _get_text_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
    text_cols: list[str] = []
    for _, name, col_type, *_ in cols:
        if isinstance(col_type, str) and "TEXT" in col_type.upper():
            text_cols.append(name)
    return text_cols


def _make_where() -> tuple[str, list[str]]:
    clauses = [f"INSTR({{col}}, ?) > 0" for _ in MOJIBAKE_MARKERS]
    return " OR ".join(clauses), list(MOJIBAKE_MARKERS)


def scan(db_path: str, sample_limit: int) -> int:
    conn = sqlite3.connect(db_path)
    where_template, params = _make_where()
    total_hits = 0
    table_count = 0
    col_count = 0
    issues: list[tuple[str, str, int, list[tuple]]] = []

    for table in _get_tables(conn):
        text_cols = _get_text_columns(conn, table)
        if not text_cols:
            continue
        table_count += 1
        for col in text_cols:
            col_count += 1
            where = where_template.format(col=col)
            count_sql = f"SELECT COUNT(*) FROM {table} WHERE {where}"
            count = conn.execute(count_sql, params).fetchone()[0]
            if count <= 0:
                continue
            total_hits += count
            sample_sql = f"SELECT rowid, {col} FROM {table} WHERE {where} LIMIT ?"
            sample_rows = conn.execute(sample_sql, params + [sample_limit]).fetchall()
            issues.append((table, col, count, sample_rows))

    print(f"DB: {db_path}")
    print(f"tables_scanned: {table_count}")
    print(f"text_columns_scanned: {col_count}")
    print(f"columns_with_issues: {len(issues)}")
    print(f"total_suspect_rows: {total_hits}")

    if not issues:
        print("No mojibake markers detected.")
        conn.close()
        return 0

    print("\nSample problematic rows:")
    for table, col, count, samples in issues:
        print(f"\n- {table}.{col}: {count} suspect rows")
        for rowid, value in samples:
            preview = (value or "").replace("\n", " ").strip()
            if len(preview) > 140:
                preview = preview[:137] + "..."
            print(f"  rowid={rowid}: {preview}")

    conn.close()
    return 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scan SQLite text columns for common mojibake markers."
    )
    parser.add_argument("--db", default=DEFAULT_DB, help="Path to SQLite DB file.")
    parser.add_argument(
        "--sample-limit",
        type=int,
        default=5,
        help="How many sample rows to print per problematic column.",
    )
    args = parser.parse_args()
    raise SystemExit(scan(args.db, args.sample_limit))


if __name__ == "__main__":
    main()
