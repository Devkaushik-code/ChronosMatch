import unittest

from chronosmatch.matching_engine_cython import MatchingEngine


class TestCythonMatchingEngine(unittest.TestCase):

    def setUp(self):
        self.engine = MatchingEngine()

    def test_buy_matches_sell(self):
        self.engine.submit_order(1, "SELL", 100, 5)
        trades = self.engine.submit_order(2, "BUY", 100, 3)

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].buy_order_id, 2)
        self.assertEqual(trades[0].sell_order_id, 1)
        self.assertEqual(trades[0].price, 100)
        self.assertEqual(trades[0].quantity, 3)

    def test_no_match_when_prices_do_not_cross(self):
        self.engine.submit_order(1, "BUY", 100, 10)
        trades = self.engine.submit_order(2, "SELL", 110, 5)

        self.assertEqual(trades, [])
        self.assertEqual(self.engine.best_bid(), 100)
        self.assertEqual(self.engine.best_ask(), 110)

    def test_price_priority_for_sells(self):
        self.engine.submit_order(1, "SELL", 105, 5)
        self.engine.submit_order(2, "SELL", 100, 5)

        trades = self.engine.submit_order(3, "BUY", 110, 5)

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].sell_order_id, 2)
        self.assertEqual(trades[0].price, 100)

    def test_time_priority_at_same_price(self):
        self.engine.submit_order(1, "SELL", 100, 2)
        self.engine.submit_order(2, "SELL", 100, 4)

        trades = self.engine.submit_order(3, "BUY", 100, 3)

        self.assertEqual(len(trades), 2)
        self.assertEqual(trades[0].sell_order_id, 1)
        self.assertEqual(trades[0].quantity, 2)
        self.assertEqual(trades[1].sell_order_id, 2)
        self.assertEqual(trades[1].quantity, 1)

    def test_partial_fill_keeps_remaining_quantity(self):
        self.engine.submit_order(1, "SELL", 100, 10)
        trades = self.engine.submit_order(2, "BUY", 100, 4)

        self.assertEqual(trades[0].quantity, 4)
        self.assertEqual(self.engine.asks[100][0].quantity, 6)

    def test_invalid_side_rejected(self):
        with self.assertRaises(ValueError):
            self.engine.submit_order(1, "HOLD", 100, 1)

    def test_invalid_price_rejected(self):
        with self.assertRaises(ValueError):
            self.engine.submit_order(1, "BUY", 0, 1)

    def test_invalid_quantity_rejected(self):
        with self.assertRaises(ValueError):
            self.engine.submit_order(1, "BUY", 100, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
