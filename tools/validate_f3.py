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
SAMPLES = {
    "amplitude": {
        "file": SOURCE_FILE,
        "size": SIZE,
        "sha256": SHA256,
        "grid": [230, 430, 475, 675],
        "samples": 51,
        "interval": 4000,
    },
    "similarity": {
        "file": "F3_Similarity_FEF_subvolume_IL230-430_XL475-675_T1600-1800.sgy",
        "size": 12_384_984,
        "sha256": "dc6da7bf5c47cf5b8fcc7e321cdb989b91e95aa3ae7aea2bf1706a21c71ab8b2",
        "grid": [230, 420, 475, 620],
        "samples": 51,
        "interval": 4000,
    },
    "npra": {
        "file": "3X_75_PR.SGY",
        "size": 5_168_048,
        "sha256": "4a8490434e6e09cb0c2389328d42f7ad710d1fbc96a83be2c529ceec321d9722",
        "grid": None,
        "samples": 751,
        "interval": 8000,
    },
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def inspect_independently(data, sample="amplitude"):
    """Stdlib oracle with manually specified offsets and filename grid expectations."""
    spec = SAMPLES[sample]
    require(len(data) == spec["size"], "field sample has an unexpected size")
    require(hashlib.sha256(data).hexdigest() == spec["sha256"], "field sample fingerprint mismatch")
    words = {
        offset: struct.unpack_from(">H", data, offset)[0]
        for offset in [3216, 3220, 3224, 3254, 3500, 3502, 3504]
    }
    if sample == "npra":
        require(
            words == {3216: 8000, 3220: 751, 3224: 1, 3254: 0, 3500: 0, 3502: 0, 3504: 0},
            "legacy binary header contradicts the oracle",
        )
        for offset in range(3600, len(data), 3244):
            require(
                struct.unpack_from(">HH", data, offset + 114) == (751, 8000),
                "legacy trace sampling contradicts the oracle",
            )
        return {
            "traces": 1592,
            "samples_per_trace": 751,
            "sample_interval_us": 8000,
            "revision_word": 0,
            "format_code": 1,
            "fixed_length_flag": 0,
            "geometry": "Not interpreted: legacy textual header declares custom offsets",
        }
    require(
        words == {3216: 4000, 3220: 51, 3224: 5, 3254: 1, 3500: 256, 3502: 1, 3504: 0},
        "binary header contradicts the independent oracle",
    )
    imin, imax, jmin, jmax = spec["grid"]
    expected = {(i, j) for i in range(imin, imax + 1) for j in range(jmin, jmax + 1)}
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
        "inline_range": [imin, imax],
        "crossline_range": [jmin, jmax],
        "scaled_xy_extents": [min(xs), max(xs), min(ys), max(ys)],
        "scalar": -10,
        "coordinate_unit_code": 1,
        "measurement_system": 1,
    }


