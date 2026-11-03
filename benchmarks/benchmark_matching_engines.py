"""Compare Python and Cython matching-engine performance."""

import argparse
import json
import platform
import random
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from chronosmatch.matching_engine import MatchingEngine as PythonEngine
from chronosmatch.matching_engine_cython import MatchingEngine as CythonEngine


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

    return (
        ordered[lower] * (1 - fraction)
        + ordered[upper] * fraction
    )


def make_workload(order_count, seed=42):
    """Generate one deterministic workload shared by both engines."""
    rng = random.Random(seed)
    orders = []

    for order_id in range(1, order_count + 1):
        orders.append(
            (
                order_id,
                rng.choice(("BUY", "SELL")),
                rng.randint(9900, 10100),
                rng.randint(1, 20),
            )
        )

    return orders


def snapshot_engine(engine):
    """Return a comparable snapshot of trades and the remaining book."""
    trades = [
        (
            trade.buy_order_id,
            trade.sell_order_id,
            trade.price,
            trade.quantity,
        )
        for trade in engine.trades
    ]

    def snapshot_book(book):
        result = []

        for price in sorted(book):
            queue = []

            for order in book[price]:
                queue.append(
                    (
                        order.order_id,
                        order.side,
                        order.price,
                        order.quantity,
                        order.timestamp,
                    )
                )

            result.append((price, queue))

        return result

    return {
        "trades": trades,
        "bids": snapshot_book(engine.bids),
        "asks": snapshot_book(engine.asks),
        "best_bid": engine.best_bid(),
        "best_ask": engine.best_ask(),
    }


