# Changelog

## Unreleased - local improvements, 14 October 2026

- Independent ObsPy writer compatibility experiment with clean and contradictory fixtures.
- Optional isolated-process benchmark with raw repeats, fingerprints, machine details,
  sampled process-tree RSS, timeout cleanup, and a documented synthetic baseline.
- Regression coverage for benchmark validation, provenance, worker failures, and cleanup.
- Runtime auditing still requires only segyio and its dependencies.

## 0.1.0 - local first version, 14 October 2026

### Added
- Read-only SEG-Y header acceptance against explicit sampling, coordinate and grid policies.
- Bounded explanatory findings, SHA-256 provenance, and offline JSON/HTML reports.
- Seven generated fixtures and an independently specified expected-results corpus.
- CLI exit codes separating acceptance, rejection, incomplete knowledge, and invocation errors.
- Regression tests, installable wheel, source distribution, and prepared CI workflow.

This version is local and has not been published to GitHub or PyPI. Field validation
and expanded format support remain future work. Initial performance evidence appears
in the unreleased improvements above.
