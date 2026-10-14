# v0.1.0 preview release evidence

Prepared **14 October 2026** for a public scientific-software portfolio.
This release is a usable preview for the stated receiving profile. It is not a
claim of broad industrial validation or practitioner endorsement.

| Requirement | Evidence |
| --- | --- |
| Behavioral checks | 108 passing tests locally; [remote quality matrix](https://github.com/MRL-creator/segy-accept/actions/workflows/ci.yml) checks Linux/Python 3.10 and 3.12, Windows/Python 3.12 |
| Distribution | Wheel and source archive build; each CI job installs the wheel in a new environment outside the source tree, with only runtime dependencies, then exercises all seven demo outcomes |
| Real data | [F3 oracle and three outcomes](field-validation/README.md), 40,401 traces; [Windows/Linux field run](https://github.com/MRL-creator/segy-accept/actions/runs/38548998666) |
| Independent writer | ObsPy clean/duplicate experiments and byte-level fixtures, covered by tests |
| Resource evidence | [Raw benchmark repeats and limits](benchmarks.md); no unmeasured speedup or capacity claim |
| Supply chain | Resolved dependencies audited in each CI job; action revisions pinned; patched setuptools build requirement |
| Code review | Separate model reviewed input safety, CLI, measurement, field oracle, and packaging; actionable findings were fixed and rechecked |
| User documentation | [README](../README.md), [rules](rules.md), [contributing](../CONTRIBUTING.md), [security](../SECURITY.md), and [changelog](../CHANGELOG.md) |
| Practitioner assessment | **Pending**; no reviewer is available. [Review packet](practitioner-review.md) is ready |

The initial remote failures remain visible in history: one Python 3.10 JSON
decoder crash and one old runner build-tool vulnerability. Both were repaired
without skipping tests, ignoring vulnerabilities, or reducing declared support.
The [three-job quality run](https://github.com/MRL-creator/segy-accept/actions/runs/38548992535)
and two-job field run both passed on source revision `b97e88d`. Final package and
documentation changes are rechecked by the quality workflow before tagging.

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

Download the wheel from the [v0.1.0 release](https://github.com/MRL-creator/segy-accept/releases/tag/v0.1.0)
and install it in a virtual environment. Run `python -m segy_accept demo demo-output`
with a new destination; compare the seven outcomes with the manifest. Release
assets include SHA-256 checksums. Nothing is published to PyPI by this release.

If a release produces misleading findings, stop relying on its acceptance decision,
retain the input/policy fingerprints and reports, and report a minimal synthetic
reproduction. Install a reviewed replacement in a separate environment and rerun
the same stable inputs. The tool never repairs or modifies input surveys, so no
data migration or reversal of source-file edits is required. Do not overwrite
existing evidence when comparing releases.
