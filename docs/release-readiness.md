# v1.0.0 stable release evidence

Prepared **14 October 2026** for a public scientific-software portfolio.
This release stabilizes the [CLI and schema-1 contract](interface-contract.md)
for the stated receiving profile. Stable describes that tested compatibility
promise, not universal SEG-Y support or practitioner endorsement.

| Requirement | Evidence |
| --- | --- |
| Behavioral checks | 122 passing tests locally, including installed CLI/JSON consumer checks; [remote quality matrix](https://github.com/MRL-creator/segy-accept/actions/workflows/ci.yml) checks Linux/Python 3.10 and 3.12, Windows/Python 3.12 |
| Distribution | Wheel and source archive build; each CI job installs the wheel in a new environment outside the source tree, with only runtime dependencies, then exercises all seven demo outcomes |
| Real data | [Independent oracles and eight outcomes](field-validation/README.md) across F3 amplitude, F3 similarity, and legacy NPRA; [Windows/Linux field workflow](https://github.com/MRL-creator/segy-accept/actions/workflows/field-validation.yml) |
| Independent writer | ObsPy clean/duplicate experiments and byte-level fixtures, covered by tests |
| Resource evidence | [Raw benchmark repeats and limits](benchmarks.md); no unmeasured speedup or capacity claim |
| Supply chain | Resolved dependencies audited in each CI job; action revisions pinned; patched setuptools build requirement |
| Code review | Separate model reviewed input safety, CLI, measurement, field oracle, and packaging; actionable findings were fixed and rechecked |
| User documentation | [README](../README.md), [rules](rules.md), [contributing](../CONTRIBUTING.md), [security](../SECURITY.md), and [changelog](../CHANGELOG.md) |
| Optional practitioner assessment | **Pending, not a release gate**. [Review packet](practitioner-review.md) is ready; no endorsement is claimed |

The preview's initial remote failures remain visible in history: one Python 3.10 JSON
decoder crash and one old runner build-tool vulnerability. Both were repaired
without skipping tests, ignoring vulnerabilities, or reducing declared support.
The archived [v0.1.0 final quality run](https://github.com/MRL-creator/segy-accept/actions/runs/38549679091)
and [original field run](https://github.com/MRL-creator/segy-accept/actions/runs/38548998666)
remain available. The stable candidate reruns both workflows with the expanded
field cases and consumer contract before tagging. The v0.1.0 release remains
unchanged as historical evidence.

## Known limitations

- Only revision 1.0, big-endian, fixed-length IEEE format 5, no extended textual
  headers, and standard CDP/inline/crossline fields. Signed sampling words are
  restricted to 1–32767. Unsupported layouts remain incomplete.
- The F3 source is a processed export with an explicitly unlocated numeric XY
  basis. No EPSG, navigation accuracy, scientific calibration, amplitude quality,
  or geological interpretation is validated.
- Grid checks assume one trace per explicitly declared Cartesian post-stack cell.
  They are not appropriate for every sparse, prestack, or irregular survey.
- File-change detection is best effort. Use stable copies; there is no atomic
  snapshot, filesystem lock, or hostile-native-parser sandbox.
- Memory grows with unique grid cells; input safety ceilings are not measured
  guarantees. Benchmarks cover selected synthetic workloads on one laptop.
- Python 3.10 and 3.12 are the tested matrix. Other Python versions and macOS are
  not verified by this release.

## Install, verify, and recover

Download the wheel from the [v1.0.0 release](https://github.com/MRL-creator/segy-accept/releases/tag/v1.0.0)
and install it in a virtual environment. Run `python -m segy_accept demo demo-output`
with a new destination; compare the seven outcomes with the manifest. Release
assets include SHA-256 checksums. Nothing is published to PyPI by this release.

If a release produces misleading findings, stop relying on its acceptance decision,
retain the input/policy fingerprints and reports, and report a minimal synthetic
reproduction. Install a reviewed replacement in a separate environment and rerun
the same stable inputs. The tool never repairs or modifies input surveys, so no
data migration or reversal of source-file edits is required. Do not overwrite
existing evidence when comparing releases.
