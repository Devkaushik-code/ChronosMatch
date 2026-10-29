import unittest

from chronosmatch.matching_engine import MatchingEngine as PythonEngine
from chronosmatch.matching_engine_cython import MatchingEngine as CythonEngine


class TestMatchingEngineParity(unittest.TestCase):

    def test_identical_orders_produce_identical_results(self):
        python_engine = PythonEngine()
        cython_engine = CythonEngine()

        orders = [
            (1, "SELL", 105, 5),
            (2, "SELL", 100, 3),
            (3, "BUY", 100, 2),
            (4, "BUY", 110, 4),
            (5, "SELL", 99, 6),
            (6, "BUY", 98, 2),
            (7, "SELL", 110, 3),
        ]

        for order in orders:
            python_trades = python_engine.submit_order(*order)
            cython_trades = cython_engine.submit_order(*order)

            self.assertEqual(
                [vars(trade) for trade in python_trades],
                [vars(trade) for trade in cython_trades],
            )

            self.assertEqual(
                python_engine.best_bid(),
                cython_engine.best_bid(),
            )
            self.assertEqual(
                python_engine.best_ask(),
                cython_engine.best_ask(),
            )

            self.assertEqual(
                {
                    price: [
                        (item.order_id, item.quantity)
                        for item in queue
                    ]
                    for price, queue in python_engine.bids.items()
                },
                {
                    price: [
                        (item.order_id, item.quantity)
                        for item in queue
                    ]
                    for price, queue in cython_engine.bids.items()
                },
            )

            self.assertEqual(
                {
                    price: [
                        (item.order_id, item.quantity)
                        for item in queue
                    ]
                    for price, queue in python_engine.asks.items()
                },
                {
                    price: [
                        (item.order_id, item.quantity)
                        for item in queue
                    ]
                    for price, queue in cython_engine.asks.items()
                },
            )

        self.assertEqual(
            [vars(trade) for trade in python_engine.trades],
            [vars(trade) for trade in cython_engine.trades],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
