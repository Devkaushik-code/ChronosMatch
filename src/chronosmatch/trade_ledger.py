"""SQLite persistence for executed ChronosMatch trades."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from collections.abc import Iterable

from chronosmatch.matching_engine import Trade


class TradeLedger:
    """Store and retrieve executed trades using SQLite."""

    def __init__(self, db_path: str | Path = "chronosmatch_trades.db"):
        self.db_path = str(db_path)
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row

        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                buy_order_id INTEGER NOT NULL,
                sell_order_id INTEGER NOT NULL,
                price INTEGER NOT NULL CHECK (price > 0),
                quantity INTEGER NOT NULL CHECK (quantity > 0),
                created_at TEXT NOT NULL
            )
            """
        )
        self.connection.commit()

    def save_trades(self, trades: Iterable[Trade]) -> int:
        """Save trades atomically and return the number saved."""
        rows = []

        for trade in trades:
            rows.append(
                (
                    trade.buy_order_id,
                    trade.sell_order_id,
                    trade.price,
                    trade.quantity,
                    datetime.now(timezone.utc).isoformat(),
                )
            )

        if not rows:
            return 0

        with self.connection:
            self.connection.executemany(
                """
                INSERT INTO trades (
                    buy_order_id,
                    sell_order_id,
                    price,
                    quantity,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                rows,
            )

        return len(rows)

    def get_trades(self) -> list[Trade]:
        """Return saved trades in insertion order."""
        rows = self.connection.execute(
            """
            SELECT buy_order_id, sell_order_id, price, quantity
            FROM trades
            ORDER BY id
            """
        ).fetchall()

        return [
            Trade(
                buy_order_id=row["buy_order_id"],
                sell_order_id=row["sell_order_id"],
                price=row["price"],
                quantity=row["quantity"],
            )
            for row in rows
        ]

    def count_trades(self) -> int:
        """Return the total number of stored trades."""
        row = self.connection.execute(
            "SELECT COUNT(*) AS total FROM trades"
        ).fetchone()
        return row["total"]

    def close(self) -> None:
        """Close the SQLite connection."""
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
