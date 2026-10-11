"""Multiprocess producer-consumer correctness test for the mmap ring buffer."""

import fcntl
import multiprocessing as mp
import os
import tempfile
import time

from chronosmatch.ipc.mmap_ring_buffer import MmapRingBuffer


def producer(path, capacity, count, lock_path, result_queue):
    try:
        buffer = MmapRingBuffer(path, capacity, create=False)
        lock_fd = os.open(lock_path, os.O_RDWR)

        try:
            for order_id in range(count):
                while True:
                    with_lock = False
                    fcntl.flock(lock_fd, fcntl.LOCK_EX)
                    try:
                        if not buffer.is_full:
                            buffer.put(order_id, 1000 + order_id, 1)
                            with_lock = True
                    finally:
                        fcntl.flock(lock_fd, fcntl.LOCK_UN)

                    if with_lock:
                        break

                    time.sleep(0.0001)

            result_queue.put(("producer", count, None))
        finally:
            os.close(lock_fd)
            buffer.close()
    except Exception as exc:
        result_queue.put(("producer", 0, repr(exc)))


def consumer(path, capacity, count, lock_path, result_queue):
    received = 0
    try:
        buffer = MmapRingBuffer(path, capacity, create=False)
        lock_fd = os.open(lock_path, os.O_RDWR)

        try:
            while received < count:
                order = None
                fcntl.flock(lock_fd, fcntl.LOCK_EX)
                try:
                    if not buffer.is_empty:
                        order = buffer.get()
                finally:
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)

                if order is None:
                    time.sleep(0.0001)
                    continue

                expected = (received, 1000 + received, 1)
                if order != expected:
                    raise AssertionError(
                        f"FIFO/data mismatch at index {received}: "
                        f"expected {expected}, got {order}"
                    )

                received += 1

            result_queue.put(("consumer", received, None))
        finally:
            os.close(lock_fd)
            buffer.close()
    except Exception as exc:
        result_queue.put(("consumer", received, repr(exc)))


def main():
    count = 10_000
    capacity = 1024
    context = mp.get_context("spawn")
    result_queue = context.Queue()

    with tempfile.TemporaryDirectory(prefix="chronosmatch-") as directory:
        path = os.path.join(directory, "orders.mmap")
        lock_path = os.path.join(directory, "orders.lock")

        with open(lock_path, "wb"):
            pass

        with MmapRingBuffer(path, capacity, create=True):
            pass

        producer_process = context.Process(
            target=producer,
            args=(path, capacity, count, lock_path, result_queue),
        )
        consumer_process = context.Process(
            target=consumer,
            args=(path, capacity, count, lock_path, result_queue),
        )

        consumer_process.start()
        producer_process.start()

        producer_process.join(15)
        consumer_process.join(15)

        print(f"Producer alive: {producer_process.is_alive()}")
        print(f"Producer exit code: {producer_process.exitcode}")
        print(f"Consumer alive: {consumer_process.is_alive()}")
        print(f"Consumer exit code: {consumer_process.exitcode}")

        if producer_process.is_alive():
            producer_process.terminate()
            producer_process.join()

        if consumer_process.is_alive():
            consumer_process.terminate()
            consumer_process.join()

        if producer_process.exitcode is None or consumer_process.exitcode is None:
            raise RuntimeError("Could not determine process exit status")

        if producer_process.exitcode != 0 or consumer_process.exitcode != 0:
            raise RuntimeError(
                f"Process failure: producer={producer_process.exitcode}, "
                f"consumer={consumer_process.exitcode}"
            )

        print("Both worker processes exited successfully.")
        results = [result_queue.get(timeout=5) for _ in range(2)]

        errors = [item for item in results if item[2] is not None]
        if errors:
            raise RuntimeError(f"Worker error(s): {errors}")

        producer_result = next(item for item in results if item[0] == "producer")
        consumer_result = next(item for item in results if item[0] == "consumer")
        received_count = consumer_result[1]

        if producer_result[1] != count:
            raise AssertionError("Producer did not send all orders")

        if received_count != count:
            raise AssertionError(
                f"Expected {count} orders, received {received_count}"
            )

        print("Multiprocess mmap IPC test: PASS")
        print(f"Orders sent:     {producer_result[1]:,}")
        print(f"Orders received: {received_count:,}")
        print("FIFO ordering:   PASS")
        print("Data integrity:  PASS")
        print("Processes:       producer + consumer")


if __name__ == "__main__":
    main()
