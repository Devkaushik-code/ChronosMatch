"""Benchmark ChronosMatch trading pipeline."""

import asyncio
import json
import statistics
import time

from chronosmatch.market_simulator import MarketSimulator
from chronosmatch.matching_engine import MatchingEngine


async def benchmark(order_count: int = 10_000) -> dict:
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

    def percentile(values, percentile_value):
        if not values:
            return 0
        index = int((len(values) - 1) * percentile_value / 100)
        return values[index]

    return {
        "orders_processed": processed,
        "trades_executed": len(engine.trades),
        "elapsed_ms": round(elapsed_ns / 1_000_000, 3),
        "throughput_orders_per_second": round(
            processed / (elapsed_ns / 1_000_000_000), 2
        ) if elapsed_ns else 0,
        "average_matching_latency_us": round(
            statistics.mean(latencies_ns) / 1000, 3
        ) if latencies_ns else 0,
        "p50_latency_us": round(percentile(sorted_latencies, 50) / 1000, 3),
        "p95_latency_us": round(percentile(sorted_latencies, 95) / 1000, 3),
        "p99_latency_us": round(percentile(sorted_latencies, 99) / 1000, 3),
    }


if __name__ == "__main__":
    results = asyncio.run(benchmark(10_000))
    print(json.dumps(results, indent=2))
