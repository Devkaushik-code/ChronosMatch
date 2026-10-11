import unittest

from chronosmatch.matching_engine import MatchingEngine
from chronosmatch.market_simulator import MarketSimulator
from chronosmatch.trading_pipeline import run_trading_pipeline


class TestTradingPipeline(unittest.IsolatedAsyncioTestCase):
    async def test_processes_all_generated_orders(self):
        result = await run_trading_pipeline(count=100)

        self.assertEqual(result.orders_processed, 100)

    async def test_zero_orders(self):
        result = await run_trading_pipeline(count=0)

        self.assertEqual(result.orders_processed, 0)
        self.assertEqual(result.trades, [])
        self.assertIsNone(result.best_bid)
        self.assertIsNone(result.best_ask)

    async def test_reuses_supplied_engine(self):
        engine = MatchingEngine()

        result = await run_trading_pipeline(
            count=20,
            engine=engine,
        )

        self.assertEqual(result.orders_processed, 20)
        self.assertEqual(result.trades, engine.trades)

    async def test_rejects_negative_count(self):
        with self.assertRaises(ValueError):
            await run_trading_pipeline(count=-1)

    async def test_rejects_invalid_batch_size(self):
        with self.assertRaises(ValueError):
            await run_trading_pipeline(count=10, batch_size=0)

    async def test_accepts_supplied_simulator(self):
        simulator = MarketSimulator(seed=42)

        result = await run_trading_pipeline(
            count=10,
            simulator=simulator,
        )

        self.assertEqual(result.orders_processed, 10)


if __name__ == "__main__":
    unittest.main()
