import unittest

from chronosmatch.matching_engine import MatchingEngine as PythonEngine
from chronosmatch.matching_engine_cython_original import MatchingEngine as OriginalCythonEngine
from chronosmatch.matching_engine_cython_optimized import MatchingEngine as OptimizedCythonEngine


class TestThreeWayMatchingEngineParity(unittest.TestCase):

    def test_all_engines_produce_identical_results(self):
        engines = [
            ("Python", PythonEngine()),
            ("Original Cython", OriginalCythonEngine()),
            ("Optimized Cython", OptimizedCythonEngine()),
        ]

        orders = [
            (1, "SELL", 105, 5),
            (2, "SELL", 100, 3),
            (3, "SELL", 100, 4),
            (4, "BUY", 100, 5),
            (5, "BUY", 110, 4),
            (6, "SELL", 99, 6),
            (7, "BUY", 98, 2),
            (8, "SELL", 110, 3),
            (9, "BUY", 105, 2),
            (10, "SELL", 103, 1),
        ]

        def book_snapshot(engine):
            return {
                "bids": {
                    price: [
                        (order.order_id, order.quantity)
                        for order in queue
                    ]
                    for price, queue in engine.bids.items()
                },
                "asks": {
                    price: [
                        (order.order_id, order.quantity)
                        for order in queue
                    ]
                    for price, queue in engine.asks.items()
                },
                "best_bid": engine.best_bid(),
                "best_ask": engine.best_ask(),
                "trades": [vars(trade) for trade in engine.trades],
            }

        for order in orders:
            results = []

            for name, engine in engines:
                trades = engine.submit_order(*order)
                results.append(
                    (
                        name,
                        [vars(trade) for trade in trades],
                        book_snapshot(engine),
                    )
                )

            reference_name, reference_trades, reference_snapshot = results[0]

            for name, trades, snapshot in results[1:]:
                with self.subTest(order=order, engine=name):
                    self.assertEqual(
                        trades,
                        reference_trades,
                        f"Trade mismatch: {reference_name} vs {name}",
                    )
                    self.assertEqual(
                        snapshot,
                        reference_snapshot,
                        f"Order-book mismatch: {reference_name} vs {name}",
                    )


if __name__ == "__main__":
    unittest.main(verbosity=2)
