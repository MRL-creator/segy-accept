"""Header checks with bounded evidence and explicit partial-knowledge states."""

import hashlib
import json
import os
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path

import segyio

from . import __version__
from .reader import MAX_BYTES, AuditInputError, file_signature, inspect_envelope, regular_file_stat

RULES = {
    "format.profile": (
        "Supported envelope and complete header scan",
        "Use the documented revision-1 fixed-length IEEE profile; inspect/export other layouts separately.",
    ),
    "sampling.consistency": (
        "Trace sampling agrees with the binary header",
        "Confirm sample count/interval with the producer; correct metadata or re-export outside this tool.",
    ),
    "sampling.policy": (
        "Binary sampling agrees with declared workflow expectations",
        "Supply both sampling expectations and confirm that they describe the intended workflow.",
    ),
    "coordinates.units": (
        "CDP coordinate units agree with the receiving policy",
        "Confirm coordinate units and binary measurement system with the producer; do not guess a CRS.",
    ),
    "coordinates.scalar": (
        "Coordinate scaling is explicit and interpretable",
        "Confirm the scalar; positive multiplies, negative divides. Zero is an explicit unity fallback warning.",
    ),
    "coordinates.bounds": (
        "Scaled CDP X/Y falls inside the declared bounds",
        "Check CDP fields, scalar, units and declared reference/bounds. No reprojection or repair is performed.",
    ),
    "geometry.grid": (
        "One trace per declared Cartesian post-stack cell",
        "Confirm the post-stack grid policy; review duplicates, unexpected cells and missing cells before import.",
    ),
}


class Check:
    def __init__(self, rule_id, limit):
        self.limit = limit
        title, remedy = RULES[rule_id]
        self.data = {
            "rule_id": rule_id,
            "title": title,
            "status": "pass",
            "count": 0,
            "examples": [],
            "next_step": remedy,
        }

    def add(self, status, evidence):
        priority = {"pass": 0, "warning": 1, "unknown": 2, "failure": 3}
        if priority[status] > priority[self.data["status"]]:
            self.data["status"] = status
            self.data["examples"].clear()
        self.data["count"] += 1
        if status == self.data["status"] and len(self.data["examples"]) < self.limit:
            self.data["examples"].append(evidence)


def sha256_file(path):
    """Hash at most the initial size plus a growth probe, refusing unstable inputs."""
    path = Path(path)
    initial = regular_file_stat(path)
    if initial.st_size > MAX_BYTES:
        raise AuditInputError(f"input exceeds hashing limit of {MAX_BYTES} bytes")
    signature = file_signature(initial)
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        if file_signature(os.fstat(stream.fileno())) != signature:
            raise AuditInputError("input changed before hashing")
        remaining = initial.st_size
        while remaining:
            block = stream.read(min(1024 * 1024, remaining))
            if not block:
                raise AuditInputError("input changed during hashing (short read)")
            digest.update(block)
            remaining -= len(block)
        if stream.read(1) or file_signature(os.fstat(stream.fileno())) != signature:
            raise AuditInputError("input changed during hashing")
    if file_signature(regular_file_stat(path)) != signature:
        raise AuditInputError("input changed after hashing")
    return digest.hexdigest()


def coordinate_units(code, measurement, expected):
    if code == 0 or code not in [1, 2, 3, 4]:
        return "unknown", "coordinate unit code is unknown/unrecognized"
    wanted = 3 if expected == "decimal_degrees" else 1
    if code != wanted:
        return "failure", f"unit code {code} contradicts declared {expected}"
    if code == 1:
        if measurement not in [1, 2]:
            return "unknown", "length unit needs binary measurement system 1 (metres) or 2 (feet)"
        if measurement != (1 if expected == "metres" else 2):
            return "failure", f"binary measurement system {measurement} contradicts {expected}"
    return "pass", "declared units agree"


