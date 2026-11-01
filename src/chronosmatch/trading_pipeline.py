"""Connect the mock market simulator to the price-time matching engine."""

import asyncio
import time
from dataclasses import dataclass

from chronosmatch.market_simulator import MarketSimulator
from chronosmatch.matching_engine import MatchingEngine, Trade
from chronosmatch.trade_ledger import TradeLedger


@dataclass
class TradingPipelineResult:
    """Summary of one simulated trading run."""

    orders_processed: int
    trades: list[Trade]
    best_bid: int | None
    best_ask: int | None


async def run_trading_pipeline(
    count: int,
    batch_size: int = 1000,
    simulator: MarketSimulator | None = None,
    engine: MatchingEngine | None = None,
    ledger: TradeLedger | None = None,
    order_processing_latencies_ns: list[int] | None = None,
) -> TradingPipelineResult:
    """Generate orders, match them, and optionally persist trades.

    When order_processing_latencies_ns is supplied, append each order's
    processing duration in nanoseconds. Timing covers side assignment,
    matching, and any trade persistence, but excludes order generation.
    """
    if count < 0:
        raise ValueError("count cannot be negative")

    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    if simulator is None:
        simulator = MarketSimulator()

    if engine is None:
        engine = MatchingEngine()
    processed = 0

    async for order_id, price, quantity in simulator.generate_orders(
        count=count,
        batch_size=batch_size,
    ):
        processing_start_ns = (
            time.perf_counter_ns()
            if order_processing_latencies_ns is not None
            else 0
        )

        # Deterministic side assignment for testing, not real market data.
        side = "BUY" if order_id % 2 == 1 else "SELL"

        new_trades = engine.submit_order(
            order_id,
            side,
            price,
            quantity,
        )

        # Persist only trades produced by this order.
        if ledger is not None and new_trades:
            ledger.save_trades(new_trades)

        if order_processing_latencies_ns is not None:
            order_processing_latencies_ns.append(
                time.perf_counter_ns() - processing_start_ns
            )

        processed += 1

    return TradingPipelineResult(
        orders_processed=processed,
        trades=list(engine.trades),
        best_bid=engine.best_bid(),
        best_ask=engine.best_ask(),
    )


def run_trading_pipeline_sync(
    count: int,
    batch_size: int = 1000,
) -> TradingPipelineResult:
    """Synchronous convenience wrapper for scripts and manual testing."""
    return asyncio.run(
        run_trading_pipeline(count=count, batch_size=batch_size)
    )
