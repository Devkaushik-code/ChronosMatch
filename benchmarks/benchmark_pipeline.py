"""Benchmark end-to-end pipeline and individual-order processing latency."""

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
from chronosmatch.trading_pipeline import run_trading_pipeline


def percentile(values, percentile_value):
    """Calculate a percentile using linear interpolation."""
    if not 0 <= percentile_value <= 100:
        raise ValueError("percentile_value must be between 0 and 100")

    if not values:
        return 0.0

    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile_value / 100
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower

    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


async def benchmark_pipeline(order_count, batch_size):
    """Measure total pipeline time and individual-order processing time."""
    simulator = MarketSimulator(seed=42)
    order_latencies_ns = []

    start_ns = time.perf_counter_ns()

    result = await run_trading_pipeline(
        count=order_count,
        batch_size=batch_size,
        simulator=simulator,
        order_processing_latencies_ns=order_latencies_ns,
    )

    elapsed_ns = time.perf_counter_ns() - start_ns
    elapsed_seconds = elapsed_ns / 1_000_000_000

    order_latencies_us = [value / 1000 for value in order_latencies_ns]

    return {
        "orders_requested": order_count,
        "orders_processed": result.orders_processed,
        "trades_executed": len(result.trades),
        "total_pipeline_latency_ms": round(elapsed_ns / 1_000_000, 3),
        "average_pipeline_time_per_order_us": round(
            elapsed_ns / result.orders_processed / 1000, 3
        ) if result.orders_processed else 0,
        "throughput_orders_per_second": round(
            result.orders_processed / elapsed_seconds, 2
        ) if elapsed_seconds else 0,
        "individual_order_processing_latency_us": {
            "samples": len(order_latencies_us),
            "mean": round(statistics.mean(order_latencies_us), 3)
            if order_latencies_us else 0,
            "median": round(statistics.median(order_latencies_us), 3)
            if order_latencies_us else 0,
            "p50": round(percentile(order_latencies_us, 50), 3),
            "p95": round(percentile(order_latencies_us, 95), 3),
            "p99": round(percentile(order_latencies_us, 99), 3),
            "maximum": round(max(order_latencies_us), 3)
            if order_latencies_us else 0,
        },
        "best_bid": result.best_bid,
        "best_ask": result.best_ask,
    }


async def run_repeated_benchmark(
    order_count,
    batch_size,
    runs,
    warmup_runs,
):
    """Run warm-ups and collect repeated benchmark measurements."""
    if order_count < 0:
        raise ValueError("order_count cannot be negative")
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    if runs < 1:
        raise ValueError("runs must be at least 1")
    if warmup_runs < 0:
        raise ValueError("warmup_runs cannot be negative")

    for number in range(1, warmup_runs + 1):
        await benchmark_pipeline(order_count, batch_size)
        print(f"Warm-up {number}/{warmup_runs} complete")

    results = []

    for number in range(1, runs + 1):
        result = await benchmark_pipeline(order_count, batch_size)
        result["run"] = number
        results.append(result)

        order_stats = result["individual_order_processing_latency_us"]
        print(
            f"Run {number}/{runs}: "
            f"pipeline={result['total_pipeline_latency_ms']} ms, "
            f"throughput={result['throughput_orders_per_second']} orders/sec, "
            f"order p50={order_stats['p50']} us, "
            f"order p95={order_stats['p95']} us, "
            f"order p99={order_stats['p99']} us"
        )

    pipeline_latencies = [
        result["total_pipeline_latency_ms"] for result in results
    ]
    throughputs = [
        result["throughput_orders_per_second"] for result in results
    ]

    order_means = [
        result["individual_order_processing_latency_us"]["mean"]
        for result in results
    ]
    order_p50s = [
        result["individual_order_processing_latency_us"]["p50"]
        for result in results
    ]
    order_p95s = [
        result["individual_order_processing_latency_us"]["p95"]
        for result in results
    ]
    order_p99s = [
        result["individual_order_processing_latency_us"]["p99"]
        for result in results
    ]

    return {
        "benchmark": "ChronosMatch end-to-end trading pipeline",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python_version": sys.version,
            "python_implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor() or "Not reported",
        },
        "orders_per_run": order_count,
        "batch_size": batch_size,
        "runs": runs,
        "warmup_runs": warmup_runs,
        "results": results,
        "summary": {
            "mean_pipeline_latency_ms": round(
                statistics.mean(pipeline_latencies), 3
            ),
            "median_pipeline_latency_ms": round(
                statistics.median(pipeline_latencies), 3
            ),
            "p50_pipeline_latency_ms": round(
                percentile(pipeline_latencies, 50), 3
            ),
            "p95_pipeline_latency_ms": round(
                percentile(pipeline_latencies, 95), 3
            ),
            "p99_pipeline_latency_ms": round(
                percentile(pipeline_latencies, 99), 3
            ),
            "mean_throughput_orders_per_second": round(
                statistics.mean(throughputs), 2
            ),
            "mean_individual_order_processing_latency_us": round(
                statistics.mean(order_means), 3
            ),
            "median_run_order_p50_latency_us": round(
                statistics.median(order_p50s), 3
            ),
            "median_run_order_p95_latency_us": round(
                statistics.median(order_p95s), 3
            ),
            "median_run_order_p99_latency_us": round(
                statistics.median(order_p99s), 3
            ),
        },
        "notes": [
            "Total pipeline time includes order generation and matching.",
            "Individual-order processing latency starts after an order is yielded "
            "by the simulator and ends after matching and any trade persistence.",
            "Individual-order latency excludes simulator generation and waiting time.",
            "The summary's order percentiles are medians of the per-run percentiles.",
            "SQLite persistence is not included unless a ledger is supplied.",
            "Multiprocess IPC is not included.",
            "Results depend on the runtime environment and system load.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark the ChronosMatch trading pipeline."
    )
    parser.add_argument("--orders", type=int, default=10000)
    parser.add_argument("--batch-size", type=int, default=1000)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--warmup-runs", type=int, default=1)
    parser.add_argument(
        "--output",
        default="benchmarks/results_pipeline.json",
    )
    args = parser.parse_args()

    if args.orders < 0:
        parser.error("--orders cannot be negative")
    if args.batch_size <= 0:
        parser.error("--batch-size must be positive")
    if args.runs < 1:
        parser.error("--runs must be at least 1")
    if args.warmup_runs < 0:
        parser.error("--warmup-runs cannot be negative")

    report = asyncio.run(
        run_repeated_benchmark(
            args.orders,
            args.batch_size,
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
