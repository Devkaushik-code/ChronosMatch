"""Connect the mock market simulator to the price-time matching engine."""

import asyncio
from dataclasses import dataclass

from chronosmatch.market_simulator import MarketSimulator
from chronosmatch.matching_engine import MatchingEngine, Trade


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
) -> TradingPipelineResult:
    """Generate mock orders and process them through the matching engine."""

    if count < 0:
        raise ValueError("count cannot be negative")

    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    simulator = simulator or MarketSimulator()
    engine = engine or MatchingEngine()
    processed = 0

    async for order_id, price, quantity in simulator.generate_orders(
        count=count,
        batch_size=batch_size,
    ):
        # Deterministic side assignment for testing, not real market data.
        side = "BUY" if order_id % 2 == 1 else "SELL"
        engine.submit_order(order_id, side, price, quantity)
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
