# Decisions and sources

## A policy checker above an established reader

Use released segyio 1.9.14 in mode `r` with `ignore_geometry=True`. Automatic
geometry inference can reject the exact inconsistencies the auditor should
explain. Independently inspect only the narrow file envelope and sizes with
stdlib `struct`; do not build another general trace reader.

Read every header, keep only bounded evidence examples, and store a set for
global cell checks. This is intentionally O(unique cells), not constant memory.
Checks require explicit workflow expectations so an unknown CRS, grid, or unit
does not become a false acceptance. No scientific calibration or amplitude QA
is inferred from header agreement.

## Differentiation checkpoint

The synthetic `readable-broken.sgy` file opens in segyio while its second trace
contradicts binary sampling and duplicates a grid cell. Header scans expose
values; this tool connects them to receiving-policy failures, missing expected
cells, producer-facing next steps, and a reproducible identity record. That is
the narrow added behavior. SEG-Y-SAK was reviewed through its documentation;
no claim of an exhaustive head-to-head benchmark or commercial-tool survey is made.

## Reporting and trust boundaries

The narrow profile uses positive signed 16-bit sampling words (1-32767), following
revision-1 section 3.3. A high-bit fixture exposed different reader interpretations
of these words. The tool rejects that extension at envelope inspection rather
than allowing binary and trace interpretations to disagree. This is a documented
input-profile decision, not a claim about every producer's convention.

The CLI orchestrates policy loading, auditing and output. No network calls,
shell evaluation, HTML scripts, authentication, or uploaded field data are part
of the runtime. Every file/policy value is HTML-escaped. JSON keys are checked,
duplicate keys refused, bounds finite, and grid products bounded.

Inputs remain read-only. Reports are newly created by default. Explicit overwrite
uses replacement, with alias checks protecting source/policy even if hardlinked.
Do not run in directories concurrently manipulated by untrusted processes;
path checks are not a filesystem sandbox. Reports may reveal survey coordinates
and filenames, so review their contents before sharing.

The original code and generated fixtures use MIT; the parser's LGPL terms are
separate. A distribution compliance review and real-field-data permission checks
are still needed before bundling other components or datasets.

## Primary references

Accessed 14 October 2026:

- [SEG revision-1 specification](https://seg.org/wp-content/uploads/2025/11/seg_y_rev1.pdf): Tables 2/3 and disk layout appendix. The MVP deliberately covers a subset.
- [SEG standards register](https://seg.org/publications/seg-technical-standards/): later revisions exist; no revision-2 support is claimed.
- [segyio stable API](https://segyio.readthedocs.io/en/stable/segyio.html): read-only mode, geometry bypass, and header fields.
- [segyio repository](https://github.com/equinor/segyio): LGPL and maintenance/version context.
- [segyio 1.9.14 registry release](https://pypi.org/project/segyio/1.9.14/): released binary dependency.
- [SEG-Y-SAK header scan examples](https://trhallam.github.io/segysak/latest/examples/example_segy_headers.html): established header summaries.
- [GitHub checkout](https://github.com/actions/checkout) and [setup-python](https://github.com/actions/setup-python): current documented v7 workflow usage.
