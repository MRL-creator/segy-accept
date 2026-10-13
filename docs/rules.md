# Rule catalogue (policy/result schema 1)

| Rule | Pass means | Failure or unknown |
| --- | --- | --- |
| `format.profile` | Envelope fits the supported layout and segyio completes every trace header | Truncated/invalid narrow envelope: failure, incomplete audit. Other layouts or resource guard: unknown. |
| `sampling.consistency` | Every trace sample count/interval matches the binary header | Any contradiction fails. A scan that stops cannot establish a pass. |
| `sampling.policy` | Binary sample count/interval matches both declared workflow values | Contradiction fails. Either absent expectation leaves unknown knowledge. |
| `coordinates.units` | Each trace's unit code and, for lengths, binary measurement system matches the policy | Unknown unit/basis is unknown; explicitly contradictory units fail. |
| `coordinates.scalar` | Each CDP scalar is one of +/-1, 10, 100, 1000, 10000 | Other nonzero scalar fails. Zero uses unity with a warning. |
| `coordinates.bounds` | Scaled CDP X/Y is inside inclusive declared bounds with compatible units | Out-of-bounds fails; missing policy or untrusted scalar/units is unknown. |
| `geometry.grid` | Exactly one trace per declared Cartesian post-stack grid cell | Duplicate, unexpected and missing cells fail separately. No grid contract is unknown. |

The tool uses 1-based trace numbers in evidence. Counts are non-pass events,
not necessarily distinct traces; a geometry cell may contribute to more than
one event category. Evidence examples are capped by `example_limit` (default 5,
range 1-100); counts continue after the cap. A passing check has count zero.
Examples represent the highest severity encountered for that rule, so earlier
warnings or unknown events cannot hide the evidence for a later failure.

## Header mapping

All byte positions below are **1-based**; binary locations are absolute in the file,
trace locations relative to a 240-byte trace header.

- Binary sample interval: 3217-3218; sample count: 3221-3222; format: 3225-3226.
- Binary measurement system: 3255-3256 (1 metres, 2 feet).
- Revision: 3501-3502; fixed flag: 3503-3504; extended count: 3505-3506.
- Trace scalar: 71-72; units: 89-90; samples: 115-116; interval: 117-118.
- Trace CDP X/Y: 181-184 / 185-188; inline/crossline: 189-192 / 193-196.

Positive scalar multiplies raw coordinates; negative scalar divides by its
absolute value. Example: raw 10000 and scalar -10 give 1000. Bounds and units
still require a declared reference. Source/group coordinates and elevations
are not audited. Header consistency cannot establish that a stated CRS is true.

## Scan and overall status

Only a full header scan may be accepted or rejected. A completed audit with any
failure is rejected; otherwise any unknown makes it incomplete; otherwise it
is accepted, potentially with warnings. If parsing stops or a size/trace guard
is hit, the audit is incomplete. The detected format defect may still be a failure.
Passed rules whose scan is interrupted become unknown. Findings already detected
remain available but are not a claim that all traces were checked.

The input fingerprint is computed in bounded blocks. Before/after file metadata
checks detect ordinary size/mtime changes, but this does not create an atomic
snapshot or defend against a hostile writer preserving metadata. Audit an
immutable copy when concurrent changes are possible.
