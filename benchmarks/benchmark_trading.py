"""Repeatable performance benchmark for ChronosMatch."""

import argparse
import asyncio
import json
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from chronosmatch.market_simulator import MarketSimulator
from chronosmatch.matching_engine import MatchingEngine


def percentile(values, percentile_value):
    """Calculate a percentile using linear interpolation."""
    if not 0 <= percentile_value <= 100:
        raise ValueError("percentile_value must be between 0 and 100")

    if not values:
        return 0

    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile_value / 100
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower

    return (
        ordered[lower] * (1 - fraction)
        + ordered[upper] * fraction
    )


async def benchmark(order_count: int = 10_000) -> dict:
    """Benchmark order generation and matching."""
    if order_count < 0:
        raise ValueError("order_count cannot be negative")

    simulator = MarketSimulator(seed=42)
    engine = MatchingEngine()
    latencies_ns = []
    processed = 0

    start_ns = time.perf_counter_ns()

    async for order_id, price, quantity in simulator.generate_orders(
        count=order_count,
        batch_size=1000,
    ):
        side = "BUY" if order_id % 2 == 1 else "SELL"

        order_start_ns = time.perf_counter_ns()
        engine.submit_order(order_id, side, price, quantity)
        latencies_ns.append(time.perf_counter_ns() - order_start_ns)
        processed += 1

    elapsed_ns = time.perf_counter_ns() - start_ns
    elapsed_seconds = elapsed_ns / 1_000_000_000

    return {
        "orders_requested": order_count,
        "orders_processed": processed,
        "trades_executed": len(engine.trades),
        "elapsed_ms": round(elapsed_ns / 1_000_000, 3),
        "throughput_orders_per_second": round(
            processed / elapsed_seconds, 2
        ) if elapsed_seconds else 0,
        "average_matching_latency_us": round(
            statistics.mean(latencies_ns) / 1000, 3
        ) if latencies_ns else 0,
        "p50_latency_us": round(
            percentile(latencies_ns, 50) / 1000, 3
        ),
        "p95_latency_us": round(
            percentile(latencies_ns, 95) / 1000, 3
        ),
        "p99_latency_us": round(
            percentile(latencies_ns, 99) / 1000, 3
        ),
    }


async def run_repeated_benchmark(
    order_count: int,
    runs: int,
    warmup_runs: int = 1,
) -> dict:
    """Run warm-ups, then collect measured benchmark results."""
    if order_count < 0:
        raise ValueError("order_count cannot be negative")

    if runs < 1:
        raise ValueError("runs must be at least 1")

    if warmup_runs < 0:
        raise ValueError("warmup_runs cannot be negative")

    for warmup_number in range(1, warmup_runs + 1):
        await benchmark(order_count)
        print(f"Warm-up {warmup_number}/{warmup_runs} complete")

    results = []

    for run_number in range(1, runs + 1):
        result = await benchmark(order_count)
        result["run"] = run_number
        results.append(result)

        print(
            f"Run {run_number}/{runs}: "
            f"{result['throughput_orders_per_second']} orders/sec"
        )

    throughputs = [
        result["throughput_orders_per_second"]
        for result in results
    ]

    return {
        "benchmark": "ChronosMatch Python matching engine",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python_version": sys.version,
            "python_implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor() or "Not reported",
        },
        "orders_per_run": order_count,
        "runs": runs,
        "warmup_runs": warmup_runs,
        "percentile_method": "Linear interpolation (inclusive endpoints)",
        "results": results,
        "summary": {
            "mean_throughput_orders_per_second": round(
                statistics.mean(throughputs), 2
            ),
            "median_throughput_orders_per_second": round(
                statistics.median(throughputs), 2
            ),
            "min_throughput_orders_per_second": min(throughputs),
            "max_throughput_orders_per_second": max(throughputs),
            "stdev_throughput_orders_per_second": round(
                statistics.pstdev(throughputs), 2
            ),
        },
        "notes": [
            "Single-process Python benchmark.",
            "Warm-up runs are excluded from reported results.",
            "Throughput includes order generation and matching.",
            "Matching latency measures submit_order only.",
            "Percentiles use linear interpolation.",
            "Does not measure mmap IPC or prove zero-copy communication.",
            "Results depend on the runtime environment and system load.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark the ChronosMatch Python matching engine."
    )
    parser.add_argument("--orders", type=int, default=100_000)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--warmup-runs", type=int, default=1)
    parser.add_argument(
        "--output",
        default="benchmarks/results.json",
    )
    args = parser.parse_args()

    if args.orders < 0:
        parser.error("--orders cannot be negative")

    if args.runs < 1:
        parser.error("--runs must be at least 1")

    if args.warmup_runs < 0:
        parser.error("--warmup-runs cannot be negative")

    report = asyncio.run(
        run_repeated_benchmark(
            args.orders,
            args.runs,
            args.warmup_runs,
        )
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    print("\nSummary:")
    print(json.dumps(report["summary"], indent=2))
    print(f"\nFull report saved to: {output_path}")


if __name__ == "__main__":
    main()