def execute_workload(engine_class, orders):
    """Measure throughput and latency in separate passes."""
    # Pass 1: Measure throughput without per-order timer overhead.
    engine = engine_class()

    start_ns = time.perf_counter_ns()

    for order_id, side, price, quantity in orders:
        engine.submit_order(
            order_id,
            side,
            price,
            quantity,
        )

    elapsed_ns = time.perf_counter_ns() - start_ns
    elapsed_seconds = elapsed_ns / 1_000_000_000

    # Save the completed engine state for parity verification.
    snapshot = snapshot_engine(engine)

    # Pass 2: Measure per-order latency on a fresh engine.
    latency_engine = engine_class()
    latencies_ns = []

    for order_id, side, price, quantity in orders:
        order_start_ns = time.perf_counter_ns()

        latency_engine.submit_order(
            order_id,
            side,
            price,
            quantity,
        )

        latencies_ns.append(
            time.perf_counter_ns() - order_start_ns
        )

    processed = len(orders)

    result = {
        "orders_processed": processed,
        "trades_executed": len(engine.trades),
        "elapsed_ms": round(elapsed_ns / 1_000_000, 3),
        "throughput_orders_per_second": round(
            processed / elapsed_seconds, 2
        ) if elapsed_seconds else 0,
        "average_latency_us": round(
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

    return result, snapshot

def summarize(results):
    """Summarize repeated measurements."""
    throughputs = [
        result["throughput_orders_per_second"]
        for result in results
    ]

    return {
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
        "median_p50_latency_us": round(
            statistics.median(
                result["p50_latency_us"] for result in results
            ), 3
        ),
        "median_p95_latency_us": round(
            statistics.median(
                result["p95_latency_us"] for result in results
            ), 3
        ),
        "median_p99_latency_us": round(
            statistics.median(
                result["p99_latency_us"] for result in results
            ), 3
        ),
    }


def run_benchmark(order_count, runs, warmup_runs):
    """Benchmark both engines against the same deterministic workload."""
    if order_count < 1:
        raise ValueError("order_count must be at least 1")

    if runs < 1:
        raise ValueError("runs must be at least 1")

    if warmup_runs < 0:
        raise ValueError("warmup_runs cannot be negative")

    workload = make_workload(order_count)

    engines = {
        "python": PythonEngine,
        "cython": CythonEngine,
    }

    # Warm up both implementations; exclude these measurements.
    for warmup_number in range(1, warmup_runs + 1):
        for engine_class in engines.values():
            execute_workload(engine_class, workload)

        print(f"Warm-up {warmup_number}/{warmup_runs} complete")

    results = {"python": [], "cython": []}

    for run_number in range(1, runs + 1):
        # Alternate execution order to reduce systematic ordering bias.
        names = (
            ["python", "cython"]
            if run_number % 2 == 1
            else ["cython", "python"]
        )

        snapshots = {}

        for name in names:
            result, snapshot = execute_workload(
                engines[name],
                workload,
            )

            result["run"] = run_number
            results[name].append(result)
            snapshots[name] = snapshot

        # A performance comparison is meaningful only if outputs agree.
        if snapshots["python"] != snapshots["cython"]:
            raise AssertionError(
                f"Engine results differ in run {run_number}"
            )

        print(
            f"Run {run_number}/{runs}: "
            f"Python={results['python'][-1]['throughput_orders_per_second']} "
            f"orders/sec, "
            f"Cython={results['cython'][-1]['throughput_orders_per_second']} "
            f"orders/sec; parity PASS"
        )

    python_summary = summarize(results["python"])
    cython_summary = summarize(results["cython"])

    python_throughput = python_summary[
        "mean_throughput_orders_per_second"
    ]
    cython_throughput = cython_summary[
        "mean_throughput_orders_per_second"
    ]

    speedup = (
        cython_throughput / python_throughput
        if python_throughput > 0
        else None
    )

    return {
        "benchmark": "ChronosMatch Python vs Cython matching engines",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python_version": sys.version,
            "python_implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor() or "Not reported",
        },
        "workload": {
            "orders_per_run": order_count,
            "seed": 42,
            "runs": runs,
            "warmup_runs": warmup_runs,
        },
        "correctness": {
            "all_runs_passed_parity": True,
            "compared": [
                "trades",
                "remaining bid and ask books",
                "remaining order quantities and timestamps",
                "best bid",
                "best ask",
            ],
        },
        "engines": {
            "python": {
                "runs": results["python"],
                "summary": python_summary,
            },
            "cython": {
                "runs": results["cython"],
                "summary": cython_summary,
            },
        },
        "comparison": {
            "cython_to_python_mean_throughput_ratio": round(
                speedup, 4
            ) if speedup is not None else None,
            "throughput_improvement_percent": round(
                (speedup - 1) * 100, 2
            ) if speedup is not None else None,
        },
        "notes": [
            "Both engines receive the same pre-generated orders.",
            "Workload generation is excluded from timing.",
            "Engine construction is excluded from timing.",
            "Throughput timing includes per-order latency instrumentation.",
            "Latency measures submit_order, including timing overhead.",
            "Warm-up runs are excluded from reported results.",
            "Each measured run verifies identical engine state and trades.",
            "Results depend on the runtime environment and system load.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(
        description="Compare Python and Cython matching engines."
    )
    parser.add_argument("--orders", type=int, default=10000)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--warmup-runs", type=int, default=1)
    parser.add_argument(
        "--output",
        default="benchmarks/results_engine_comparison.json",
    )
    args = parser.parse_args()

    if args.orders < 1:
        parser.error("--orders must be at least 1")

    if args.runs < 1:
        parser.error("--runs must be at least 1")

    if args.warmup_runs < 0:
        parser.error("--warmup-runs cannot be negative")

    try:
        report = run_benchmark(
            args.orders,
            args.runs,
            args.warmup_runs,
        )
    except AssertionError as exc:
        parser.exit(1, f"Correctness check failed: {exc}\n")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    print("\nMean throughput:")
    print(
        "Python:",
        report["engines"]["python"]["summary"][
            "mean_throughput_orders_per_second"
        ],
        "orders/sec",
    )
    print(
        "Cython:",
        report["engines"]["cython"]["summary"][
            "mean_throughput_orders_per_second"
        ],
        "orders/sec",
    )
    print("\nComparison:")
    print(json.dumps(report["comparison"], indent=2))
    print(f"\nFull report saved to: {output_path}")


if __name__ == "__main__":
    main()
