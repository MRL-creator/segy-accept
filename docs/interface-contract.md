# Stable interface contract — v1

The supported public interfaces are the installed `segy-accept` command, the
equivalent `python -m segy_accept` entry point, and schema-1 policy/audit JSON.
Python implementation helpers, developer experiment manifests, terminal wording,
and HTML layout are not frozen APIs. The HTML remains self-contained and offline.

## Commands and outcomes

```sh
segy-accept --version
segy-accept audit INPUT --policy POLICY --out DIRECTORY [--overwrite]
segy-accept demo NEW_DIRECTORY
```

Help and version requests exit 0. Audit outcomes retain these exact meanings:

| Exit | Meaning |
| --- | --- |
| 0 | Complete audit accepted by every implemented rule; warnings can remain |
| 1 | Complete audit found at least one failure; unknown findings can coexist |
| 2 | Incomplete scan, unsupported input, or undeclared/unresolved knowledge |
| 3 | Invalid invocation/policy or input/report I/O error |

Reports are created for exits 0–2. An exit-3 operation can leave partial output
after an output-write error; do not consume that pair as a completed result.
Existing reports are preserved by default; replacement requires `--overwrite`.
Input and policy aliases remain protected, including hardlinks. Stable source
files and output directories are required; no concurrent-writer locking is promised.

## Policy JSON

Schema 1 requires integer `schema_version: 1` and nonempty string `name`/`version`.
Unknown and duplicate keys are rejected. Sampling expectations are positive
integers 1–32767; omission or null means undeclared. Coordinate and Cartesian grid
objects follow the [README](../README.md) and [rules](rules.md); omission or null
also means undeclared. `example_limit` defaults to 5 and allows integers 1–100.
Size, grid-product, finite-bound, and explicit-reference checks still apply.

`policy.definition` in every report is valid replay input, including defaulted
null expectations. Its SHA-256 covers sorted, compact JSON with default-expanded
fields, ASCII escaping, and no trailing newline. It is not a hash of the original
policy file's whitespace. Unknown policy dimensions prevent acceptance.

## Audit JSON

Consumers must check `schema_version` and allow additional fields. Existing fields
retain their types and meanings throughout v1:

| Field | Type and meaning |
| --- | --- |
| `schema_version` | Integer 1 |
| `status` | `accepted`, `rejected`, or `incomplete` |
| `tool` | `name`, package `version`, and reader `segyio` version strings |
| `input` | `name` string, `size_bytes` integer, `sha256` lowercase hex string or null |
| `policy` | `sha256` string and replayable `definition` object |
| `scan` | `mode: full`, Boolean `complete`, integer `traces_inspected`, integer-or-null `traces_expected` |
| `findings` | One finding for each of the seven rule IDs below |
| `coordinate_examples` | Bounded arithmetic examples, with `units_verified`; cleared on detected input instability |
| `scope` | Human-readable support/interpretation statement |
| `binary_header` | Optional object, present after supported envelope inspection |

Rule IDs: `format.profile`, `sampling.consistency`, `sampling.policy`,
`coordinates.units`, `coordinates.scalar`, `coordinates.bounds`, `geometry.grid`.
Use IDs rather than list position or translated prose. Every finding has string
`rule_id`, `title`, `status`, `next_step`; nonnegative integer `count`; and list
`examples`. Status is `pass`, `warning`, `unknown`, or `failure`. Counts are events,
not necessarily distinct traces. Examples show bounded highest-severity evidence;
their rule-specific keys are explanatory, not a general data-export API.

A null source hash means fingerprinting could not be established, including an
oversized or changing input. Acceptance requires a complete scan with no unknown
or failure findings. Fixed input bytes, policy, and tool/reader environment produce
deterministic JSON. Version/provenance changes intentionally change that record.

## Compatibility policy

Within v1, keep existing commands/options, exit meanings, rule IDs, and JSON-field
types. Additive optional fields may appear, so consumers must ignore unknown output
fields. Intentional breaking changes require a new major package/schema version
and migration notes. Correctness and security fixes may change a previously wrong
decision; record those fixes in the changelog with regression evidence.

Stable means this bounded contract has passed its release checks. It does not mean
every SEG-Y variant is supported or that independent practitioner endorsement has
been obtained. Practitioner feedback can inform future releases without blocking
this one. See the [release evidence and limits](release-readiness.md).
