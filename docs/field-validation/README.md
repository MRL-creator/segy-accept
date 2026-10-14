# Field-data validation — 14 October 2026

The first experiment uses a **processed field-data subvolume**, not a generated fixture:
the F3 dip-steered median-filter amplitude volume from
[Equinor's example repository](https://github.com/equinor/segyio-notebooks/tree/c93e02027ea31d699b65be611f2747cc78cc967e/data/basic).
The source is pinned to commit `c93e02027ea31d699b65be611f2747cc78cc967e`.
Only its 17,941,644-byte subvolume was downloaded, rather than the full survey.

## Independent oracle and outcomes

The [reproduction script](../../tools/validate_f3.py) uses stdlib byte offsets
independent of segyio and the auditor's reader. It verifies the source hash,
binary profile, every trace's sampling/scalar/units, and the filename's Cartesian
grid: inlines 230–430, crosslines 475–675. It finds **40,401 unique cells**, with
51 samples per trace at 4,000 microseconds. All trace scalars are -10. Unit code 1
and binary measurement system 1 establish metres within the receiving convention.
Scaled extents are X 609,978.4–615,116.1 and Y 6,076,927.2–6,082,064.9.

| Receiving policy | Expected and observed result |
| --- | --- |
| Declared sampling, broad numeric XY bounds, and filename grid | Accepted |
| Same workflow, interval incorrectly declared as 2,000 microseconds | Rejected |
| Same workflow, grid expectation omitted | Incomplete |

All three audits inspect all 40,401 headers. The full source SHA-256 matches
before and after. The dataset itself is never edited to make it pass.
Evidence: [manifest and independent observations](manifest.json),
[accepted](accepted.json), [rejected](rejected.json), [incomplete](incomplete.json).
Each report embeds the complete receiving-policy definition.

## Reproduce

From a source checkout with the package installed:

```sh
python tools/validate_f3.py --download
```

This explicitly downloads the pinned sample into ignored `.field-data/`, checks
its fixed size/SHA-256, then writes three JSON/HTML reports under
`.field-data/f3-results/`. With an existing sample, omit `--download`. The report
destination must be new. The separately dispatched
[field workflow](../../.github/workflows/field-validation.yml) runs this experiment
on Linux and Windows. Routine unit tests do not require this download.

## Attribution and limits

Equinor's [README](https://github.com/equinor/segyio-notebooks/blob/c93e02027ea31d699b65be611f2747cc78cc967e/README.md)
identifies its F3 volumes as **CC-BY-SA**, without specifying a licence version.
The original seismic is credited to NAM/NLOG; dGB Earth Sciences made the F3 data
available through its Open Seismic Repository/TerraNubis, and Equinor distributed
this example subvolume. Thank you to these providers. The
[current F3 overview](https://terranubis.com/datainfo/F3-Demo-2023) supplies broader
survey context; its 2023 value-added package is not the exact 2019 export used here.
Sources accessed 14 October 2026. Raw data and amplitudes are not redistributed or
relicensed under this project's MIT licence.

The source textual header explicitly says **Unlocated XY**. The policy deliberately
declares only that supplied numeric basis, with no EPSG inference. Bounds are a
receiving-workflow choice, not independently verified navigation or calibration.
Acceptance does not validate amplitudes, geology, acquisition quality, or CRS.
One processed export does not establish compatibility with all producers.
A geoscience practitioner's review remains outstanding.

## Expanded v1.0 validation

Two further files from the same pinned Equinor distribution add a smaller F3
attribute volume and a legacy 2D NPRA line. They are independent files, not three
independent acquisition projects or three independently certified writers.

| Sample | Bytes | Independent observations | Checked outcomes |
| --- | ---: | --- | --- |
| F3 amplitude | 17,941,644 | 40,401 cells, inlines 230–430, crosslines 475–675 | Accepted declared workflow; wrong sampling rejected; missing grid expectation incomplete |
| F3 similarity | 12,384,984 | 27,886 cells, inlines 230–420, crosslines 475–620 | Filename-extent policy rejected; observed-rectangle policy accepted; wrong sampling rejected; undeclared grid incomplete |
| NPRA `3X_75_PR.SGY` | 5,168,048 | 1,592 complete records, 751 samples at 8,000 microseconds; revision word 0, IBM format 1 | Incomplete, with zero auditor-inspected headers: layout is outside the supported profile |

The similarity filename advertises IL230–430/XL475–675, a rectangle with 40,401
cells. The independently decoded headers contain a complete smaller rectangle;
requiring the named extent yields **12,515 missing cells**. This does not establish
corruption or a bad survey: the reason for the different extent is unknown. A
receiving workflow that expects the observed smaller extent is accepted. Its
wrong-sampling case changes only the interval in that accepted policy and requires
explicit sampling-failure evidence, so an unrelated grid failure cannot satisfy it.

The NPRA textual header declares custom legacy offsets. The auditor stops at the
unsupported envelope and does not interpret those offsets as modern geometry.
The independent experiment counts records and sampling separately; its 1,592-record
count must not be confused with the auditor's zero inspected trace headers.

```sh
python tools/validate_f3.py --sample similarity --download
python tools/validate_f3.py --sample npra --download
```

Use new destinations when repeating an experiment, for example `--out results-2`.
All eight cases verify the pinned source fingerprint and immutability. The opt-in
Windows/Linux workflow now runs all three files. Evidence:
[similarity manifest](similarity/manifest.json), [filename grid](similarity/filename-grid.json),
[observed rectangle](similarity/observed-rectangle.json),
[sampling contradiction](similarity/wrong-sampling.json),
[undeclared grid](similarity/undeclared-grid.json),
[NPRA manifest](npra/manifest.json), [unsupported-layout report](npra/audit.json).

The F3 licence/attribution above applies to both F3 exports. Equinor identifies
the NPRA source as the public USGS archive but does not state a separate file
licence. The [USGS archive description](https://www.usgs.gov/centers/central-energy-resources-science-center/science/geophysical-analysis-energy-resources)
confirms its public-data role (accessed 14 October 2026). The NPRA file is used only
for local/CI inspection; no redistribution licence is invented and no raw field
files or amplitudes are included in this repository or release assets.
