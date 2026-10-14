# SEG-Y acceptance auditor — v1.0.0

The first stable release defines a tested CLI, policy, and schema-1 JSON contract
for revision-1, big-endian, fixed-length IEEE SEG-Y datasets with standard header
fields. It explains why a file meets, contradicts, or cannot establish a receiving
workflow's declared assumptions. It does not infer scientific validity or a CRS.

## Changes from the preview

- Default-expanded report policies now replay correctly when sampling expectations
  were undeclared. Omission and null both mean undeclared; unknown knowledge still
  prevents acceptance.
- `segy-accept --version` identifies the installed release.
- Consumer contract tests exercise seven CLI outcomes, stable JSON field types,
  rule IDs, exit codes, policy hashes, and package-version consistency.
- Eight field scenarios cover three processed files. The F3 similarity volume
  contains a smaller grid than its filename suggests: a filename-extent receiving
  policy reports 12,515 missing cells, while its observed rectangle is accepted.
  A legacy IBM-float NPRA file remains explicitly unsupported/incomplete.
- Sampling experiments require specific sampling-failure evidence, and wheel
  checks identify the current version even when older artifacts remain.

122 local tests pass. The release is gated by Windows/Python 3.12 and Linux/Python
3.10/3.12 quality checks, clean-wheel installs, dependency audits, and an expanded
Windows/Linux field workflow. Raw field files are not redistributed. The original
v0.1.0 preview and its evidence remain archived unchanged.

## Install and try

Install the attached wheel in a Python virtual environment:

```sh
python -m pip install segy_accept-1.0.0-py3-none-any.whl
segy-accept --version
python -m segy_accept demo demo-output
```

The destination must be new. Open `demo-output/readable-broken/audit.html`.
The release also contains an offline sample report, source archive, and checksums.
Normal auditing requires segyio and its dependencies; developer extras remain optional.

See the [stable interface contract](https://github.com/MRL-creator/segy-accept/blob/v1.0.0/docs/interface-contract.md),
[release evidence and limits](https://github.com/MRL-creator/segy-accept/blob/v1.0.0/docs/release-readiness.md),
and [field source register](https://github.com/MRL-creator/segy-accept/blob/v1.0.0/docs/field-validation/README.md).

## Scope of stability

Existing commands/options, exit meanings, rule IDs, and JSON field types are
maintained throughout v1; additive fields may appear. Correctness/security fixes
are documented with regressions. Unsupported layouts and unresolved metadata
remain incomplete. The tool requires stable trusted files and does not promise
atomic snapshots, hostile-native-parser isolation, amplitude QC, or calibration.
Only the stated Windows/Linux Python matrix is verified.

Practitioner feedback is optional external evidence and remains unavailable.
No endorsement is claimed. It is not a prerequisite for this bounded stable release.
