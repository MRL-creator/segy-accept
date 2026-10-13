# Quality floor

Established 14 October 2026 from the reviewed report and authorized first-release scope.

- No skipped tests, suppression comments, empty exception handlers, or unimplemented stubs.
- No source-file changes or unannounced partial acceptance.
- No secrets or third-party field datasets in the repository.
- Tests must use real SEG-Y bytes and real segyio, with a fixture oracle independent of segyio.
- Every supported rule has positive and negative/unknown cases as appropriate.
- Do not weaken this file or the support profile to make tests pass.

| Gate | Command | Where |
| --- | --- | --- |
| Behavior | `python -m pytest --cov=segy_accept --cov-report=term-missing` | Local and CI |
| Lint, no configured errors | `python -m ruff check .` | Local and CI |
| Consistent formatting | `python -m ruff format --check .` | Local and CI |
| Package build | `python -m build` | Local and CI |

Coverage and resource performance are measured, not assigned an invented baseline.
The first release does not promise the career report's proposed RSS/runtime targets.
The trace/cell guards are input-safety limits, not measured memory guarantees.
