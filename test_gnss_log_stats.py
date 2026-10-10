"""Regression tests for GNSS CSV validation and summary output."""

import io
import unittest

from gnss_log_stats import LogError, analyze_stream


class AnalyzeStreamTests(unittest.TestCase):
    def test_summary_and_optional_columns(self):
        source = io.StringIO(
            "timestamp_utc,latitude_deg,longitude_deg,altitude_m,speed_mps,satellites,hdop,fix_type,extra\n"
            "2026-10-09T20:13:16Z,45.0,-73.0,12,2.5,8,0.9,3D,ignored\n"
            "2026-10-09T20:14:16+00:00,45.2,-73.4,14,3.5,10,1.1,custom label,ignored\n"
        )
        result = analyze_stream(source)
        self.assertEqual(result["records"], 2)
        self.assertEqual(result["time_utc"]["duration_seconds"], 60.0)
        self.assertEqual(result["position"]["latitude_deg"]["mean"], 45.1)
        self.assertEqual(result["satellites"]["max"], 10.0)
        self.assertEqual(result["fix_type_counts"], {"3d": 1, "other": 1})
        self.assertNotIn("custom label", str(result))
        self.assertNotIn("ignored", str(result))

    def test_normalizes_utc_z_and_sorts_out_of_order_timestamps(self):
        source = io.StringIO(
            "timestamp_utc,latitude_deg,longitude_deg\n"
            "2026-10-09T20:14:16z,45,-73\n"
            "2026-10-09T20:13:16Z,46,-74\n"
        )
        result = analyze_stream(source)
        self.assertEqual(result["time_utc"]["start"], "2026-10-09T20:13:16Z")
        self.assertEqual(result["time_utc"]["end"], "2026-10-09T20:14:16Z")

    def test_optional_numeric_summaries_are_null_when_absent(self):
        source = io.StringIO(
            "timestamp_utc,latitude_deg,longitude_deg\n"
            "2026-10-09T20:13:16Z,45,-73\n"
        )
        result = analyze_stream(source)
        for field in ("altitude_m", "speed_mps", "satellites", "hdop"):
            with self.subTest(field=field):
                self.assertIsNone(result[field])

    def test_short_row_with_required_values_is_accepted(self):
        source = io.StringIO(
            "timestamp_utc,latitude_deg,longitude_deg,altitude_m,speed_mps\n"
            "2026-10-09T20:13:16Z,45,-73\n"
        )
        result = analyze_stream(source)
        self.assertEqual(result["records"], 1)
        self.assertIsNone(result["altitude_m"])
        self.assertIsNone(result["speed_mps"])

    def test_blank_rows_are_skipped(self):
        source = io.StringIO(
            "timestamp_utc,latitude_deg,longitude_deg\n"
            "2026-10-09T20:13:16Z,45,-73\n"
            ",,\n"
        )
        self.assertEqual(analyze_stream(source)["records"], 1)

    def test_rejects_empty_csv(self):
        with self.assertRaisesRegex(LogError, "missing a header row"):
            analyze_stream(io.StringIO(""))

    def test_rejects_missing_required_column(self):
        with self.assertRaisesRegex(LogError, "missing required columns"):
            analyze_stream(io.StringIO("timestamp_utc,latitude_deg\n"))

    def test_rejects_duplicate_headers(self):
        source = io.StringIO(
            "timestamp_utc,latitude_deg,latitude_deg,longitude_deg\n"
        )
        with self.assertRaisesRegex(LogError, "duplicate column names"):
            analyze_stream(source)

    def test_rejects_no_records(self):
        source = io.StringIO("timestamp_utc,latitude_deg,longitude_deg\n , , \n")
        with self.assertRaisesRegex(LogError, "no GNSS records"):
            analyze_stream(source)

    def test_rejects_naive_timestamp(self):
        source = io.StringIO(
            "timestamp_utc,latitude_deg,longitude_deg\n"
            "2026-10-09T20:13:16,45,-73\n"
        )
        with self.assertRaisesRegex(LogError, "must include a UTC timezone"):
            analyze_stream(source)

    def test_rejects_non_utc_timezone(self):
        source = io.StringIO(
            "timestamp_utc,latitude_deg,longitude_deg\n"
            "2026-10-09T20:13:16-04:00,45,-73\n"
        )
        with self.assertRaisesRegex(LogError, "must include a UTC timezone"):
            analyze_stream(source)

    def test_rejects_invalid_timestamp(self):
        source = io.StringIO(
            "timestamp_utc,latitude_deg,longitude_deg\n"
            "not-a-date,45,-73\n"
        )
        with self.assertRaisesRegex(LogError, "must be ISO 8601"):
            analyze_stream(source)

    def test_rejects_non_numeric_required_coordinate(self):
        source = io.StringIO(
            "timestamp_utc,latitude_deg,longitude_deg\n"
            "2026-10-09T20:13:16Z,north,-73\n"
        )
        with self.assertRaisesRegex(LogError, "latitude_deg must be numeric"):
            analyze_stream(source)

    def test_rejects_non_finite_numbers(self):
        source = io.StringIO(
            "timestamp_utc,latitude_deg,longitude_deg\n"
            "2026-10-09T20:13:16Z,nan,-73\n"
        )
        with self.assertRaisesRegex(LogError, "latitude_deg must be finite"):
            analyze_stream(source)

    def test_rejects_latitude_out_of_range(self):
        source = io.StringIO(
            "timestamp_utc,latitude_deg,longitude_deg\n"
            "2026-10-09T20:13:16Z,91,-73\n"
        )
        with self.assertRaisesRegex(LogError, "latitude_deg must be between"):
            analyze_stream(source)

    def test_rejects_longitude_out_of_range(self):
        source = io.StringIO(
            "timestamp_utc,latitude_deg,longitude_deg\n"
            "2026-10-09T20:13:16Z,45,-181\n"
        )
        with self.assertRaisesRegex(LogError, "longitude_deg must be between"):
            analyze_stream(source)

    def test_rejects_negative_optional_measurement(self):
        source = io.StringIO(
            "timestamp_utc,latitude_deg,longitude_deg,speed_mps\n"
            "2026-10-09T20:13:16Z,45,-73,-0.1\n"
        )
        with self.assertRaisesRegex(LogError, "speed_mps cannot be negative"):
            analyze_stream(source)

    def test_rejects_fractional_satellite_count(self):
        source = io.StringIO(
            "timestamp_utc,latitude_deg,longitude_deg,satellites\n"
            "2026-10-09T20:13:16Z,45,-73,4.5\n"
        )
        with self.assertRaisesRegex(LogError, "satellites must be a whole number"):
            analyze_stream(source)

    def test_rejects_row_with_extra_values(self):
        source = io.StringIO(
            "timestamp_utc,latitude_deg,longitude_deg\n"
            "2026-10-09T20:13:16Z,45,-73,unexpected\n"
        )
        with self.assertRaisesRegex(LogError, "more values than the header"):
            analyze_stream(source)

    def test_rejects_short_row_missing_required_value(self):
        source = io.StringIO(
            "timestamp_utc,latitude_deg,longitude_deg\n"
            "2026-10-09T20:13:16Z,45\n"
        )
        with self.assertRaisesRegex(LogError, "longitude_deg are required"):
            analyze_stream(source)


if __name__ == "__main__":
    unittest.main()
