# Synthetic performance baseline

Measured locally on **14 October 2026**. These are observations on generated,
accepted grids, not performance guarantees, field-data validation, or measured
capacity at the resource guards.

## Results

| Traces | Samples/trace | File MiB | Median audit seconds | Min–max seconds | Maximum sampled tree RSS MiB |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1,000 | 256 | 1.21 | 0.0215 | 0.0213–0.0225 | 38.7 |
| 10,000 | 256 | 12.06 | 0.1176 | 0.1150–0.1179 | 40.7 |
| 100,000 | 256 | 120.55 | 1.1014 | 1.0754–1.2049 | 51.5 |
| 10,000 | 2,048 | 80.42 | 0.1896 | 0.1891–0.1901 | 40.9 |

Each row uses one discarded warm-up followed by five fresh-process repeats.
Audit time includes envelope inspection, all trace-header checks, and full input
SHA-256 hashing. Policy loading, imports, generation, and report rendering are
excluded. End-to-end process time is also retained in the raw results.

RSS is sampled every 5 ms over startup and auditing. It sums the process tree,
including the Windows virtual-environment launcher. Shared pages may be counted
twice; brief peaks may be missed. This is resident memory, not total allocated
or committed memory. The worker PID is recorded and must have been observed.
File caches are not flushed. Results therefore describe warmed local storage;
they do not measure cold disks, network filesystems, or other machines.

At a fixed 10,000 traces, an eightfold sample-count increase did not produce an
eightfold sampled-memory increase. This is consistent with scanning headers and
streaming the hash rather than loading amplitudes. The comparison does not prove
an asymptotic memory bound. The geometry set still grows with unique grid cells.

## Environment and reproducibility

Windows 11 build 26200; AMD64 Family 25 Model 68 Stepping 1; 8 physical/16 logical
CPUs; 16,369,315,840 bytes RAM; Python 3.12.14; segyio 1.9.14; NumPy 2.5.4;
psutil 7.2.2. No thread-count overrides were set. No application tests or builds
were run concurrently with the final measurements. Background OS activity was
not controlled.

The measured package source is revision `07c7542`. The baseline started with a
clean working tree. The longer-trace comparison records a dirty tree because
README, changelog, and packaging-documentation edits were present. Both raw files
record the same package-source SHA-256; no package code changed between them.

```sh
python -m pip install -e ".[benchmark]"
python -m segy_accept.benchmark benchmark-output --traces 1000 10000 100000 --samples 256 --repeats 5
python -m segy_accept.benchmark benchmark-output-long --traces 10000 --samples 2048 --repeats 5
```

Destinations must be new. Each suite refuses more than 512 MiB of generated data;
individual files and policies also obey the auditor's safety limits. Generation
writes one record at a time. Outputs contain synthetic data and may be removed
after retaining `results.json`. No download, account, GPU, or benchmark service
is required. Typical results should be compared across multiple runs on the same
machine and cache conditions before attempting an optimization.

Raw evidence: [baseline](evidence/benchmark-2026-10-14.json) and
[longer traces](evidence/benchmark-long-traces-2026-10-14.json).
They include every repeat, discarded warm-ups, fingerprints, source provenance,
process durations, sampling counts, and environment details.

## Measurement review

A development run monitored only the Windows launcher, understating memory.
Those figures were discarded. Inspection confirmed a separate Python child;
the implementation now measures the tree and rejects observations that missed
the worker. Timeout review also led to refreshing and terminating descendants,
including children not yet sampled. Regression tests cover these cases.
No optimization or speedup claim is made: this pass establishes a baseline.

The [psutil reference](https://psutil.readthedocs.io/stable/), accessed 14 October
2026, documents process RSS, recursive child discovery, and process waiting.
