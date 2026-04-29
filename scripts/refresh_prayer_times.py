from __future__ import annotations

import argparse
import csv
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_CONFIG = os.path.join(ROOT, "scripts", "prayer_targets.json")
DEFAULT_OUTPUT = os.path.join(ROOT, "data", "source", "prayer_times_selected_plus_all_nigeria.csv")
DEFAULT_REPORT = os.path.join(ROOT, "data", "source", "prayer_refresh_report.json")
API_URL = "https://api.aladhan.com/v1/timingsByCity"
CSV_FIELDS = [
    "date_gregorian",
    "date_hijri",
    "country",
    "city",
    "timezone",
    "method",
    "fajr",
    "sunrise",
    "dhuhr",
    "asr",
    "maghrib",
    "isha",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh prayer times from AlAdhan.")
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG,
        help="Path to countries/cities JSON config (default: scripts/prayer_targets.json)",
    )
    parser.add_argument(
        "--date",
        default=datetime.now().strftime("%d-%m-%Y"),
        help="Gregorian date in dd-mm-yyyy format (default: today)",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help="Output CSV path (default: data/source/prayer_times_selected_plus_all_nigeria.csv)",
    )
    parser.add_argument(
        "--report",
        default=DEFAULT_REPORT,
        help="Output report JSON path (default: data/source/prayer_refresh_report.json)",
    )
    parser.add_argument("--max-retries", type=int, default=4, help="Retry attempts for transient failures.")
    parser.add_argument("--initial-backoff", type=float, default=1.0, help="Initial backoff in seconds.")
    return parser.parse_args()


def validate_date(value: str) -> str:
    datetime.strptime(value, "%d-%m-%Y")
    return value


def load_config(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if "targets" not in data or not isinstance(data["targets"], list):
        raise ValueError("Config must include a 'targets' list.")
    return data


def normalize_time(value: str) -> str:
    if not value:
        return ""
    return value.split(" ", 1)[0].strip()


def build_row(country: str, city: str, payload: dict[str, Any]) -> dict[str, str]:
    data = payload.get("data") or {}
    timings = data.get("timings") or {}
    date_info = data.get("date") or {}
    hijri = date_info.get("hijri") or {}
    gregorian = date_info.get("gregorian") or {}
    meta = data.get("meta") or {}
    method = (meta.get("method") or {}).get("name", "")

    return {
        "date_gregorian": gregorian.get("date", ""),
        "date_hijri": hijri.get("date", ""),
        "country": country,
        "city": city,
        "timezone": meta.get("timezone", ""),
        "method": method,
        "fajr": normalize_time(timings.get("Fajr", "")),
        "sunrise": normalize_time(timings.get("Sunrise", "")),
        "dhuhr": normalize_time(timings.get("Dhuhr", "")),
        "asr": normalize_time(timings.get("Asr", "")),
        "maghrib": normalize_time(timings.get("Maghrib", "")),
        "isha": normalize_time(timings.get("Isha", "")),
    }


def fetch_timings(
    city: str,
    country: str,
    target_date: str,
    method: int,
    timeout_seconds: float,
    max_retries: int,
    initial_backoff: float,
) -> tuple[dict[str, Any] | None, str | None, int]:
    params = urllib.parse.urlencode(
        {
            "city": city,
            "country": country,
            "date": target_date,
            "method": method,
        }
    )
    url = f"{API_URL}?{params}"
    retries = 0
    backoff = initial_backoff
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "anjal-prayer-refresh/1.0"})
            with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
                if response.status != 200:
                    raise urllib.error.HTTPError(
                        url=url,
                        code=response.status,
                        msg=f"Unexpected status: {response.status}",
                        hdrs=response.headers,
                        fp=None,
                    )
                payload = json.loads(response.read().decode("utf-8"))

            if payload.get("code") != 200 or "data" not in payload:
                raise ValueError(f"Unexpected API payload code={payload.get('code')}")
            return payload, None, retries
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            is_http_error = isinstance(exc, urllib.error.HTTPError)
            transient_http = is_http_error and exc.code in (408, 425, 429, 500, 502, 503, 504)
            transient_url = isinstance(exc, urllib.error.URLError)
            transient = transient_http or transient_url or isinstance(exc, TimeoutError)
            last_error = str(exc)

            if attempt >= max_retries or not transient:
                return None, last_error, retries

            retries += 1
            time.sleep(backoff)
            backoff *= 2

    return None, last_error or "Unknown failure", retries


def write_csv(path: str, rows: list[dict[str, str]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sorted_rows = sorted(rows, key=lambda r: (r["country"].lower(), r["city"].lower()))
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(sorted_rows)


def write_report(path: str, report: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)


def main() -> None:
    args = parse_args()
    target_date = validate_date(args.date)
    config = load_config(args.config)

    method = int(config.get("method", 2))
    timeout_seconds = float(config.get("timeout_seconds", 20))
    targets = config["targets"]

    rows: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []
    total_retries = 0
    requested = 0

    for target in targets:
        country = target.get("country")
        cities = target.get("cities", [])
        if not country or not isinstance(cities, list):
            continue
        for city in cities:
            requested += 1
            payload, error, retries = fetch_timings(
                city=city,
                country=country,
                target_date=target_date,
                method=method,
                timeout_seconds=timeout_seconds,
                max_retries=args.max_retries,
                initial_backoff=args.initial_backoff,
            )
            total_retries += retries
            if payload is None:
                failures.append({"country": country, "city": city, "error": error or "Unknown error"})
                continue
            rows.append(build_row(country=country, city=city, payload=payload))

    write_csv(args.output, rows)
    report = {
        "run_at_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target_date": target_date,
        "config_path": os.path.abspath(args.config),
        "output_csv": os.path.abspath(args.output),
        "method": method,
        "requested": requested,
        "succeeded": len(rows),
        "failed": len(failures),
        "total_retries": total_retries,
        "failures": failures,
    }
    write_report(args.report, report)

    print(f"Wrote CSV: {args.output}")
    print(f"Wrote report: {args.report}")
    print(
        f"Requested={report['requested']} Succeeded={report['succeeded']} "
        f"Failed={report['failed']} Retries={report['total_retries']}"
    )


if __name__ == "__main__":
    main()
