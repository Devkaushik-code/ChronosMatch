import os
import tempfile
import unittest

from chronosmatch.ipc.mmap_ring_buffer import MmapRingBuffer


class TestMmapRingBuffer(unittest.TestCase):

    def test_fifo_and_wraparound(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "orders.bin")

            with MmapRingBuffer(path, 2) as buffer:
                buffer.put(1, 100, 5)
                buffer.put(2, 101, 6)

                self.assertEqual(buffer.get(), (1, 100, 5))

                buffer.put(3, 102, 7)

                self.assertEqual(buffer.get(), (2, 101, 6))
                self.assertEqual(buffer.get(), (3, 102, 7))
                self.assertTrue(buffer.is_empty)

    def test_empty_buffer_raises_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "orders.bin")

            with MmapRingBuffer(path, 2) as buffer:
                with self.assertRaises(BufferError):
                    buffer.get()

    def test_full_buffer_raises_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "orders.bin")

            with MmapRingBuffer(path, 1) as buffer:
                buffer.put(1, 100, 5)

                with self.assertRaises(BufferError):
                    buffer.put(2, 101, 6)

    def test_reopen_preserves_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "orders.bin")

            with MmapRingBuffer(path, 2) as buffer:
                buffer.put(101, 2500, 10)

            with MmapRingBuffer(path, 2, create=False) as buffer:
                self.assertEqual(buffer.get(), (101, 2500, 10))
                self.assertTrue(buffer.is_empty)

    def test_capacity_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "orders.bin")

            with MmapRingBuffer(path, 3):
                pass

            with self.assertRaisesRegex(
                ValueError, "capacity does not match"
            ):
                MmapRingBuffer(path, 2, create=False)

            # Confirm the file can still be reopened correctly.
            with MmapRingBuffer(path, 3, create=False) as buffer:
                self.assertTrue(buffer.is_empty)

    def test_invalid_capacity(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "orders.bin")

            with self.assertRaises(ValueError):
                MmapRingBuffer(path, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