def validate(path, destination, retrieved_at=None, sample="amplitude"):
    spec = SAMPLES[sample]
    if path.stat().st_size != spec["size"]:
        raise ValueError("field sample size differs from the pinned source")
    data = path.read_bytes()
    oracle = inspect_independently(data, sample)
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
    if sample == "similarity":
        cases[0] = ("filename-grid", policy, "rejected")
        cases.insert(
            1,
            (
                "observed-rectangle",
                policy
                | {"grid": {"inlines": list(range(230, 421)), "crosslines": list(range(475, 621))}},
                "accepted",
            ),
        )
        cases[2] = ("wrong-sampling", cases[1][1] | {"sample_interval_us": 2000}, "rejected")
    elif sample == "npra":
        cases = [
            (
                "unsupported-legacy-profile",
                {
                    "schema_version": 1,
                    "name": "NPRA-legacy-inspection",
                    "version": "1",
                    "samples_per_trace": 751,
                    "sample_interval_us": 8000,
                },
                "incomplete",
            )
        ]
    outcomes = []
    for name, definition, expected in cases:
        policy_path = destination / f"{name}-policy.json"
        policy_path.write_text(json_text(definition), encoding="utf-8")
        result = audit(path, Policy.from_dict(definition))
        require(result["status"] == expected, f"{name}: unexpected audit decision")
        require(
            (not result["scan"]["complete"] and result["scan"]["traces_inspected"] == 0)
            if sample == "npra"
            else (
                result["scan"]["complete"]
                and result["scan"]["traces_inspected"] == oracle["traces"]
            ),
            f"{name}: incomplete field scan",
        )
        require(result["input"]["sha256"] == spec["sha256"], f"{name}: source fingerprint changed")
        if name == "wrong-sampling":
            sampling = next(f for f in result["findings"] if f["rule_id"] == "sampling.policy")
            require(
                sampling["status"] == "failure"
                and any(
                    e.get("field") == "sample_interval_us"
                    and e.get("expected") == 2000
                    and e.get("actual") == 4000
                    for e in sampling["examples"]
                ),
                "sampling-policy contradiction was not demonstrated",
            )
        if name == "filename-grid":
            geometry = next(f for f in result["findings"] if f["rule_id"] == "geometry.grid")
            require(
                geometry["count"] == 12515, "missing-cell count differs from independent oracle"
            )
        save_reports(result, destination / name, [path, policy_path])
        outcomes.append({"case": name, "expected": expected, "actual": result["status"]})
        print(
            f"{name}: {result['status']} / {result['scan']['traces_inspected']} inspected; "
            f"{oracle['traces']} traces in independent oracle"
        )
    require(
        hashlib.sha256(path.read_bytes()).hexdigest() == spec["sha256"], "field input was modified"
    )
    manifest = {
        "source_url": f"https://raw.githubusercontent.com/equinor/segyio-notebooks/{SOURCE_REVISION}/data/basic/{spec['file']}",
        "source_revision": SOURCE_REVISION,
        "source_file": spec["file"],
        "size_bytes": spec["size"],
        "sha256": spec["sha256"],
        "source_reviewed": "2026-10-14",
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "retrieved_at_utc": retrieved_at,
        "oracle": oracle,
        "cases": outcomes,
        "raw_data_redistributed": False,
        "license_source": f"https://github.com/equinor/segyio-notebooks/blob/{SOURCE_REVISION}/README.md",
        "license_as_stated": (
            "CC-BY-SA; version not specified in the source README"
            if sample != "npra"
            else "Source README identifies public USGS NPRA archive; no separate file licence stated. Raw file not redistributed."
        ),
        "limits": "Selected processed exports only; no EPSG verification, amplitude QC or scientific calibration.",
    }
    (destination / "manifest.json").write_text(json_text(manifest), encoding="utf-8")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", choices=SAMPLES, default="amplitude")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument(
        "--download", action="store_true", help="explicitly fetch the selected pinned small sample"
    )
    args = parser.parse_args()
    spec = SAMPLES[args.sample]
    if args.input is None:
        args.input = (
            Path(".field-data/F3-field.sgy")
            if args.sample == "amplitude"
            else Path(".field-data") / spec["file"]
        )
    if args.out is None:
        args.out = (
            Path(".field-data/f3-results")
            if args.sample == "amplitude"
            else Path(".field-data") / f"{args.sample}-results"
        )
    retrieved_at = None
    if args.download:
        if args.input.exists():
            parser.error("input already exists; omit --download to validate it")
        url = f"https://raw.githubusercontent.com/equinor/segyio-notebooks/{SOURCE_REVISION}/data/basic/{spec['file']}"
        with urllib.request.urlopen(url, timeout=30) as response:
            data = response.read(spec["size"] + 1)
        if len(data) != spec["size"] or hashlib.sha256(data).hexdigest() != spec["sha256"]:
            parser.error("download does not match the pinned size and SHA-256")
        args.input.parent.mkdir(parents=True, exist_ok=True)
        with args.input.open("xb") as stream:
            stream.write(data)
        retrieved_at = datetime.now(timezone.utc).isoformat()
    validate(args.input, args.out, retrieved_at, args.sample)


if __name__ == "__main__":
    main()
