import unittest

from src.chronosmatch.ipc.ring_buffer import Order, RingBuffer


class TestRingBuffer(unittest.TestCase):
    def test_fifo_order(self):
        buffer = RingBuffer(3)
        first = Order(1, 100, 10)
        second = Order(2, 101, 20)

        buffer.put(first)
        buffer.put(second)

        self.assertEqual(buffer.get(), first)
        self.assertEqual(buffer.get(), second)
        self.assertTrue(buffer.is_empty)

    def test_full_buffer_raises_error(self):
        buffer = RingBuffer(1)
        buffer.put(Order(1, 100, 10))

        with self.assertRaises(BufferError):
            buffer.put(Order(2, 101, 20))

    def test_empty_buffer_raises_error(self):
        buffer = RingBuffer(2)

        with self.assertRaises(BufferError):
            buffer.get()

    def test_wraparound(self):
        buffer = RingBuffer(2)
        first = Order(1, 100, 10)
        second = Order(2, 101, 20)
        third = Order(3, 102, 30)

        buffer.put(first)
        buffer.put(second)
        self.assertEqual(buffer.get(), first)

        buffer.put(third)

        self.assertEqual(buffer.get(), second)
        self.assertEqual(buffer.get(), third)

    def test_invalid_capacity(self):
        with self.assertRaises(ValueError):
            RingBuffer(0)


if __name__ == "__main__":
    unittest.main()