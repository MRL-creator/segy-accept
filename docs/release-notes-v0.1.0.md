# SEG-Y acceptance auditor — v0.1.0 preview

A SEG-Y file can open successfully while its sampling headers or declared grid
contradict the receiving workflow. This read-only tool explains those differences
with reproducible JSON findings, offline HTML reports, and actionable terminal summaries.

The initial profile is revision 1.0, big-endian, fixed-length IEEE format 5, with no
extended textual headers and standard CDP/inline/crossline fields. Acceptance
means agreement with implemented rules and the declared policy, not full SEG-Y
conformance or scientific validity.

## Evidence

- 108 passing local tests, including input immutability, safe output destinations,
  bounded evidence, malformed policies, and explicit incomplete states.
- Windows/Python 3.12 and Linux/Python 3.10/3.12 quality checks, with dependency audits
  and clean-wheel installations that exercise all seven demo outcomes.
- Independent ObsPy writer experiment and a pinned Netherlands F3 processed field
  subvolume: 40,401 headers compared with a stdlib oracle. The declared workflow is
  accepted, a wrong sampling interval is rejected, and an undeclared grid is incomplete.
- The field experiment passes on both Windows and Linux. Raw field data are excluded.
- Repeatable synthetic performance measurements, raw timings, and sampled memory.

See [release evidence](https://github.com/MRL-creator/segy-accept/blob/v0.1.0/docs/release-readiness.md)
and the [field source register](https://github.com/MRL-creator/segy-accept/blob/v0.1.0/docs/field-validation/README.md).

## Install and try

Install the attached wheel in a Python virtual environment:

```sh
python -m pip install segy_accept-0.1.0-py3-none-any.whl
python -m segy_accept demo demo-output
```

The destination must be new. Open `demo-output/readable-broken/audit.html`.
`SHA256SUMS` covers the attached wheel and source archive. Runtime requirements
remain segyio and its dependencies; ObsPy and psutil are optional developer extras.
This release is available on GitHub, not PyPI.

## Known limits

Only one processed field export has been validated. Its source says Unlocated XY;
the receiving policy uses that numeric basis and infers no EPSG. Broader producer
coverage, scientific calibration, hostile-input isolation, macOS, and other Python
versions remain unverified. File stability checks are best effort.

**Practitioner review is pending.** No domain expert has endorsed this preview.
A review packet is included. The supported profile and known limitations are
deliberately explicit so the work can be assessed as a scientific-software portfolio project.
