# ChronosMatch

ChronosMatch is a Python-based low-latency trading engine project featuring a limit order book, memory-mapped IPC, market simulation, and latency monitoring.

## Features

- Python limit order matching engine.
- Cython matching-engine implementations.
- Matching behavior and parity tests.
- Ring buffers and memory-mapped IPC.
- Multiprocess producer-consumer tests.
- Market simulation and pipeline processing.
- SQLite trade ledger and latency tracking.
- Order cancellation with price-time priority preservation.
- Authenticated Flask web dashboard.
- Benchmark scripts and performance analysis.

## Project Structure

    ChronosMatch/
    ├── benchmarks/
    ├── docs/
    ├── src/chronosmatch/
    │   ├── ipc/
    │   ├── matching_engine.py
    │   ├── matching_engine_cython.pyx
    │   ├── market_pipeline.py
    │   ├── market_simulator.py
    │   ├── trade_ledger.py
    │   └── trading_pipeline.py
    ├── tests/
    ├── web_dashboard/
    │   ├── app.py
    │   ├── auth.py
    │   ├── static/
    │   └── templates/
    ├── setup.py
    └── setup_ab.py

## Requirements

- Python 3.10 or later
- pip
- setuptools
- Cython
- Flask
- A compatible C compiler

## Installation

Clone the repository:

    git clone https://github.com/Devkaushik-code/ChronosMatch.git
    cd ChronosMatch

Install dependencies:

    python3 -m pip install --upgrade pip setuptools Cython Flask

## Build Cython Extensions

    python3 setup.py build_ext --inplace
    python3 setup_ab.py build_ext --inplace

Generated binaries may depend on the operating system, Python version, and CPU architecture.

## Run Tests

    PYTHONPATH=src python3 -m unittest discover -s tests -v

Build the Cython extensions first if Cython-specific tests require them.

## Benchmarks

Benchmark scripts are located in the benchmarks directory.

For meaningful comparisons, use the same machine, Python version, workload, and build settings. Repeat measurements and compare medians or distributions.

A successful test run confirms correctness for tested cases; it does not prove that Cython is faster.

See docs/benchmark-analysis.md for recorded benchmark results and analysis.

## Order Cancellation

The Python matching engine supports cancellation by order ID.

- Cancels open buy and sell orders.
- Supports partially filled orders.
- Preserves the price-time priority of remaining orders.
- Returns False if the order ID is not found.

## Web Dashboard

ChronosMatch includes an authenticated Flask dashboard.

### Features

- User registration and login.
- User-specific trading data.
- Buy and sell order submission.
- Order book display.
- Open-order cancellation.
- Recent trade history.
- Market simulation.
- Benchmark comparison cards and charts.

### Run the Dashboard

Install Flask:

    python3 -m pip install Flask

Start the dashboard:

    python3 web_dashboard/app.py

Open in your browser:

    http://127.0.0.1:5000

The dashboard uses a local secret key and SQLite databases. These private files are excluded from Git using .gitignore.

**Security note:** The included Flask development server is intended for local testing and evaluation, not production deployment.

## Project Status

This project is under active development for learning, experimentation, and evaluation. It has not been established as a production-ready trading system. Benchmark results should be independently reproduced before making performance claims.

## License

No license has been specified yet.
