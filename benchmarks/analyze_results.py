"""Read-only analyzer for ChronosMatch benchmark result JSON files."""

import argparse
import json
import math
from pathlib import Path


def _number(value):
    """Return a finite numeric value, or None."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value):
        return None
    return float(value)


def _format(value, digits=2):
    number = _number(value)
    return f"{number:,.{digits}f}" if number is not None else "N/A"


def load_result(path):
    """Load and validate one benchmark result file."""
    path = Path(path)

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("top-level JSON value must be an object")

    if not isinstance(data.get("benchmark"), str):
        raise ValueError("missing or invalid benchmark name")

    if not isinstance(data.get("timestamp_utc"), str):
        raise ValueError("missing or invalid timestamp_utc")

    if isinstance(data.get("engines"), dict):
        kind = "engine_comparison"
    elif isinstance(data.get("results"), list):
        if "pipeline" in data["benchmark"].lower():
            kind = "pipeline"
        else:
            kind = "matching_engine"
    else:
        raise ValueError("unsupported benchmark result format")

    return {
        "path": path,
        "data": data,
        "kind": kind,
    }


def _engine_rows(data):
    engines = data.get("engines", {})
    rows = []

    for name, engine in engines.items():
        if not isinstance(engine, dict):
            continue

        summary = engine.get("summary", {})
        if not isinstance(summary, dict):
            summary = {}

        throughput = _number(
            summary.get("mean_throughput_orders_per_second")
        )

        if throughput is None:
            runs = engine.get("runs", [])
            values = [
                _number(run.get("throughput_orders_per_second"))
                for run in runs
                if isinstance(run, dict)
            ]
            values = [value for value in values if value is not None]
            if values:
                throughput = sum(values) / len(values)

        rows.append((name, throughput, summary))

    return rows


def summarize_result(result):
    """Create a concise, consistent summary for one result."""
    data = result["data"]
    kind = result["kind"]
    workload = data.get("workload", {})
    orders = (
        workload.get("orders_per_run")
        if isinstance(workload, dict)
        else None
    )
    if orders is None:
        orders = data.get("orders_per_run")

    report = {
        "file": result["path"].name,
        "benchmark": data["benchmark"],
        "timestamp": data["timestamp_utc"],
        "kind": kind,
        "orders_per_run": orders,
        "runs": data.get("runs", workload.get("runs") if isinstance(workload, dict) else None),
        "metrics": [],
    }

    if kind == "engine_comparison":
        for name, throughput, summary in _engine_rows(data):
            report["metrics"].append({
                "name": name,
                "throughput": throughput,
                "p50": _number(summary.get("median_p50_latency_us")),
                "p95": _number(summary.get("median_p95_latency_us")),
                "p99": _number(summary.get("median_p99_latency_us")),
            })

        comparison = data.get(
            "comparisons_vs_python",
            data.get("comparison", {}),
        )
        if isinstance(comparison, dict):
            report["comparison"] = comparison

        optimized = data.get("optimized_vs_original_cython")
        if isinstance(optimized, dict):
            report["optimized_comparison"] = optimized

    else:
        summary = data.get("summary", {})
        if not isinstance(summary, dict):
            summary = {}

        if kind == "pipeline":
            keys = (
                "mean_throughput_orders_per_second",
                "mean_pipeline_latency_ms",
                "p95_pipeline_latency_ms",
                "p99_pipeline_latency_ms",
                "mean_individual_order_processing_latency_us",
                "median_run_order_p50_latency_us",
                "median_run_order_p95_latency_us",
                "median_run_order_p99_latency_us",
            )
        else:
            keys = (
                "mean_throughput_orders_per_second",
                "median_throughput_orders_per_second",
                "min_throughput_orders_per_second",
                "max_throughput_orders_per_second",
                "stdev_throughput_orders_per_second",
                "median_p50_latency_us",
                "median_p95_latency_us",
                "median_p99_latency_us",
            )

        report["metrics"] = [
            (key, _number(summary.get(key)))
            for key in keys
            if key in summary
        ]

    return report


def analyze_directory(directory):
    """Analyze results*.json files without changing them."""
    directory = Path(directory)
    reports = []
    errors = []

    if not directory.is_dir():
        raise ValueError(f"not a directory: {directory}")

    for path in sorted(directory.glob("results*.json")):
        try:
            result = load_result(path)
            reports.append(summarize_result(result))
        except ValueError as exc:
            errors.append((path.name, str(exc)))

    return reports, errors


def render_report(reports, errors):
    """Render summaries as readable terminal text."""
    lines = ["ChronosMatch Benchmark Results", "=" * 34]

    for report in reports:
        lines.extend([
            "",
            report["file"],
            f"  Type: {report['kind']}",
            f"  Benchmark: {report['benchmark']}",
            f"  Timestamp: {report['timestamp']}",
            f"  Orders/run: {report['orders_per_run'] or 'N/A'}",
            f"  Runs: {report['runs'] or 'N/A'}",
        ])

        if report["kind"] == "engine_comparison":
            for metric in report["metrics"]:
                lines.append(
                    f"  {metric['name']}: "
                    f"{_format(metric['throughput'])} orders/sec"
                )
                if metric["p95"] is not None:
                    lines.append(
                        f"    Median p95 latency: "
                        f"{_format(metric['p95'], 3)} us"
                    )

            comparison = report.get("comparison", {})
            direct_change = comparison.get("throughput_improvement_percent")
            if _number(direct_change) is not None:
                lines.append(
                    f"  Cython vs Python throughput change: "
                    f"{_format(direct_change)}%"
                )

            for name, values in comparison.items():
                if isinstance(values, dict):
                    change = values.get(
                        "throughput_change_percent_vs_python"
                    )
                    if change is None:
                        change = values.get("throughput_improvement_percent")
                    if _number(change) is not None:
                        lines.append(
                            f"  {name} vs Python: {_format(change)}%"
                        )

            optimized = report.get("optimized_comparison", {})
            change = optimized.get("throughput_change_percent")
            if _number(change) is not None:
                lines.append(
                    f"  Optimized vs original Cython: "
                    f"{_format(change)}%"
                )
        else:
            for key, value in report["metrics"]:
                label = key.replace("_", " ")
                unit = (
                    " orders/sec"
                    if "throughput" in key
                    else " ms"
                    if "ms" in key
                    else " us"
                )
                lines.append(f"  {label}: {_format(value)}{unit}")

    lines.extend([
        "",
        "=" * 34,
        f"Files analyzed: {len(reports)}",
        f"Files skipped: {len(errors)}",
    ])

    for filename, error in errors:
        lines.append(f"  SKIPPED {filename}: {error}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze ChronosMatch benchmark result JSON files."
    )
    parser.add_argument(
        "--directory",
        default="benchmarks",
        help="Directory containing results*.json files",
    )
    args = parser.parse_args()

    try:
        reports, errors = analyze_directory(args.directory)
    except ValueError as exc:
        parser.error(str(exc))

    print(render_report(reports, errors))


if __name__ == "__main__":
    main()
