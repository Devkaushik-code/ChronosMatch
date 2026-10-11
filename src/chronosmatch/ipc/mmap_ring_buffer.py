"""Memory-mapped ring buffer prototype for ChronosMatch IPC."""

import mmap
import os
import struct


# Header: capacity, head, tail, size.
_HEADER = struct.Struct("<IIII")

# Order: order_id, price, quantity.
_ORDER = struct.Struct("<QqQ")


class MmapRingBuffer:
    """Fixed-capacity ring buffer backed by a memory-mapped file.

    This is a single-process prototype.
    Inter-process synchronization is not implemented.

    WARNING:
        create=True initializes and resets the file.
        Use create=False to reopen an existing buffer.
    """

    def __init__(self, path: str, capacity: int, create: bool = True):
        if not 1 <= capacity <= 0xFFFFFFFF:
            raise ValueError("capacity must be between 1 and 2**32 - 1")

        self.path = path
        self.capacity = capacity
        self._slot_size = _ORDER.size
        self._data_offset = _HEADER.size
        self._file_size = self._data_offset + capacity * self._slot_size

        self._fd = None
        self._map = None

        flags = os.O_RDWR | os.O_CREAT if create else os.O_RDWR
        self._fd = os.open(path, flags, 0o600)

        try:
            if create:
                os.ftruncate(self._fd, self._file_size)
            elif os.fstat(self._fd).st_size < self._file_size:
                raise ValueError("mapped file is smaller than expected")

            self._map = mmap.mmap(
                self._fd,
                self._file_size,
                access=mmap.ACCESS_WRITE,
            )

            if create:
                _HEADER.pack_into(self._map, 0, capacity, 0, 0, 0)
            else:
                stored_capacity, head, tail, size = _HEADER.unpack_from(
                    self._map, 0
                )

                if stored_capacity != capacity:
                    raise ValueError("capacity does not match mapped file")

                if (
                    head >= capacity
                    or tail >= capacity
                    or size > capacity
                ):
                    raise ValueError("mapped file contains an invalid header")

        except Exception:
            if self._map is not None:
                self._map.close()
                self._map = None

            if self._fd is not None:
                os.close(self._fd)
                self._fd = None

            raise

    def _header(self):
        return _HEADER.unpack_from(self._map, 0)

    @property
    def size(self) -> int:
        return self._header()[3]

    @property
    def is_empty(self) -> bool:
        return self.size == 0

    @property
    def is_full(self) -> bool:
        return self.size == self.capacity

    def put(self, order_id: int, price: int, quantity: int) -> None:
        """Write one order into the next available slot."""
        stored_capacity, head, tail, size = self._header()

        if size >= stored_capacity:
            raise BufferError("ring buffer is full")

        offset = self._data_offset + tail * self._slot_size

        _ORDER.pack_into(
            self._map, offset, order_id, price, quantity
        )

        tail = (tail + 1) % stored_capacity

        _HEADER.pack_into(
            self._map, 0, stored_capacity, head, tail, size + 1
        )

    def get(self) -> tuple[int, int, int]:
        """Read and remove the oldest order."""
        stored_capacity, head, tail, size = self._header()

        if size == 0:
            raise BufferError("ring buffer is empty")

        offset = self._data_offset + head * self._slot_size
        order = _ORDER.unpack_from(self._map, offset)

        head = (head + 1) % stored_capacity

        _HEADER.pack_into(
            self._map, 0, stored_capacity, head, tail, size - 1
        )

        return order

    def close(self) -> None:
        """Close the mapping and file descriptor."""
        if self._map is not None:
            self._map.close()
            self._map = None

        if self._fd is not None:
            os.close(self._fd)
            self._fd = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
