import tempfile
import unittest
from pathlib import Path

from chronosmatch.matching_engine import MatchingEngine, Trade
from chronosmatch.market_simulator import MarketSimulator
from chronosmatch.trade_ledger import TradeLedger
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
        result = await run_trading_pipeline(count=20, engine=engine)

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
        result = await run_trading_pipeline(count=10, simulator=simulator)

        self.assertEqual(result.orders_processed, 10)

    async def test_persists_executed_trades(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "trades.db"

            with TradeLedger(db_path) as ledger:
                result = await run_trading_pipeline(
                    count=100,
                    ledger=ledger,
                )

                self.assertGreater(len(result.trades), 0)
                self.assertEqual(
                    ledger.get_trades(),
                    result.trades,
                )
                self.assertEqual(
                    ledger.count_trades(),
                    len(result.trades),
                )

    async def test_zero_orders_do_not_persist_trades(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "trades.db"

            with TradeLedger(db_path) as ledger:
                result = await run_trading_pipeline(
                    count=0,
                    ledger=ledger,
                )

                self.assertEqual(result.trades, [])
                self.assertEqual(ledger.count_trades(), 0)

    async def test_existing_engine_trades_are_not_duplicated(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "trades.db"
            engine = MatchingEngine()

            # Create one existing trade before the pipeline starts.
            engine.submit_order(1, "SELL", 100, 5)
            engine.submit_order(2, "BUY", 100, 5)

            old_trades = list(engine.trades)
            self.assertEqual(len(old_trades), 1)

            with TradeLedger(db_path) as ledger:
                result = await run_trading_pipeline(
                    count=0,
                    engine=engine,
                    ledger=ledger,
                )

                self.assertEqual(result.trades, old_trades)
                self.assertEqual(ledger.count_trades(), 0)


    async def test_preserves_falsey_supplied_simulator(self):
        class FalseySimulator(MarketSimulator):
            def __bool__(self):
                return False

            async def generate_orders(self, count, batch_size=1000):
                self.was_used = True
                if False:
                    yield (0, 0, 0)

        simulator = FalseySimulator()
        simulator.was_used = False

        await run_trading_pipeline(count=0, simulator=simulator)

        self.assertTrue(simulator.was_used)

    async def test_preserves_falsey_supplied_engine(self):
        class FalseyEngine(MatchingEngine):
            def __bool__(self):
                return False

            def submit_order(self, *args, **kwargs):
                self.was_used = True
                return super().submit_order(*args, **kwargs)

        engine = FalseyEngine()
        engine.was_used = False

        await run_trading_pipeline(count=1, engine=engine)

        self.assertTrue(engine.was_used)

    async def test_collects_order_processing_latencies(self):
        latencies = []

        result = await run_trading_pipeline(
            count=20,
            order_processing_latencies_ns=latencies,
        )

        self.assertEqual(result.orders_processed, 20)
        self.assertEqual(len(latencies), 20)
        self.assertTrue(all(latency > 0 for latency in latencies))

if __name__ == "__main__":
    unittest.main()
