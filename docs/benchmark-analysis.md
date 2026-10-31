# ChronosMatch Benchmark Analysis

## 1. Purpose

This report summarizes the recorded matching-engine benchmarks for the
Python, original Cython, and optimized Cython implementations. It documents
performance observations, correctness checks, limitations, and next steps.

## 2. Three-way benchmark: 20,000 orders

The following figures come from
`benchmarks/results_engine_three_way_20000_15runs.json`.

| Metric | Python | Original Cython | Optimized Cython |
|---|---:|---:|---:|
| Mean throughput (orders/sec) | 169,543.32 | 159,496.75 | 163,448.81 |
| Median throughput (orders/sec) | 173,248.44 | 161,189.63 | 165,052.85 |
| Throughput standard deviation | 8,941.30 | 5,077.69 | 4,810.73 |
| Median p95 latency (microseconds) | 11.153 | 11.385 | 11.000 |

Recorded configuration: 20,000 orders per run, 15 measured runs, and one
warm-up run. The recorded environment was CPython 3.12.15 on Linux/AArch64.

## 3. Recorded comparisons

- All three engines passed the recorded cross-engine parity checks.
- Original Cython mean throughput was 5.93% below Python.
- Optimized Cython mean throughput was 3.59% below Python.
- Optimized Cython mean throughput was 2.48% above original Cython.
- Optimized Cython had the lowest recorded median p95 latency in this run.

These percentages are the values recorded in the benchmark result file.
They describe this workload and environment, not every possible deployment.

## 4. Additional recorded measurements

Other result files also report successful parity checks:

| Result file | Orders/run | Measured runs | Python mean throughput | Cython mean throughput |
|---|---:|---:|---:|---:|
| results_engine_baseline_5000.json | 5,000 | 5 | 182,202.75 | 167,391.58 |
| results_engine_comparison.json | 2,000 | 3 | 153,963.94 | 138,638.06 |
| results_engine_comparison_20000.json | 20,000 | 5 | 169,612.54 | 158,889.42 |
| results_engine_comparison_optimized.json | 2,000 | 3 | 150,164.37 | 134,473.77 |
| results_engine_localvars_20000.json | 20,000 | 5 | 161,728.92 | 160,037.53 |
| results_engine_localvars_repeat_20000.json | 20,000 | 5 | 157,329.50 | 147,616.73 |
| results_engine_original_localvars_comparison_20000.json | 20,000 | 5 | 160,349.65 | 146,161.40 |
| results_engine_smoke.json | 1,000 | 2 | 207,850.41 | 201,374.24 |

The measurements were collected in different runs, with different workload
sizes and configurations. They should not be treated as one controlled
head-to-head experiment or used to infer a trend across files.

## 5. Interpretation

### Correctness

Recorded parity checks are encouraging evidence that the implementations
produce matching results for the tested workloads. They do not prove
correctness for every possible order sequence or concurrency scenario.

### Performance

Python was faster than both Cython variants in the recorded three-way
20,000-order benchmark. The optimized Cython variant improved throughput
relative to the original Cython variant, but did not surpass Python.

The optimized variant's lower p95 latency in that run is a useful signal,
but it does not establish that it is consistently lower-latency under all
workloads.

### Variability

The reported standard deviations show that throughput varied between runs.
Benchmark conclusions should account for machine load, runtime behavior,
warm-up, and measurement overhead.

## 6. Recommended next steps

1. Keep the Python implementation as the measured performance baseline.
2. Preserve the existing JSON results so the experimental history remains
   available.
3. Repeat head-to-head comparisons under the same workload, environment,
   warm-up policy, and measurement procedure.
4. Investigate profiling results before making further low-level changes.
5. Run the correctness suite after each engine change.
6. Record compiler, Cython, Python, and platform versions for reproducibility.
7. Report both throughput and latency rather than choosing an implementation
   from a single metric.

## 7. Conclusion

ChronosMatch has three-way benchmark evidence and recorded parity checks for
the tested workload. The optimized Cython version improves on the original
Cython version in the 15-run comparison, but Python remains the throughput
leader in that experiment. Further optimization should be guided by profiling
and controlled, repeatable measurements.

This report summarizes existing results; it does not claim that a new
benchmark was run while preparing this document.
