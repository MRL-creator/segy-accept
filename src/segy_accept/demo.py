"""Generate a tiny, explicitly synthetic, adversarial SEG-Y corpus."""

import copy
import struct
from pathlib import Path

from .report import json_text

POLICY = {
    "schema_version": 1,
    "name": "synthetic-poststack",
    "version": "1",
    "sample_interval_us": 2000,
    "samples_per_trace": 8,
    "coordinates": {
        "units": "metres",
        "reference": "Synthetic local grid, not a real CRS",
        "bounds": [900, 1100, 1900, 2100],
    },
    "grid": {"inlines": [10, 11], "crosslines": [20, 21]},
}


def write_fixture(path, traces, revision=256):
    """Write known standard fields with struct, independently of the segyio reader."""
    header = bytearray(b" " * 3200 + bytes(400))
    label = b"C 1 SYNTHETIC SEG-Y ACCEPT FIXTURE - NOT FIELD DATA"
    header[: len(label)] = label
    for offset, value in [
        (3216, 2000),
        (3220, 8),
        (3224, 5),
        (3254, 1),
        (3500, revision),
        (3502, 1),
    ]:
        struct.pack_into(">H", header, offset, value)
    with Path(path).open("xb") as stream:
        stream.write(header)
        for trace in traces:
            raw = bytearray(240)
            fields = [
                (70, "h", trace.get("scalar", -10)),
                (88, "h", trace.get("units", 1)),
                (114, "H", trace.get("ns", 8)),
                (116, "H", trace.get("dt", 2000)),
                (180, "i", trace["x"]),
                (184, "i", trace["y"]),
                (188, "i", trace["inline"]),
                (192, "i", trace["crossline"]),
            ]
            for offset, fmt, value in fields:
                struct.pack_into(">" + fmt, raw, offset, value)
            stream.write(raw)
            stream.write(struct.pack(">8f", *range(8)))


def generate_demo(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "policy.json").write_text(json_text(POLICY), encoding="utf-8")
    clean = [
        {"inline": i, "crossline": j, "x": 10000 + (i - 10) * 100, "y": 20000 + (j - 20) * 100}
        for i in [10, 11]
        for j in [20, 21]
    ]
    broken = copy.deepcopy(clean)
    broken[1] |= {"dt": 4000, "ns": 7, "inline": 10, "crossline": 20}
    outside = copy.deepcopy(clean)
    outside[2]["x"] = 500000
    unknown = copy.deepcopy(clean)
    unknown[0]["units"] = 0
    definitions = [
        ("clean", clean, "accepted", {"geometry.grid": "pass"}),
        (
            "readable-broken",
            broken,
            "rejected",
            {"sampling.consistency": "failure", "geometry.grid": "failure"},
        ),
        ("outside-bounds", outside, "rejected", {"coordinates.bounds": "failure"}),
        ("unknown-units", unknown, "incomplete", {"coordinates.units": "unknown"}),
        ("missing-cell", clean[:-1], "rejected", {"geometry.grid": "failure"}),
        ("truncated", clean, "incomplete", {"format.profile": "failure"}),
        ("unsupported-revision", clean, "incomplete", {"format.profile": "unknown"}),
    ]
    cases = []
    for name, traces, expected, findings in definitions:
        path = destination / f"{name}.sgy"
        write_fixture(path, traces, revision=512 if name == "unsupported-revision" else 256)
        if name == "truncated":
            with path.open("r+b") as stream:
                stream.truncate(path.stat().st_size - 5)
        cases.append(
            {
                "file": path.name,
                "report": name,
                "expected_status": expected,
                "expected_findings": findings,
            }
        )
    manifest = {
        "synthetic": True,
        "fixture_license": "MIT, see project LICENSE",
        "policy": "policy.json",
        "cases": cases,
    }
    (destination / "manifest.json").write_text(json_text(manifest), encoding="utf-8")
    return manifest
