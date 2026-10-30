# ChronosMatch

ChronosMatch is a Python-based low-latency trading engine project featuring a limit order book, memory-mapped IPC, market simulation, and latency monitoring.

## Features

- Limit order matching engine implemented in Python.
- Cython matching-engine implementations for performance experiments.
- Tests comparing matching behavior across implementations.
- Ring buffers and memory-mapped IPC for producer-consumer communication.
- Multiprocess IPC correctness tests.
- Market simulation and pipeline processing.
- SQLite-based trade ledger.
- Pipeline latency tracking and benchmark scripts.

## Project Structure

```text
ChronosMatch/
├── benchmarks/                 # Benchmark scripts and experimental results
├── src/chronosmatch/            # Main package
│   ├── ipc/                     # Ring buffers and memory-mapped IPC
│   ├── matching_engine.py       # Python matching engine
│   ├── matching_engine_cython.pyx
│   ├── matching_engine_cython_original.pyx
│   ├── matching_engine_cython_optimized.pyx
│   ├── market_pipeline.py
│   ├── market_simulator.py
│   ├── trade_ledger.py
│   └── trading_pipeline.py
├── tests/                       # Unit, integration, and parity tests
├── setup.py                     # Main Cython extension build
└── setup_ab.py                  # Additional Cython variants build
```

## Requirements

- Python 3.10 or later recommended
- pip
- setuptools
- Cython
- A C compiler compatible with the Python environment

## Installation

Clone the repository and enter its directory:

```bash
git clone https://github.com/Devkaushik-code/ChronosMatch.git
cd ChronosMatch
```

Install the build dependencies:

```bash
python3 -m pip install --upgrade pip setuptools Cython
```

## Build Cython Extensions

Build the primary matching-engine extension:

```bash
python3 setup.py build_ext --inplace
```

Build the original and optimized experimental variants:

```bash
python3 setup_ab.py build_ext --inplace
```

The build commands generate local C source, HTML annotation, and compiled extension files. Generated binaries may be specific to the operating system, Python version, and CPU architecture.

## Run Tests

From the repository root:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Build the Cython extensions before running the full suite if Cython-specific tests require them.

## Benchmarks

Benchmark scripts are located in `benchmarks/`. Run the relevant script from the repository root and preserve its output for comparison.

For meaningful performance comparisons, use the same machine, Python version, workload, and build settings. Repeat measurements and compare medians or distributions. A successful test run confirms correctness for the tested cases; it does not establish that a Cython implementation is faster.

## Project Status

This repository is under active development and is intended for learning, experimentation, and evaluation. It has not been established as a production-ready trading system. Benchmark results should be independently reproduced before making performance claims.

## License

No license has been specified yet.