def check_coordinates(header, index, envelope, policy, checks, examples):
    scalar = header[segyio.TraceField.SourceGroupScalar]
    raw_x, raw_y = header[segyio.TraceField.CDP_X], header[segyio.TraceField.CDP_Y]
    evidence = {"trace": index, "scalar": scalar, "raw_x": raw_x, "raw_y": raw_y}
    status = "unknown"
    if policy.coordinates is not None:
        code = header[segyio.TraceField.CoordinateUnits]
        status, reason = coordinate_units(
            code, envelope.measurement_system, policy.coordinates["units"]
        )
        if status != "pass":
            checks["coordinates.units"].add(
                status,
                {
                    "trace": index,
                    "unit_code": code,
                    "measurement_system": envelope.measurement_system,
                    "reason": reason,
                },
            )
    if scalar not in [0, 1, -1, 10, -10, 100, -100, 1000, -1000, 10000, -10000]:
        checks["coordinates.scalar"].add("failure", evidence | {"reason": "non-profile scalar"})
        checks["coordinates.bounds"].add("unknown", evidence | {"reason": "untrusted scalar"})
        return
    if scalar == 0:
        checks["coordinates.scalar"].add(
            "warning", evidence | {"reason": "zero treated as unity by this receiving convention"}
        )
    if scalar < 0:
        x, y = raw_x / abs(scalar), raw_y / abs(scalar)
    else:
        x, y = raw_x * (scalar or 1), raw_y * (scalar or 1)
    evidence |= {"scaled_x": x, "scaled_y": y, "units_verified": status == "pass"}
    if len(examples) < policy.example_limit:
        examples.append(evidence)
    if policy.coordinates is None:
        return
    if status != "pass":
        checks["coordinates.bounds"].add(
            "unknown", {"trace": index, "reason": "units do not establish comparable coordinates"}
        )
        return
    xmin, xmax, ymin, ymax = policy.coordinates["bounds"]
    if not (xmin <= x <= xmax and ymin <= y <= ymax):
        checks["coordinates.bounds"].add(
            "failure", evidence | {"bounds": policy.coordinates["bounds"]}
        )


def check_grid(seen, cell, index, inlines, crosslines, check):
    if cell in seen:
        check.add(
            "failure",
            {"kind": "duplicate", "trace": index, "inline": cell[0], "crossline": cell[1]},
        )
    seen.add(cell)
    if cell[0] not in inlines or cell[1] not in crosslines:
        check.add(
            "failure",
            {"kind": "unexpected", "trace": index, "inline": cell[0], "crossline": cell[1]},
        )


