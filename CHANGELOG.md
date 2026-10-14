# Changelog

## 0.1.0 — initial preview, 14 October 2026

- Actionable terminal summaries with prioritized findings, reasons, remedies, and report paths.
- Regular-file guards and bounded policy/hash reads that cannot follow a growing file indefinitely.
- Input replacement detection; changed or disappearing inputs invalidate fingerprints and passing findings.
- Independent ObsPy writer compatibility experiment with clean and contradictory fixtures.
- Optional isolated-process benchmark with raw repeats, fingerprints, machine details,
  sampled process-tree RSS, timeout cleanup, and a documented synthetic baseline.
- Regression coverage for benchmark validation, provenance, worker failures, and cleanup.
- Runtime auditing still requires only segyio and its dependencies.
- A pinned processed F3 field subvolume verified against an independent byte-level oracle.
- Windows/Linux quality workflows with clean-wheel checks, dependency audits,
  and an opt-in real-data workflow. 108 tests pass locally.
- Python 3.10 JSON nesting recovery and patched build-tool requirements.
- Security guidance, contribution instructions, and a practitioner review packet.

### Core functionality
- Read-only SEG-Y header acceptance against explicit sampling, coordinate and grid policies.
- Bounded explanatory findings, SHA-256 provenance, and offline JSON/HTML reports.
- Seven generated fixtures and an independently specified expected-results corpus.
- CLI exit codes separating acceptance, rejection, incomplete knowledge, and invocation errors.
- Regression tests, installable wheel, source distribution, and automated CI workflow.

This preview is published on GitHub with wheel/source assets; it is not published
to PyPI. Raw field data are not bundled. Broader producer validation, practitioner
review, and expanded format support remain future work.
