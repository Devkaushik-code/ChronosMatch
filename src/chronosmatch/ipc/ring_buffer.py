"""
ChronosMatch: Fixed-capacity ring buffer prototype.

This first version is an in-memory, single-process implementation.
It does not yet provide mmap-based IPC or inter-process synchronization.
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Order:
    order_id: int
    price: int
    quantity: int


class RingBuffer:
    """A fixed-capacity FIFO ring buffer for Order objects."""

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be greater than zero")

        self._capacity = capacity
        self._buffer: list[Order | None] = [None] * capacity
        self._head = 0
        self._tail = 0
        self._size = 0

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def size(self) -> int:
        return self._size

    @property
    def is_empty(self) -> bool:
        return self._size == 0

    @property
    def is_full(self) -> bool:
        return self._size == self._capacity

    def put(self, order: Order) -> None:
        """Add an order; raise BufferError if the buffer is full."""
        if self.is_full:
            raise BufferError("ring buffer is full")

        self._buffer[self._tail] = order
        self._tail = (self._tail + 1) % self._capacity
        self._size += 1

    def get(self) -> Order:
        """Remove and return the oldest order."""
        if self.is_empty:
            raise BufferError("ring buffer is empty")

        order = self._buffer[self._head]
        self._buffer[self._head] = None
        self._head = (self._head + 1) % self._capacity
        self._size -= 1

        assert order is not None
        return order