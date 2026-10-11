import asyncio
import unittest

from chronosmatch.market_simulator import MarketSimulator


class TestMarketSimulator(unittest.TestCase):

    def test_generates_requested_number_of_orders(self):
        async def run_test():
            simulator = MarketSimulator(seed=42)
            orders = [
                order
                async for order in simulator.generate_orders(5)
            ]

            self.assertEqual(len(orders), 5)

            self.assertEqual(
                [order[0] for order in orders],
                [1, 2, 3, 4, 5],
            )

            for order_id, price, quantity in orders:
                self.assertGreater(order_id, 0)
                self.assertGreater(price, 0)
                self.assertGreater(quantity, 0)

        asyncio.run(run_test())

    def test_zero_orders(self):
        async def run_test():
            simulator = MarketSimulator()
            orders = [
                order
                async for order in simulator.generate_orders(0)
            ]
            self.assertEqual(orders, [])

        asyncio.run(run_test())

    def test_negative_count_rejected(self):
        async def run_test():
            simulator = MarketSimulator()

            with self.assertRaises(ValueError):
                async for _ in simulator.generate_orders(-1):
                    pass

        asyncio.run(run_test())

    def test_invalid_batch_size_rejected(self):
        async def run_test():
            simulator = MarketSimulator()

            with self.assertRaises(ValueError):
                async for _ in simulator.generate_orders(5, batch_size=0):
                    pass

        asyncio.run(run_test())

    def test_invalid_constructor_arguments(self):
        with self.assertRaises(ValueError):
            MarketSimulator(base_price=0)

        with self.assertRaises(ValueError):
            MarketSimulator(max_price_change=-1)

        with self.assertRaises(ValueError):
            MarketSimulator(max_quantity=0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
