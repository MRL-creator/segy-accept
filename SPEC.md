# SEG-Y acceptance auditor: first usable version

## Objective and authorization
Build the flagship selected from the 14 October 2026 career report. The user
reviewed that report, then asked to choose a doable project and start it.
This file records the report's narrow first-release contract and routine
implementation choices. No new approval gate is needed to begin that authorized work.

A geoscience developer should be able to explain why a local seismic file does
or does not meet a receiving workflow's declared assumptions. Acceptance means
passing the implemented rules only, not full standards compliance or scientific validity.

## Supported input and boundaries
- SEG-Y revision 1.0 (revision word 0x0100), big endian, format code 5,
  fixed-length traces, no extended textual headers. Standard CDP X/Y and
  inline/crossline fields only; header and policy checks, not amplitude QC.
  Sampling words must be positive signed 16-bit integers (1-32767), following
  revision-1 section 3.3; unsigned vendor extensions are outside the profile.
- Use released segyio 1.9.14 read-only, ignoring automatic geometry inference.
  Independent envelope inspection detects narrow-profile size errors before parsing.
- Policy: sampling expectations, explicit coordinate units/reference/bounds,
  optional Cartesian post-stack grid. No CRS guessing, repair, or reprojection.
- Missing policy dimensions produce unknown findings; they never silently pass.
- All traces are inspected. No sampled audit, remote downloads, dashboard,
  arbitrary header offsets, variable-length records, or revision-2 support.
- Source file SHA-256 and policy SHA-256, policy/schema/tool/reader versions,
  trace counts, examples, remedies, and scan completeness accompany each result.
- Bounded examples; geometry membership uses O(unique cells) memory.
  A 2 GiB file / one-million-trace / one-million-expected-cell guard bounds the initial release;
  resource limits give incomplete results, not partial acceptance.

## Contract and success criteria
`segy-accept audit INPUT --policy POLICY --out OUTPUT_DIRECTORY`
creates deterministic `audit.json` and self-contained `audit.html`.
Exit codes: 0 accepted, 1 rejected by a completed audit, 2 incomplete/unknown,
3 invalid invocation, policy, or output error. Findings use pass/warning/failure/unknown.
Rejected takes precedence over unknown only for a complete audit. Incomplete
input remains incomplete even if a detected structural defect is a failure.
No overwriting reports by default; `--overwrite` permits replacing only report
files after checking neither target aliases the source or policy.
Inputs and policies must be regular files. Bound policy reads to 1 MiB plus a
one-byte overflow probe and hashing to the initial file size plus one byte.
Compare device/inode, size, and modification time to detect ordinary replacement
or mutation. On detected instability, clear the fingerprint and coordinate
examples, mark the scan incomplete, and change passing rules to unknown.
This is best-effort detection; stable inputs remain required, with no atomic
snapshot guarantee. Terminal summaries prioritize failures, unknowns, and warnings,
include reasons/remedies and report paths; JSON and exit codes remain the machine contract.

Generated fixtures include clean, contradictory sampling, duplicate/missing cells,
coordinate scaling/unit/bounds cases, and unreadable/unsupported inputs. An independent
stdlib fixture writer supplies known header bytes; integration tests use real segyio.
Tests establish outcomes, input immutability, deterministic reports, bounded examples,
safe HTML escaping, and honest handling of unsupported/incomplete input.

## Stack, structure, style, and commands
Python, segyio, pytest; stdlib JSON/HTML and hashing. No server or network required at runtime.
`src/segy_accept/`: policy, envelope inspection, audit checks, reports, CLI, generated fixtures.
`tests/`: independent byte-level fixtures and behavior/integration tests.
`examples/`: small generated corpus, example policy, expected results, and report.
`docs/`: rule catalogue, decisions, validation notes and sources.

Use descriptive snake_case names, small functions, dataclasses for the policy,
and explicit statuses, e.g. `finding["status"] = "unknown"`.

Setup: `python -m pip install -e ".[dev]"`
Tests: `python -m pytest --cov=segy_accept --cov-report=term-missing`
Lint: `python -m ruff check .`
Format: `python -m ruff format --check .`
Build: `python -m build`
Demo: `python -m segy_accept demo demo-output`

## Build order
1. Policy/envelope contract and independent fixtures; fail-first tests.
2. Sampling/coordinate/geometry rules; real-parser tests and incomplete cases.
3. Reports/CLI/demo, end-to-end tests, clean-wheel install and documented limitations.

## Always / ask first / never
Always validate policy and file bounds, preserve source bytes, run relevant tests,
and explain partial knowledge. Ask before field-data redistribution, external publication,
or scope expansion. Never commit credentials, weaken failing checks, or imply full SEG-Y compliance.
No blocking product questions remain for this local first version.

## Evidence expansion (14 October 2026)
The user authorized continuing improvements. Add developer-only independent
ObsPy writer validation and isolated-process runtime/RSS measurements from the
report's roadmap. These do not widen the supported SEG-Y profile. Generated data
remain synthetic and locally owned; no third-party field data are redistributed.
Benchmark output records all repeats, sampling interval, environment, workload,
source revision, and timing scope. Generation and reporting are outside the timed
audit. Performance measurements are descriptive, not noisy CI timing gates.

## Release authorization (14 October 2026)
After reviewing the remaining release requirements, the user instructed "do it".
This authorizes publishing this repository and a tagged preview, executing remote
Windows/Linux checks, and validating a small openly licensed field sample locally.
The F3 raw subvolume stays excluded from Git and distributions; publish the oracle,
attributed source register, fingerprints, policy definitions, and audit results.
The user has no practitioner reviewer available. Prepare a review packet and retain
that limitation; automated review must never be presented as practitioner endorsement.

## Stable release scope (14 October 2026)
The user agreed to finish a stable version within the documented scope without
making another person's involvement a prerequisite. Verify two additional small
field examples, freeze the CLI/schema-1 consumer contract, and publish v1.0.0 only
after the existing quality gates and expanded field workflow pass. Practitioner
feedback is optional external evidence, not a release gate. Retain all technical
limits and preserve the archived v0.1.0 preview and its evidence.

An omitted or null sampling expectation means undeclared; default-expanded report
policies must be accepted as replay input. Add `--version` for installed-tool
identification. No SEG-Y layout or scientific-validation scope is expanded.
