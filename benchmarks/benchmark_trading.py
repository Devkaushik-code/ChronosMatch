"""Repeatable performance benchmark for ChronosMatch."""

import argparse
import asyncio
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from chronosmatch.market_simulator import MarketSimulator
from chronosmatch.matching_engine import MatchingEngine


def percentile(values, percentile_value):
    if not values:
        return 0

    index = int((len(values) - 1) * percentile_value / 100)
    return values[index]


async def benchmark(order_count: int = 10_000) -> dict:
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
    sorted_latencies = sorted(latencies_ns)
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
            percentile(sorted_latencies, 50) / 1000, 3
        ),
        "p95_latency_us": round(
            percentile(sorted_latencies, 95) / 1000, 3
        ),
        "p99_latency_us": round(
            percentile(sorted_latencies, 99) / 1000, 3
        ),
    }


async def run_repeated_benchmark(order_count: int, runs: int) -> dict:
    if runs < 1:
        raise ValueError("runs must be at least 1")

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
        result["throughput_orders_per_second"] for result in results
    ]

    return {
        "benchmark": "ChronosMatch Python matching engine",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "orders_per_run": order_count,
        "runs": runs,
        "results": results,
        "summary": {
            "mean_throughput_orders_per_second": round(
                statistics.mean(throughputs), 2
            ),
            "min_throughput_orders_per_second": min(throughputs),
            "max_throughput_orders_per_second": max(throughputs),
            "stdev_throughput_orders_per_second": round(
                statistics.pstdev(throughputs), 2
            ),
        },
        "notes": [
            "Single-process Python benchmark.",
            "Matching latency measures submit_order only.",
            "Does not measure mmap IPC or prove zero-copy communication.",
        ],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--orders", type=int, default=100_000)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument(
        "--output",
        default="benchmarks/results.json",
    )
    args = parser.parse_args()

    report = asyncio.run(
        run_repeated_benchmark(args.orders, args.runs)
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n")

    print("\nSummary:")
    print(json.dumps(report["summary"], indent=2))
    print(f"\nFull report saved to: {output_path}")


if __name__ == "__main__":
    main()
