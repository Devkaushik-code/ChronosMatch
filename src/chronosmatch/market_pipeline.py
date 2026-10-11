"""Integration between the async market simulator and mmap ring buffer."""

import asyncio
from collections.abc import AsyncIterator

from chronosmatch.ipc.mmap_ring_buffer import MmapRingBuffer
from chronosmatch.market_simulator import MarketSimulator


async def write_orders(
    simulator: MarketSimulator,
    buffer: MmapRingBuffer,
    count: int,
    batch_size: int = 1000,
) -> int:
    """Generate orders and write them into the ring buffer.

    The buffer must have enough free slots for all generated orders.
    """
    if count < 0:
        raise ValueError("count cannot be negative")

    if count > buffer.capacity - buffer.size:
        raise BufferError("not enough free slots for all orders")

    written = 0

    async for order_id, price, quantity in simulator.generate_orders(
        count=count,
        batch_size=batch_size,
    ):
        buffer.put(order_id, price, quantity)
        written += 1

    return written


def read_orders(
    buffer: MmapRingBuffer,
    count: int,
) -> list[tuple[int, int, int]]:
    """Read up to count orders from the ring buffer."""
    if count < 0:
        raise ValueError("count cannot be negative")

    orders = []

    for _ in range(min(count, buffer.size)):
        orders.append(buffer.get())

    return orders


async def run_pipeline(
    path: str,
    count: int,
    capacity: int = 10000,
) -> list[tuple[int, int, int]]:
    """Generate mock orders, buffer them, and read them back."""
    if capacity <= 0:
        raise ValueError("capacity must be positive")

    if count < 0 or count > capacity:
        raise ValueError("count must be between zero and capacity")

    simulator = MarketSimulator()

    with MmapRingBuffer(path, capacity) as buffer:
        written = await write_orders(simulator, buffer, count)
        if written != count:
            raise RuntimeError("not all orders were written")

        orders = read_orders(buffer, count)

        if len(orders) != count:
            raise RuntimeError("not all orders were read")

        return orders
