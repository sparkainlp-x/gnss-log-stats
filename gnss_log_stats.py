#!/usr/bin/env python3
"""Compute descriptive statistics from an offline GNSS CSV log."""

# Copyright (C) 2026 Spark
# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import Counter
from datetime import datetime, timezone
from typing import TextIO

REQUIRED_COLUMNS = ("timestamp_utc", "latitude_deg", "longitude_deg")
OPTIONAL_NUMERIC_COLUMNS = ("altitude_m", "speed_mps", "satellites", "hdop")
KNOWN_FIX_TYPES = {
    "none", "2d", "3d", "dgps", "rtk_float", "rtk_fixed", "unknown"
}


class LogError(ValueError):
    """Raised when the CSV is malformed or contains invalid GNSS values."""


class Stats:
    """Track count, minimum, mean, and maximum without retaining input rows."""

    def __init__(self) -> None:
        self.count = 0
        self.total = 0.0
        self.minimum: float | None = None
        self.maximum: float | None = None

    def add(self, value: float) -> None:
        self.count += 1
        self.total += value
        self.minimum = value if self.minimum is None else min(self.minimum, value)
        self.maximum = value if self.maximum is None else max(self.maximum, value)

    def as_dict(self) -> dict[str, int | float] | None:
        if not self.count:
            return None
        assert self.minimum is not None and self.maximum is not None
        return {
            "count": self.count,
            "min": self.minimum,
            "mean": self.total / self.count,
            "max": self.maximum,
        }


def _number(value: str, field: str, line: int) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise LogError(f"line {line}: {field} must be numeric") from exc
    if not math.isfinite(number):
        raise LogError(f"line {line}: {field} must be finite")
    return number


def _timestamp(value: str, line: int) -> datetime:
    text = value.strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise LogError(f"line {line}: timestamp_utc must be ISO 8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise LogError(f"line {line}: timestamp_utc must include a UTC timezone")
    return parsed.astimezone(timezone.utc)


def _timestamp_text(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def analyze_stream(stream: TextIO) -> dict[str, object]:
    """Validate a CSV stream and return aggregate GNSS statistics."""
    reader = csv.DictReader(stream)
    headers = reader.fieldnames
    if not headers:
        raise LogError("CSV is missing a header row")
    if len(headers) != len(set(headers)):
        raise LogError("CSV contains duplicate column names")

    missing = [column for column in REQUIRED_COLUMNS if column not in headers]
    if missing:
        raise LogError("CSV is missing required columns: " + ", ".join(missing))

    latitude = Stats()
    longitude = Stats()
    optional_stats = {name: Stats() for name in OPTIONAL_NUMERIC_COLUMNS}
    fix_counts: Counter[str] = Counter()
    first_time: datetime | None = None
    last_time: datetime | None = None
    record_count = 0

    for line, row in enumerate(reader, start=2):
        if row is None or all(value is None or not value.strip() for value in row.values()):
            continue
        if None in row:
            raise LogError(f"line {line}: row has more values than the header")

        timestamp_value = row.get("timestamp_utc") or ""
        lat_value = row.get("latitude_deg") or ""
        lon_value = row.get("longitude_deg") or ""
        if not timestamp_value.strip() or not lat_value.strip() or not lon_value.strip():
            raise LogError(f"line {line}: timestamp_utc, latitude_deg, and longitude_deg are required")

        timestamp = _timestamp(timestamp_value, line)
        lat = _number(lat_value, "latitude_deg", line)
        lon = _number(lon_value, "longitude_deg", line)
        if not -90 <= lat <= 90:
            raise LogError(f"line {line}: latitude_deg must be between -90 and 90")
        if not -180 <= lon <= 180:
            raise LogError(f"line {line}: longitude_deg must be between -180 and 180")

        latitude.add(lat)
        longitude.add(lon)
        first_time = timestamp if first_time is None else min(first_time, timestamp)
        last_time = timestamp if last_time is None else max(last_time, timestamp)
        record_count += 1

        for field in OPTIONAL_NUMERIC_COLUMNS:
            raw = row.get(field)
            if raw is None or not raw.strip():
                continue
            value = _number(raw, field, line)
            if field in ("speed_mps", "satellites", "hdop") and value < 0:
                raise LogError(f"line {line}: {field} cannot be negative")
            if field == "satellites" and not value.is_integer():
                raise LogError(f"line {line}: satellites must be a whole number")
            optional_stats[field].add(value)

        raw_fix = row.get("fix_type")
        if raw_fix and raw_fix.strip():
            normalized = raw_fix.strip().lower().replace("-", "_").replace(" ", "_")
            fix_counts[normalized if normalized in KNOWN_FIX_TYPES else "other"] += 1

    if record_count == 0 or first_time is None or last_time is None:
        raise LogError("CSV contains no GNSS records")

    return {
        "records": record_count,
        "time_utc": {
            "start": _timestamp_text(first_time),
            "end": _timestamp_text(last_time),
            "duration_seconds": (last_time - first_time).total_seconds(),
        },
        "position": {
            "latitude_deg": latitude.as_dict(),
            "longitude_deg": longitude.as_dict(),
        },
        "altitude_m": optional_stats["altitude_m"].as_dict(),
        "speed_mps": optional_stats["speed_mps"].as_dict(),
        "satellites": optional_stats["satellites"].as_dict(),
        "hdop": optional_stats["hdop"].as_dict(),
        "fix_type_counts": dict(sorted(fix_counts.items())),
        "scope_note": "Descriptive statistics only; this output is not physical evidence or an RF finding.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize an approved GNSS CSV log locally; no network access is used."
    )
    parser.add_argument("csv_file", help="path to the input CSV file")
    args = parser.parse_args()

    try:
        with open(args.csv_file, "r", encoding="utf-8-sig", newline="") as stream:
            result = analyze_stream(stream)
    except (OSError, UnicodeError, csv.Error, LogError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(result, indent=2, sort_keys=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
