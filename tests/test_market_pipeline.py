import asyncio
import os
import tempfile
import unittest

from chronosmatch.ipc.mmap_ring_buffer import MmapRingBuffer
from chronosmatch.market_simulator import MarketSimulator
from chronosmatch.market_pipeline import (
    read_orders,
    run_pipeline,
    write_orders,
)


class TestMarketPipeline(unittest.TestCase):

    def test_write_and_read_orders(self):
        async def run_test():
            with tempfile.TemporaryDirectory() as directory:
                path = os.path.join(directory, "orders.bin")

                with MmapRingBuffer(path, 10) as buffer:
                    simulator = MarketSimulator(seed=42)

                    written = await write_orders(
                        simulator, buffer, count=5
                    )

                    self.assertEqual(written, 5)
                    self.assertEqual(buffer.size, 5)

                    orders = read_orders(buffer, 5)

                    self.assertEqual(len(orders), 5)
                    self.assertEqual(
                        [order[0] for order in orders],
                        [1, 2, 3, 4, 5],
                    )
                    self.assertTrue(buffer.is_empty)

        asyncio.run(run_test())

    def test_insufficient_capacity(self):
        async def run_test():
            with tempfile.TemporaryDirectory() as directory:
                path = os.path.join(directory, "orders.bin")

                with MmapRingBuffer(path, 2) as buffer:
                    simulator = MarketSimulator()

                    with self.assertRaises(BufferError):
                        await write_orders(
                            simulator, buffer, count=3
                        )

                    self.assertTrue(buffer.is_empty)

        asyncio.run(run_test())

    def test_pipeline_end_to_end(self):
        async def run_test():
            with tempfile.TemporaryDirectory() as directory:
                path = os.path.join(directory, "orders.bin")

                orders = await run_pipeline(
                    path=path,
                    count=20,
                    capacity=20,
                )

                self.assertEqual(len(orders), 20)
                self.assertEqual(
                    [order[0] for order in orders],
                    list(range(1, 21)),
                )

        asyncio.run(run_test())

    def test_pipeline_rejects_count_over_capacity(self):
        async def run_test():
            with tempfile.TemporaryDirectory() as directory:
                path = os.path.join(directory, "orders.bin")

                with self.assertRaises(ValueError):
                    await run_pipeline(
                        path=path,
                        count=3,
                        capacity=2,
                    )

        asyncio.run(run_test())

    def test_read_negative_count_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "orders.bin")

            with MmapRingBuffer(path, 2) as buffer:
                with self.assertRaises(ValueError):
                    read_orders(buffer, -1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
