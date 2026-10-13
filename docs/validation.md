# First-version verification

Verified locally on **14 October 2026**, Windows, Python 3.12.14,
segyio 1.9.14 and NumPy 2.5.4.

## Evidence collected

- **60 tests pass**, with **95% statement coverage** (385 statements, 18 not covered).
  Coverage is descriptive, not proof of scientific validity.
- Stdlib-generated fixture bytes open in real segyio; tests do not mock the parser.
- Clean, contradictory, truncated and unsupported files produce distinct outcomes.
- Repeated audits produce identical results and leave source bytes unchanged.
- A real-hardlink test verifies overwrite refusal when a report aliases an input.
- Unit and scalar checks run independently. Negative scalar division preserves the
  tested inclusive decimal boundary. Unknown metadata never becomes acceptance.
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

No controlled runtime/RSS benchmark or field-data study has been performed.
The resource guards are ceilings, not measured supported capacities. Future work:
measure increasing generated workloads, test with a separately produced licensed
file, obtain user feedback, and evaluate a focused upstream contribution.
These follow the career report's roadmap; they are not required to try this working
local first version.