def audit(path, policy):
    """Audit every trace header; never infer acceptance for missing policy dimensions."""
    path = Path(path)
    original_stat = regular_file_stat(path)
    canonical = {"schema_version": 1, **asdict(policy)}
    policy_bytes = json.dumps(
        canonical, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    checks = {rule: Check(rule, policy.example_limit) for rule in RULES}
    result = {
        "schema_version": 1,
        "tool": {"name": "segy-accept", "version": __version__, "segyio": version("segyio")},
        "input": {"name": path.name, "size_bytes": original_stat.st_size, "sha256": None},
        "policy": {"sha256": hashlib.sha256(policy_bytes).hexdigest(), "definition": canonical},
        "scan": {"mode": "full", "complete": False, "traces_expected": None, "traces_inspected": 0},
        "status": "incomplete",
        "coordinate_examples": [],
        "scope": "Standard revision-1 big-endian fixed-length IEEE headers, no extended headers; not full standards or scientific validation.",
    }
    for rule in ["sampling.policy", "coordinates.units", "coordinates.bounds", "geometry.grid"]:
        absent = (
            rule == "sampling.policy"
            and (policy.samples_per_trace is None or policy.sample_interval_us is None)
            or rule.startswith("coordinates")
            and policy.coordinates is None
            or rule == "geometry.grid"
            and policy.grid is None
        )
        if absent:
            checks[rule].add("unknown", {"reason": "workflow expectations not fully declared"})
    try:
        envelope = inspect_envelope(path)
        result["scan"]["traces_expected"] = envelope.trace_count
        result["binary_header"] = asdict(envelope)
        for key, actual in [
            ("samples_per_trace", envelope.samples_per_trace),
            ("sample_interval_us", envelope.sample_interval_us),
        ]:
            expected = getattr(policy, key)
            if expected is not None and expected != actual:
                checks["sampling.policy"].add(
                    "failure", {"field": key, "expected": expected, "actual": actual}
                )
        seen = set()
        inlines = set(policy.grid["inlines"]) if policy.grid else set()
        crosslines = set(policy.grid["crosslines"]) if policy.grid else set()
        with segyio.open(str(path), "r", ignore_geometry=True, endian="big") as dataset:
            if dataset.tracecount != envelope.trace_count:
                raise AuditInputError(
                    "parser trace count disagrees with independent envelope", "failure"
                )
            for index, header in enumerate(dataset.header, 1):
                ns = header[segyio.TraceField.TRACE_SAMPLE_COUNT]
                dt = header[segyio.TraceField.TRACE_SAMPLE_INTERVAL]
                if ns != envelope.samples_per_trace or dt != envelope.sample_interval_us:
                    checks["sampling.consistency"].add(
                        "failure",
                        {
                            "trace": index,
                            "samples": ns,
                            "interval_us": dt,
                            "expected_samples": envelope.samples_per_trace,
                            "expected_interval_us": envelope.sample_interval_us,
                        },
                    )
                check_coordinates(
                    header, index, envelope, policy, checks, result["coordinate_examples"]
                )
                if policy.grid is not None:
                    cell = (
                        header[segyio.TraceField.INLINE_3D],
                        header[segyio.TraceField.CROSSLINE_3D],
                    )
                    check_grid(seen, cell, index, inlines, crosslines, checks["geometry.grid"])
                result["scan"]["traces_inspected"] = index
        if policy.grid is not None:
            for i in sorted(inlines):
                for j in sorted(crosslines):
                    if (i, j) not in seen:
                        checks["geometry.grid"].add(
                            "failure", {"kind": "missing", "inline": i, "crossline": j}
                        )
        result["scan"]["complete"] = True
    except (AuditInputError, OSError, RuntimeError, ValueError) as error:
        checks["format.profile"].add(getattr(error, "status", "failure"), {"reason": str(error)})
        for rule, check in checks.items():
            if rule != "format.profile" and check.data["status"] == "pass":
                check.add("unknown", {"reason": "scan could not be completed"})
    unstable_reason = None
    try:
        if file_signature(regular_file_stat(path)) != file_signature(original_stat):
            raise AuditInputError("input changed during audit; rerun on a stable file")
        if original_stat.st_size <= MAX_BYTES:
            result["input"]["sha256"] = sha256_file(path)
        if file_signature(regular_file_stat(path)) != file_signature(original_stat):
            raise AuditInputError("input changed during audit; rerun on a stable file")
    except (AuditInputError, OSError) as error:
        unstable_reason = str(error)
    if unstable_reason is not None:
        result["scan"]["complete"] = False
        checks["format.profile"].add("unknown", {"reason": unstable_reason})
        for rule, check in checks.items():
            if rule != "format.profile" and check.data["status"] in ["pass", "warning"]:
                check.add("unknown", {"reason": "input stability could not be established"})
        result["input"]["sha256"] = None
        result["coordinate_examples"].clear()
    result["findings"] = [check.data for check in checks.values()]
    statuses = {check.data["status"] for check in checks.values()}
    if result["scan"]["complete"]:
        result["status"] = (
            "rejected"
            if "failure" in statuses
            else "incomplete"
            if "unknown" in statuses
            else "accepted"
        )
    return result
