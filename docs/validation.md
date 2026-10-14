# Local verification

Verified locally on **14 October 2026**, Windows, Python 3.12.14,
segyio 1.9.14 and NumPy 2.5.4.

Current snapshot: **106 tests pass**, with **90% statement coverage** across the
core auditor and optional developer experiments (701 statements, 69 not covered).
Ruff checks and formatting pass; wheel and source-distribution builds succeed.
The dependency audit includes the newly installed ObsPy/psutil stack and reports
no known vulnerabilities. These checks ran on Windows/Python 3.12 only.
The updated wheel's seven-case demo also runs from outside the source directory
in a separate environment with neither ObsPy nor psutil installed.

## Evidence collected

- The full test suite covers the audit contract, independent writer, and benchmark
  behavior. Coverage is descriptive, not proof of scientific validity.
- Stdlib-generated fixture bytes open in real segyio; tests do not mock the parser.
- Clean, contradictory, truncated and unsupported files produce distinct outcomes.
- Repeated audits produce identical results and leave source bytes unchanged.
- A real-hardlink test verifies overwrite refusal when a report aliases an input.
- Unit and scalar checks run independently. Negative scalar division preserves the
  tested inclusive decimal boundary. Unknown metadata never becomes acceptance.
- Input-safety regressions cover same-size/timestamp file replacement, mutation,
  disappearance, nonregular inputs, hashing growth, and policy growth. Changed inputs
  invalidate the fingerprint and passing checks; coordinate examples are cleared.
  Checks use file identity/size/mtime and are not an atomic snapshot guarantee.
- Terminal summaries explain failures, unknowns, warnings, unsupported profiles,
  and report paths. Inverting the incomplete-scan display condition made its focused
  regression fail; the source was restored before final verification.
- Bounded examples retain evidence at the highest encountered severity; event counts
  continue after the cap.
- High-bit sampling words are rejected under the documented signed revision-1 profile.
  The original proposed unsigned-acceptance test was corrected after checking
  revision-1 section 3.3, then a failing regression was written for the actual contract.
- Deliberately inverting the coordinate-bounds condition made its focused regression
  test fail. The original source was restored before final verification.
- The committed seven-file corpus and checked-in sample JSON/HTML reproduce current
  tool output. No field data or adoption claim is involved.
- The report was inspected in a real browser at desktop and 390-pixel viewport widths.
  It had no horizontal overflow, scripts, or external asset requests. The rule link
  navigated to the correct evidence section.
- Local package build succeeds. Wheel installation is checked in a separate environment
  and the demo is exercised from outside the source directory.
- `pip-audit --skip-editable` found no known vulnerabilities in the resolved installed
  dependencies at this snapshot. It skips the original editable package, and does not
  establish absence of unknown vulnerabilities or native-parser memory-safety defects.

## Commands

```sh
python -m pytest --cov=segy_accept --cov-report=term-missing
python -m ruff check .
python -m ruff format --check .
python -m build
python -m segy_accept demo demo-output
python -m pip_audit --skip-editable --progress-spinner off
```

In the restricted local environment, pytest used `--basetemp=.pytest-work`.
The hardlink check required running outside the restricted filesystem sandbox.
No test was skipped or weakened to work around that environment.

## Remaining evidence to collect

The GitHub Actions workflow is prepared but has not run remotely. Linux and other
Python versions remain unverified locally. The test fixtures do not represent
all producer variants, real survey semantics, or an independently certified SEG-Y writer.

No field-data study has been performed. The resource guards are ceilings, not
measured supported capacities. Future work: obtain a legally usable field sample,
collect user feedback, and evaluate a focused upstream contribution.
These follow the career report's roadmap; they are not required to try this working
local first version.

## Independent writer experiment

The optional validation module uses the public ObsPy `Stream.write` interface,
with float32 arrays and explicit standard headers. It does not use our byte
writer or segyio's writer. ObsPy 1.5.1 writes two four-trace files: a clean
Cartesian grid and a duplicate-cell variant. The auditor accepts the first and
rejects the second, identifying both the duplicate and the missing cell.
Tests independently inspect header bytes, read sample values back through ObsPy,
and verify source immutability and fingerprint matching.

```sh
python -m pip install -e ".[validation]"
python -m segy_accept.validation independent-output
```

The arrays and generated files are our synthetic MIT fixtures. ObsPy itself is a
separate LGPL-3.0 dependency. This verifies compatibility with one independent
software writer, not real survey semantics or certified standards compliance.
Evidence: [writer manifest](evidence/independent-writer.json),
[clean audit](evidence/obspy-clean-audit.json), and
[contradictory audit](evidence/obspy-duplicate-audit.json).
The command regenerates files and offline HTML reports in a new directory.

Sources, accessed 14 October 2026: [ObsPy SEG-Y support and licence](https://docs.obspy.org/packages/obspy.io.segy.html)
and [writer API](https://docs.obspy.org/packages/autogen/obspy.io.segy.core._write_segy.html).
The auditor retains its narrower signed revision-1 sampling profile even though
the writer supports a wider interval range.

## Performance evidence

[The baseline](benchmarks.md) records five repeats at 1,000, 10,000, and 100,000
traces, plus a fixed-trace-count comparison with longer payloads. Raw evidence
contains environment details, all timings, sampled process-tree RSS, and hashes.
No noisy timing threshold is imposed in CI. Tests check measurement correctness,
invalid workloads, optional Git metadata, worker failures, and timeout cleanup.
