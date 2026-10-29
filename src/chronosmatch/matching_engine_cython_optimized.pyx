# cython: language_level=3
"""Cython-backed price-time-priority matching engine."""

from collections import deque
from dataclasses import dataclass
from itertools import count


@dataclass
class Order:
    order_id: int
    side: str
    price: int
    quantity: int
    timestamp: int


@dataclass
class Trade:
    buy_order_id: int
    sell_order_id: int
    price: int
    quantity: int


class MatchingEngine:
    """Cython-compiled matching engine preserving the Python API."""

    def __init__(self):
        self.bids = {}
        self.asks = {}
        self._timestamps = count(1)
        self.trades = []

    def submit_order(
        self,
        order_id: int,
        side: str,
        price: int,
        quantity: int,
    ) -> list:
        side = side.upper()

        if side not in ("BUY", "SELL"):
            raise ValueError("side must be BUY or SELL")

        if price <= 0:
            raise ValueError("price must be positive")

        if quantity <= 0:
            raise ValueError("quantity must be positive")

        order = Order(
            order_id=order_id,
            side=side,
            price=price,
            quantity=quantity,
            timestamp=next(self._timestamps),
        )

        new_trades = []

        if side == "BUY":
            self._match_buy(order, new_trades)
        else:
            self._match_sell(order, new_trades)

        if order.quantity > 0:
            book = self.bids if side == "BUY" else self.asks
            book.setdefault(price, deque()).append(order)

        self.trades.extend(new_trades)
        return new_trades

    def _match_buy(self, order, new_trades):
        if not self.asks:
            return

        order_qty = order.quantity
        order_price = order.price
        best_ask = min(self.asks)

        while order_qty > 0 and best_ask <= order_price:
            queue = self.asks[best_ask]
            resting_order = queue[0]
            resting_qty = resting_order.quantity
            traded_quantity = min(order_qty, resting_qty)

            new_trades.append(
                Trade(
                    buy_order_id=order.order_id,
                    sell_order_id=resting_order.order_id,
                    price=resting_order.price,
                    quantity=traded_quantity,
                )
            )

            order_qty -= traded_quantity
            resting_qty -= traded_quantity
            resting_order.quantity = resting_qty

            if resting_qty == 0:
                queue.popleft()

            if not queue:
                del self.asks[best_ask]

                if not self.asks:
                    break

                best_ask = min(self.asks)

        order.quantity = order_qty

    def _match_sell(self, order, new_trades):
        if not self.bids:
            return

        order_qty = order.quantity
        order_price = order.price
        best_bid = max(self.bids)

        while order_qty > 0 and best_bid >= order_price:
            queue = self.bids[best_bid]
            resting_order = queue[0]
            resting_qty = resting_order.quantity
            traded_quantity = min(order_qty, resting_qty)

            new_trades.append(
                Trade(
                    buy_order_id=resting_order.order_id,
                    sell_order_id=order.order_id,
                    price=resting_order.price,
                    quantity=traded_quantity,
                )
            )

            order_qty -= traded_quantity
            resting_qty -= traded_quantity
            resting_order.quantity = resting_qty

            if resting_qty == 0:
                queue.popleft()

            if not queue:
                del self.bids[best_bid]

                if not self.bids:
                    break

                best_bid = max(self.bids)

        order.quantity = order_qty

    def best_bid(self):
        return max(self.bids) if self.bids else None

    def best_ask(self):
        return min(self.asks) if self.asks else None
