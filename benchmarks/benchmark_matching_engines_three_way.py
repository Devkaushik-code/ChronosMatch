import json
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from benchmarks.benchmark_matching_engines import (
    make_workload,
    execute_workload,
    summarize,
)

from chronosmatch.matching_engine import MatchingEngine as PythonEngine
from chronosmatch.matching_engine_cython_original import (
    MatchingEngine as OriginalCythonEngine,
)
from chronosmatch.matching_engine_cython_optimized import (
    MatchingEngine as OptimizedCythonEngine,
)


ENGINES = {
    "python": PythonEngine,
    "cython_original": OriginalCythonEngine,
    "cython_optimized": OptimizedCythonEngine,
}


def run_benchmark(order_count=20000, runs=5, warmup_runs=1):
    workload = make_workload(order_count, seed=42)
    results = {name: [] for name in ENGINES}
    engine_names = list(ENGINES)

    for warmup in range(warmup_runs):
        for name in engine_names:
            execute_workload(ENGINES[name], workload)
        print(f"Warm-up {warmup + 1}/{warmup_runs} complete")

    for run_number in range(1, runs + 1):
        # Rotate execution order between runs.
        shift = (run_number - 1) % len(engine_names)
        run_order = engine_names[shift:] + engine_names[:shift]
        snapshots = {}

        for name in run_order:
            result, snapshot = execute_workload(
                ENGINES[name], workload
            )
            result["run"] = run_number
            results[name].append(result)
            snapshots[name] = snapshot

        reference = snapshots["python"]
        for name, snapshot in snapshots.items():
            if snapshot != reference:
                raise AssertionError(
                    f"Parity failure in run {run_number}: {name}"
                )

        throughputs = {
            name: results[name][-1]["throughput_orders_per_second"]
            for name in engine_names
        }
        print(
            f"Run {run_number}/{runs}: "
            + ", ".join(
                f"{name}={throughputs[name]:.2f} orders/sec"
                for name in engine_names
            )
            + " | parity PASS"
        )

    summaries = {
        name: summarize(results[name])
        for name in engine_names
    }

    python_mean = summaries["python"][
        "mean_throughput_orders_per_second"
    ]

    comparisons = {}
    for name in ("cython_original", "cython_optimized"):
        mean = summaries[name]["mean_throughput_orders_per_second"]
        ratio = mean / python_mean if python_mean else None
        comparisons[name] = {
            "throughput_ratio_vs_python": (
                round(ratio, 4) if ratio is not None else None
            ),
            "throughput_change_percent_vs_python": (
                round((ratio - 1) * 100, 2)
                if ratio is not None else None
            ),
        }

    original_mean = summaries["cython_original"][
        "mean_throughput_orders_per_second"
    ]
    optimized_mean = summaries["cython_optimized"][
        "mean_throughput_orders_per_second"
    ]
    original_ratio = (
        optimized_mean / original_mean if original_mean else None
    )

    report = {
        "benchmark": "ChronosMatch three-way matching-engine comparison",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {
            "python_version": sys.version,
            "python_implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "machine": platform.machine(),
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
            name: {
                "runs": results[name],
                "summary": summaries[name],
            }
            for name in engine_names
        },
        "comparisons_vs_python": comparisons,
        "optimized_vs_original_cython": {
            "throughput_ratio": (
                round(original_ratio, 4)
                if original_ratio is not None else None
            ),
            "throughput_change_percent": (
                round((original_ratio - 1) * 100, 2)
                if original_ratio is not None else None
            ),
        },
        "notes": [
            "All engines receive the same pre-generated deterministic orders.",
            "Workload generation and engine construction are excluded from throughput timing.",
            "Throughput and per-order latency are measured in separate passes.",
            "Warm-up measurements are excluded from reported results.",
            "Execution order rotates between measured runs.",
            "Every run compares trades and final order-book state.",
            "Results may vary with system load and runtime conditions.",
        ],
    }

    return report


if __name__ == "__main__":
    report = run_benchmark()

    output = Path(
        "benchmarks/results_engine_three_way_20000.json"
    )
    output.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )

    print("\n===== MEAN THROUGHPUT =====")
    for name, data in report["engines"].items():
        print(
            f"{name}: "
            f"{data['summary']['mean_throughput_orders_per_second']:.2f} "
            "orders/sec"
        )

    print("\n===== OPTIMIZED VS ORIGINAL CYTHON =====")
    print(report["optimized_vs_original_cython"])
    print("\nAll runs passed parity:", report["correctness"]["all_runs_passed_parity"])
    print("Saved results to:", output)
