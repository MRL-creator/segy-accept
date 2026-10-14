"""Independent writer experiment; requires the optional validation extra."""

import argparse
from importlib.metadata import version
from pathlib import Path

from .audit import audit, sha256_file
from .cli import load_policy, save_reports
from .report import json_text


def generate_independent(destination):
    """Create owned synthetic data with ObsPy, without our byte writer or segyio writing."""
    import numpy as np
    from obspy import Stream, Trace
    from obspy.core import AttribDict
    from obspy.io.segy.segy import SEGYBinaryFileHeader, SEGYTraceHeader

    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    stream = Stream()
    for i in [10, 11]:
        for j in [20, 21]:
            trace = Trace(np.arange(64, dtype=np.float32) / 64)
            trace.stats.delta = 0.002
            trace.stats.segy = AttribDict(trace_header=SEGYTraceHeader())
            header = trace.stats.segy.trace_header
            header.scalar_to_be_applied_to_all_coordinates = -10
            header.coordinate_units = 1
            header.x_coordinate_of_ensemble_position_of_this_trace = 10000 + (i - 10) * 100
            header.y_coordinate_of_ensemble_position_of_this_trace = 20000 + (j - 20) * 100
            header.for_3d_poststack_data_this_field_is_for_in_line_number = i
            header.for_3d_poststack_data_this_field_is_for_cross_line_number = j
            stream.append(trace)
    stream.stats = AttribDict(binary_file_header=SEGYBinaryFileHeader())
    stream.stats.binary_file_header.measurement_system = 1
    stream.stats.binary_file_header.seg_y_format_revision_number = 256
    stream.stats.binary_file_header.fixed_length_trace_flag = 1
    stream.stats.textual_file_header = (
        b"C 1 SYNTHETIC INDEPENDENT WRITER VALIDATION - NOT FIELD DATA"
    )
    clean = destination / "obspy-clean.sgy"
    stream.write(
        str(clean), format="SEGY", data_encoding=5, byteorder=">", textual_header_encoding="ASCII"
    )
    stream[1].stats.segy.trace_header.for_3d_poststack_data_this_field_is_for_cross_line_number = 20
    contradictory = destination / "obspy-duplicate.sgy"
    stream.write(
        str(contradictory),
        format="SEGY",
        data_encoding=5,
        byteorder=">",
        textual_header_encoding="ASCII",
    )
    policy = {
        "schema_version": 1,
        "name": "independent-synthetic-grid",
        "version": "1",
        "sample_interval_us": 2000,
        "samples_per_trace": 64,
        "coordinates": {
            "units": "metres",
            "reference": "Synthetic local grid, not a real CRS",
            "bounds": [900, 1100, 1900, 2100],
        },
        "grid": {"inlines": [10, 11], "crosslines": [20, 21]},
    }
    (destination / "policy.json").write_text(json_text(policy), encoding="utf-8")
    manifest = {
        "synthetic": True,
        "fixture_license": "MIT",
        "writer": {"name": "ObsPy", "version": version("obspy"), "library_license": "LGPL-3.0"},
        "input": clean.name,
        "input_sha256": sha256_file(clean),
        "contradictory_input": contradictory.name,
        "contradictory_sha256": sha256_file(contradictory),
        "expected_clean_status": "accepted",
        "expected_contradictory_status": "rejected",
        "source": "https://docs.obspy.org/packages/obspy.io.segy.html",
        "limits": "Owned synthetic arrays, not independently certified or representative field data.",
    }
    (destination / "manifest.json").write_text(json_text(manifest), encoding="utf-8")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Validate the auditor against independently written synthetic SEG-Y"
    )
    parser.add_argument("directory", type=Path)
    args = parser.parse_args(argv)
    try:
        manifest = generate_independent(args.directory)
        policy_path = args.directory / "policy.json"
        policy = load_policy(policy_path)
        for field, expected in [("input", "accepted"), ("contradictory_input", "rejected")]:
            path = args.directory / manifest[field]
            result = audit(path, policy)
            save_reports(result, args.directory / path.stem, [path, policy_path])
            if result["status"] != expected:
                raise ValueError(
                    f"independent validation expected {expected}, got {result['status']}"
                )
            print(f"{result['status']}: {path.name}")
    except (OSError, ValueError, ImportError) as error:
        parser.exit(3, f"validation: {error}\nInstall .[validation] if ObsPy is missing.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
