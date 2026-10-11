"""Tests for the ChronosMatch benchmark utilities."""

import asyncio
import unittest

from benchmarks.benchmark_trading import (
    percentile,
    run_repeated_benchmark,
)


class TestPercentile(unittest.TestCase):
    def test_median_of_even_length_list(self):
        self.assertEqual(percentile([10, 20, 30, 40], 50), 25)

    def test_p95_uses_linear_interpolation(self):
        self.assertEqual(percentile([10, 20, 30, 40], 95), 38.5)

    def test_single_value(self):
        self.assertEqual(percentile([42], 99), 42)

    def test_empty_values(self):
        self.assertEqual(percentile([], 50), 0)

    def test_zero_percentile(self):
        self.assertEqual(percentile([10, 20, 30], 0), 10)

    def test_hundred_percentile(self):
        self.assertEqual(percentile([10, 20, 30], 100), 30)

    def test_unsorted_values(self):
        self.assertEqual(percentile([40, 10, 30, 20], 50), 25)

    def test_invalid_percentile(self):
        for value in (-1, 101):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    percentile([10, 20, 30], value)


class TestRepeatedBenchmarkValidation(unittest.TestCase):
    def test_zero_runs_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "runs must be at least 1"):
            asyncio.run(run_repeated_benchmark(100, 0))

    def test_negative_order_count_is_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "order_count cannot be negative",
        ):
            asyncio.run(run_repeated_benchmark(-1, 1))

    def test_negative_warmup_runs_is_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "warmup_runs cannot be negative",
        ):
            asyncio.run(run_repeated_benchmark(100, 1, -1))


if __name__ == "__main__":
    unittest.main(verbosity=2)
