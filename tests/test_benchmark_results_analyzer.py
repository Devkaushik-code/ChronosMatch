import json
import tempfile
import unittest
from pathlib import Path

from benchmarks.analyze_results import (
    _number,
    analyze_directory,
    load_result,
    render_report,
    summarize_result,
)


class BenchmarkResultsAnalyzerTests(unittest.TestCase):

    def write_json(self, directory, name, data):
        path = Path(directory) / name
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_matching_engine_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_json(tmp, "results_matching.json", {
                "benchmark": "matching_engine",
                "timestamp_utc": "2026-10-29T10:00:00Z",
                "orders_per_run": 5000,
                "runs": 3,
                "summary": {
                    "mean_throughput_orders_per_second": 150000,
                    "median_p95_latency_us": 10.5,
                },
                "results": [],
            })
            result = load_result(path)
            report = summarize_result(result)
            self.assertEqual(report["kind"], "matching_engine")
            self.assertEqual(report["orders_per_run"], 5000)
            self.assertEqual(report["runs"], 3)

    def test_two_engine_comparison(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_json(tmp, "results_engine.json", {
                "benchmark": "engine_comparison",
                "timestamp_utc": "2026-10-29T10:00:00Z",
                "workload": {"orders_per_run": 20000, "runs": 5},
                "engines": {
                    "python": {"summary": {
                        "mean_throughput_orders_per_second": 170000
                    }},
                    "cython": {"summary": {
                        "mean_throughput_orders_per_second": 160000
                    }},
                },
                "comparison": {
                    "throughput_improvement_percent": -5.88
                },
            })
            report = summarize_result(load_result(path))
            self.assertEqual(report["runs"], 5)
            output = render_report([report], [])
            self.assertIn("-5.88%", output)
            self.assertIn("Cython vs Python", output)

    def test_three_engine_comparison(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_json(tmp, "results_engine_three.json", {
                "benchmark": "engine_comparison",
                "timestamp_utc": "2026-10-29T10:00:00Z",
                "workload": {"orders_per_run": 20000, "runs": 15},
                "engines": {
                    "python": {"summary": {}},
                    "cython_original": {"summary": {}},
                    "cython_optimized": {"summary": {}},
                },
                "comparisons_vs_python": {
                    "cython_optimized": {
                        "throughput_change_percent_vs_python": -3.59
                    }
                },
                "optimized_vs_original_cython": {
                    "throughput_change_percent": 2.48
                },
            })
            report = summarize_result(load_result(path))
            output = render_report([report], [])
            self.assertIn("-3.59%", output)
            self.assertIn("2.48%", output)

    def test_pipeline_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_json(tmp, "results_pipeline.json", {
                "benchmark": "pipeline",
                "timestamp_utc": "2026-10-29T10:00:00Z",
                "orders_per_run": 10000,
                "runs": 3,
                "results": [],
                "summary": {
                    "mean_throughput_orders_per_second": 140000,
                    "mean_pipeline_latency_ms": 70.0,
                },
            })
            report = summarize_result(load_result(path))
            self.assertEqual(report["kind"], "pipeline")
            self.assertEqual(report["orders_per_run"], 10000)

    def test_invalid_json_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "results_broken.json"
            path.write_text("{broken", encoding="utf-8")
            reports, errors = analyze_directory(tmp)
            self.assertEqual(reports, [])
            self.assertEqual(len(errors), 1)

    def test_source_file_is_not_modified(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.write_json(tmp, "results_sample.json", {
                "benchmark": "pipeline",
                "timestamp_utc": "2026-10-29T10:00:00Z",
                "results": [],
                "summary": {},
            })
            original = path.read_bytes()
            analyze_directory(tmp)
            self.assertEqual(path.read_bytes(), original)

    def test_number_rejects_invalid_values(self):
        self.assertIsNone(_number(True))
        self.assertIsNone(_number("123"))
        self.assertIsNone(_number(float("nan")))
        self.assertEqual(_number(123), 123.0)

    def test_missing_directory_raises_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing"
            with self.assertRaises(ValueError):
                analyze_directory(missing)


if __name__ == "__main__":
    unittest.main(verbosity=2)
