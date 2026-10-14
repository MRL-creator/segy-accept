"""Opt-in field experiment; raw F3 data are never bundled with the package."""

import argparse
import hashlib
import struct
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from segy_accept.audit import audit
from segy_accept.cli import save_reports
from segy_accept.policy import Policy
from segy_accept.report import json_text

SOURCE_REVISION = "c93e02027ea31d699b65be611f2747cc78cc967e"
SOURCE_FILE = "F3_Dip_steered_median_subvolume_IL230-430_XL475-675_T1600-1800.sgy"
SOURCE_URL = f"https://raw.githubusercontent.com/equinor/segyio-notebooks/{SOURCE_REVISION}/data/basic/{SOURCE_FILE}"
SIZE = 17_941_644
SHA256 = "ed50c38db56cbdd1343ca6d06a93e2ed0de2b82946c1cb6756ef9bba207f8573"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inspect_independently(data):
    """Stdlib oracle with manually specified offsets and filename grid expectations."""
    require(len(data) == SIZE, "field sample has an unexpected size")
    require(hashlib.sha256(data).hexdigest() == SHA256, "field sample fingerprint mismatch")
    words = {
        offset: struct.unpack_from(">H", data, offset)[0]
        for offset in [3216, 3220, 3224, 3254, 3500, 3502, 3504]
    }
    require(
        words == {3216: 4000, 3220: 51, 3224: 5, 3254: 1, 3500: 256, 3502: 1, 3504: 0},
        "binary header contradicts the independent oracle",
    )
    expected = {(i, j) for i in range(230, 431) for j in range(475, 676)}
    seen, xs, ys = set(), [], []
    for offset in range(3600, len(data), 444):
        scalar, units = (struct.unpack_from(">h", data, offset + k)[0] for k in [70, 88])
        ns, dt = (struct.unpack_from(">h", data, offset + k)[0] for k in [114, 116])
        x, y, i, j = (struct.unpack_from(">i", data, offset + k)[0] for k in [180, 184, 188, 192])
        require(
            (scalar, units, ns, dt) == (-10, 1, 51, 4000), "trace metadata contradicts the oracle"
        )
        require(
            (i, j) in expected and (i, j) not in seen, "unexpected or duplicate field grid cell"
        )
        seen.add((i, j))
        xs.append(x / 10)
        ys.append(y / 10)
    require(seen == expected, "field grid has missing cells")
    return {
        "traces": len(seen),
        "samples_per_trace": 51,
        "sample_interval_us": 4000,
        "inline_range": [230, 430],
        "crossline_range": [475, 675],
        "scaled_xy_extents": [min(xs), max(xs), min(ys), max(ys)],
        "scalar": -10,
        "coordinate_unit_code": 1,
        "measurement_system": 1,
    }


def validate(path, destination, retrieved_at=None):
    if path.stat().st_size != SIZE:
        raise ValueError("field sample size differs from the pinned source")
    data = path.read_bytes()
    oracle = inspect_independently(data)
    destination.mkdir(parents=True, exist_ok=False)
    policy = {
        "schema_version": 1,
        "name": "F3-subvolume-receiving-workflow",
        "version": "1",
        "samples_per_trace": 51,
        "sample_interval_us": 4000,
        "coordinates": {
            "units": "metres",
            "reference": "Unlocated XY from source textual header; no EPSG inferred",
            "bounds": [609000, 616000, 6076000, 6083000],
        },
        "grid": {"inlines": list(range(230, 431)), "crosslines": list(range(475, 676))},
    }
    cases = [
        ("declared-workflow", policy, "accepted"),
        ("wrong-sampling", policy | {"sample_interval_us": 2000}, "rejected"),
        ("undeclared-grid", policy | {"grid": None}, "incomplete"),
    ]
    outcomes = []
    for name, definition, expected in cases:
        policy_path = destination / f"{name}-policy.json"
        policy_path.write_text(json_text(definition), encoding="utf-8")
        result = audit(path, Policy.from_dict(definition))
        require(result["status"] == expected, f"{name}: unexpected audit decision")
        require(
            result["scan"]["complete"] and result["scan"]["traces_inspected"] == oracle["traces"],
            f"{name}: incomplete field scan",
        )
        require(result["input"]["sha256"] == SHA256, f"{name}: source fingerprint changed")
        save_reports(result, destination / name, [path, policy_path])
        outcomes.append({"case": name, "expected": expected, "actual": result["status"]})
        print(f"{name}: {result['status']} / {oracle['traces']} traces")
    require(hashlib.sha256(path.read_bytes()).hexdigest() == SHA256, "field input was modified")
    manifest = {
        "source_url": SOURCE_URL,
        "source_revision": SOURCE_REVISION,
        "source_file": SOURCE_FILE,
        "size_bytes": SIZE,
        "sha256": SHA256,
        "source_reviewed": "2026-10-14",
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "retrieved_at_utc": retrieved_at,
        "oracle": oracle,
        "cases": outcomes,
        "raw_data_redistributed": False,
        "license_source": f"https://github.com/equinor/segyio-notebooks/blob/{SOURCE_REVISION}/README.md",
        "license_as_stated": "CC-BY-SA; version not specified in the source README",
        "limits": "One processed field subvolume; contractual numeric bounds, no EPSG verification or scientific calibration.",
    }
    (destination / "manifest.json").write_text(json_text(manifest), encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path(".field-data/F3-field.sgy"))
    parser.add_argument("--out", type=Path, default=Path(".field-data/f3-results"))
    parser.add_argument(
        "--download", action="store_true", help="explicitly fetch the pinned 17.1 MiB sample"
    )
    args = parser.parse_args()
    retrieved_at = None
    if args.download:
        if args.input.exists():
            parser.error("input already exists; omit --download to validate it")
        with urllib.request.urlopen(SOURCE_URL, timeout=30) as response:
            data = response.read(SIZE + 1)
        if len(data) != SIZE or hashlib.sha256(data).hexdigest() != SHA256:
            parser.error("download does not match the pinned size and SHA-256")
        args.input.parent.mkdir(parents=True, exist_ok=True)
        with args.input.open("xb") as stream:
            stream.write(data)
        retrieved_at = datetime.now(timezone.utc).isoformat()
    validate(args.input, args.out, retrieved_at)


if __name__ == "__main__":
    main()
