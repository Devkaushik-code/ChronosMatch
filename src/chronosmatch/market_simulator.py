"""Asynchronous mock market order generator for ChronosMatch."""

import asyncio
import random
from collections.abc import AsyncIterator


class MarketSimulator:
    """Generate reproducible mock trading orders asynchronously."""

    def __init__(
        self,
        base_price: int = 2500,
        max_price_change: int = 20,
        max_quantity: int = 100,
        seed: int = 42,
    ):
        if base_price <= 0:
            raise ValueError("base_price must be positive")

        if max_price_change < 0:
            raise ValueError("max_price_change cannot be negative")

        if max_quantity <= 0:
            raise ValueError("max_quantity must be positive")

        self.base_price = base_price
        self.max_price_change = max_price_change
        self.max_quantity = max_quantity
        self.random = random.Random(seed)

    async def generate_orders(
        self,
        count: int,
        batch_size: int = 1000,
    ) -> AsyncIterator[tuple[int, int, int]]:
        """Yield (order_id, price, quantity) tuples asynchronously."""

        if count < 0:
            raise ValueError("count cannot be negative")

        if batch_size <= 0:
            raise ValueError("batch_size must be positive")

        for order_id in range(1, count + 1):
            price = self.base_price + self.random.randint(
                -self.max_price_change,
                self.max_price_change,
            )

            price = max(1, price)
            quantity = self.random.randint(1, self.max_quantity)

            yield order_id, price, quantity

            if order_id % batch_size == 0:
                await asyncio.sleep(0)
