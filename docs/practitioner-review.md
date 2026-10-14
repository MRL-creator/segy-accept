# Practitioner review packet

**Status: pending.** No geoscience practitioner has reviewed or endorsed this
project. Automated code review and test evidence are separate from domain feedback.

Suggested effort: 20–30 minutes. Intended reviewer: a geoscience developer or data
recipient who works with post-stack seismic volumes and SEG-Y import assumptions.

1. Read the support profile and receiving policy in the [README](../README.md).
2. Run `python -m segy_accept demo review-demo` in a new directory. Compare the
   clean, readable-broken, unknown-units, and missing-cell reports with their known
   [expected outcomes](../examples/manifest.json).
3. Review the [field experiment](field-validation/README.md). In particular,
   decide whether its explicit numeric XY basis is described clearly enough to
   prevent treating it as verified navigation or an inferred CRS.
4. Assess whether rule IDs, bounded evidence, counts, and next steps would help
   decide whether to import a dataset. Identify any misleading language.
5. Explain one realistic receiving workflow that the current profile serves and
   one it cannot serve. Prioritize the next missing check with a concrete example.

Record reviewer role, relevant experience, date, tested version, commands/cases
used, findings by severity, and a recommendation: usable for the stated workflow,
usable after specific fixes, or not yet useful. State any conflicts of interest.
Permission is required before publishing a reviewer's identity or quoting feedback.
Synthetic cases are enough for the review; confidential files are unnecessary.

Until this review occurs, describe the project as a tested preview with one
processed-field-data experiment, rather than a practitioner-validated product.
