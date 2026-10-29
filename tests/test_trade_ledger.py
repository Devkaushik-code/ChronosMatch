"""Tests for SQLite trade persistence."""

import tempfile
import unittest
from pathlib import Path

from chronosmatch.matching_engine import Trade
from chronosmatch.trade_ledger import TradeLedger


class TestTradeLedger(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_trades.db"
        self.ledger = TradeLedger(self.db_path)

    def tearDown(self):
        self.ledger.close()
        self.temp_dir.cleanup()

    def test_save_and_retrieve_trade(self):
        trade = Trade(
            buy_order_id=1,
            sell_order_id=2,
            price=100,
            quantity=5,
        )

        saved_count = self.ledger.save_trades([trade])

        self.assertEqual(saved_count, 1)
        self.assertEqual(self.ledger.count_trades(), 1)
        self.assertEqual(self.ledger.get_trades(), [trade])

    def test_empty_trade_list(self):
        saved_count = self.ledger.save_trades([])

        self.assertEqual(saved_count, 0)
        self.assertEqual(self.ledger.count_trades(), 0)

    def test_save_multiple_trades(self):
        trades = [
            Trade(1, 2, 100, 5),
            Trade(3, 4, 105, 2),
            Trade(5, 6, 110, 3),
        ]

        saved_count = self.ledger.save_trades(trades)

        self.assertEqual(saved_count, 3)
        self.assertEqual(self.ledger.get_trades(), trades)

    def test_trades_survive_database_reopen(self):
        trade = Trade(10, 20, 150, 4)
        self.ledger.save_trades([trade])

        self.ledger.close()
        self.ledger = TradeLedger(self.db_path)

        self.assertEqual(self.ledger.count_trades(), 1)
        self.assertEqual(self.ledger.get_trades(), [trade])


if __name__ == "__main__":
    unittest.main()
