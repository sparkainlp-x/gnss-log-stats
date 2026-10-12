# GNSS Log Stats

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23307945.svg)](https://doi.org/10.5281/zenodo.23307945)
[![Tests](https://github.com/sparkainlp-x/gnss-log-stats/actions/workflows/tests.yml/badge.svg)](https://github.com/sparkainlp-x/gnss-log-stats/actions/workflows/tests.yml)
[![License: AGPL-3.0-only](https://img.shields.io/badge/License-AGPL--3.0--only-blue.svg)](https://www.gnu.org/licenses/agpl-3.0.html)

A small, dependency-free command-line tool for summarizing an **approved GNSS CSV log** as JSON. It reports descriptive statistics only; it does not infer signal conditions, validate a receiver, or establish physical evidence.

## Highlights

- Runs locally and uses only the Python standard library; the program makes no network requests.
- Streams the CSV one record at a time and emits aggregate results, not individual records.
- Validates UTC timestamps, coordinate ranges, and optional numeric fields.
- Omits arbitrary input text and unrecognized fix labels from its output.
- Includes automated tests and a GitHub Actions test workflow.

> GNSS logs can reveal sensitive location history. Review the input before use, protect generated output, and do not commit real logs to this repository. The program itself does not transmit data, but your operating system, terminal, backups, or any output redirection remain outside its control.

## Requirements

- Python 3.10 or newer
- A UTF-8 CSV file with a header row and at least one GNSS record

No runtime third-party dependencies are required.

## Quick start

Run directly from a checkout:

```bash
python3 gnss_log_stats.py /path/to/approved_log.csv
```

Or install the command from the repository:

```bash
python3 -m pip install .
gnss-log-stats /path/to/approved_log.csv
```

On success, formatted JSON is written to standard output. Invalid input or file errors are reported on standard error and return exit status `2`; success returns `0`. Use shell redirection only if you intend to save the summary:

```bash
python3 gnss_log_stats.py /path/to/approved_log.csv > summary.json
```

## CSV format

Required columns:

| Column | Format | Validation |
| --- | --- | --- |
| `timestamp_utc` | ISO 8601 timestamp | Must explicitly identify UTC, for example `2026-10-09T20:13:16Z` or `2026-10-09T20:13:16+00:00`. Naive timestamps and non-zero offsets are rejected. |
| `latitude_deg` | Finite number | Inclusive range `-90` to `90`. |
| `longitude_deg` | Finite number | Inclusive range `-180` to `180`. |

Optional columns may be omitted or left blank:

| Column | Format | Output |
| --- | --- | --- |
| `altitude_m` | Finite number | Count, minimum, mean, and maximum. |
| `speed_mps` | Finite, non-negative number | Count, minimum, mean, and maximum. |
| `satellites` | Non-negative whole number | Count, minimum, mean, and maximum. |
| `hdop` | Finite, non-negative number | Count, minimum, mean, and maximum. |
| `fix_type` | Text | Counts for `none`, `2d`, `3d`, `dgps`, `rtk_float`, `rtk_fixed`, `unknown`, or `other`. Hyphens and spaces are normalized to underscores before recognition. Original unrecognized labels are not emitted. |

Additional columns are ignored. Completely blank rows are skipped. Missing required values and rows with extra values produce an error. Short rows that contain all required values are accepted; absent optional trailing fields are treated as blank. Duplicate column names, malformed CSV, invalid numbers, and out-of-range coordinates also produce an error. If an optional numeric field has no values, its summary is `null`.

## JSON summary

The output contains:

- `records`: number of accepted GNSS records
- `time_utc`: earliest and latest timestamps and their elapsed duration in seconds
- `position`: latitude and longitude count/minimum/mean/maximum
- Optional numeric summaries for altitude, speed, satellite count, and HDOP
- `fix_type_counts`: sorted counts of recognized fix categories
- `scope_note`: a reminder that the result is descriptive only

Rows may arrive out of chronological order; the reported start and end are the earliest and latest valid timestamps.

## Development

Run the test suite with Python's built-in test runner:

```bash
python3 -m unittest -v
```

The GitHub Actions workflow runs the same suite across supported Python versions. Tests use in-memory sample data; no real GNSS logs are needed.

## License

This project is licensed under the **GNU Affero General Public License, version 3 only (AGPL-3.0-only)**. See [`LICENSE`](LICENSE) for the complete terms. The software is provided without warranty; refer to the license for details.

## Cite

Concept DOI (all versions): [10.5281/zenodo.23307945](https://doi.org/10.5281/zenodo.23307945). v0.1.0: [10.5281/zenodo.23307946](https://doi.org/10.5281/zenodo.23307946). See [CITATION.cff](CITATION.cff).
