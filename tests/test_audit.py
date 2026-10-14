import hashlib

import pytest

from segy_accept.audit import audit
from segy_accept.policy import Policy


def run(path, data):
    return audit(path, Policy.from_dict(data))


def finding(result, rule):
    return next(item for item in result["findings"] if item["rule_id"] == rule)


def test_clean_declared_grid_is_accepted_without_changing_input(write_segy, policy_data):
    path = write_segy()
    original = path.read_bytes()
    result = run(path, policy_data)
    assert result["status"] == "accepted"
    assert result["scan"] == {
        "mode": "full",
        "complete": True,
        "traces_expected": 4,
        "traces_inspected": 4,
    }
    assert result["input"]["sha256"] == hashlib.sha256(original).hexdigest()
    assert path.read_bytes() == original
    assert run(path, policy_data) == result


def test_readable_sampling_contradiction_is_rejected(write_segy, policy_data):
    path = write_segy(traces=[{"dt": 4000, "ns": 7}])
    result = run(path, policy_data | {"grid": None})
    check = finding(result, "sampling.consistency")
    assert result["status"] == "rejected"
    assert result["scan"]["complete"] is True
    assert check["status"] == "failure"
    assert check["examples"][0]["trace"] == 1


def test_grid_checks_use_explicit_cartesian_expectations(write_segy, policy_data):
    path = write_segy(
        traces=[
            {"inline": 10, "crossline": 20},
            {"inline": 10, "crossline": 20},
            {"inline": 12, "crossline": 22},
        ]
    )
    result = run(path, policy_data)
    check = finding(result, "geometry.grid")
    assert check["count"] == 5  # duplicate + unexpected + three missing cells
    assert {e["kind"] for e in check["examples"]} == {"duplicate", "unexpected", "missing"}


@pytest.mark.parametrize(
    "scalar,raw,scaled,status",
    [
        (10, 100, 1000, "pass"),
        (-10, 10000, 1000, "pass"),
        (1, 1000, 1000, "pass"),
        (0, 1000, 1000, "warning"),
    ],
)
def test_scalars_are_explained(write_segy, policy_data, scalar, raw, scaled, status):
    path = write_segy(traces=[{"scalar": scalar, "x": raw, "y": 2000 if scalar >= 0 else 20000}])
    result = run(path, policy_data | {"grid": None})
    assert finding(result, "coordinates.scalar")["status"] == status
    assert result["coordinate_examples"][0]["scaled_x"] == scaled


def test_unknown_units_never_pass_bounds(write_segy, policy_data):
    result = run(write_segy(traces=[{"units": 0}]), policy_data | {"grid": None})
    assert result["status"] == "incomplete"
    assert finding(result, "coordinates.units")["status"] == "unknown"
    assert finding(result, "coordinates.bounds")["status"] == "unknown"


def test_length_units_require_binary_measurement_system(write_segy, policy_data):
    result = run(write_segy(measurement=2), policy_data)
    assert result["status"] == "rejected"
    assert finding(result, "coordinates.units")["status"] == "failure"


def test_scaled_coordinate_outside_policy_is_rejected(write_segy, policy_data):
    result = run(write_segy(traces=[{"x": 500000}]), policy_data | {"grid": None})
    assert finding(result, "coordinates.bounds")["status"] == "failure"
    assert result["status"] == "rejected"


def test_invalid_scalar_does_not_create_trusted_scaled_coordinates(write_segy, policy_data):
    result = run(write_segy(traces=[{"scalar": 3}]), policy_data | {"grid": None})
    assert finding(result, "coordinates.scalar")["status"] == "failure"
    assert finding(result, "coordinates.bounds")["status"] == "unknown"
    assert result["coordinate_examples"] == []


def test_absent_workflow_expectations_are_unknown(write_segy):
    result = run(write_segy(), {"schema_version": 1, "name": "inspect", "version": "1"})
    assert result["status"] == "incomplete"
    assert finding(result, "sampling.policy")["status"] == "unknown"
    assert finding(result, "geometry.grid")["status"] == "unknown"


def test_partial_policy_is_not_full_acceptance(write_segy, policy_data):
    result = run(write_segy(), policy_data | {"grid": None})
    assert result["status"] == "incomplete"


def test_examples_are_bounded_but_counts_are_complete(write_segy, policy_data):
    path = write_segy(traces=[{"dt": 3000}] * 40)
    result = run(path, policy_data | {"example_limit": 2})
    assert finding(result, "sampling.consistency")["count"] == 40
    assert len(finding(result, "sampling.consistency")["examples"]) == 2
    assert len(result["coordinate_examples"]) == 2


def test_truncated_file_has_an_incomplete_failure_report(write_segy, policy_data):
    path = write_segy()
    path.write_bytes(path.read_bytes()[:-5])
    result = run(path, policy_data)
    assert result["status"] == "incomplete"
    assert result["scan"]["complete"] is False
    assert finding(result, "format.profile")["status"] == "failure"


def test_unsupported_revision_has_unknown_report(write_segy, policy_data):
    result = run(write_segy(revision=512), policy_data)
    assert result["status"] == "incomplete"
    assert finding(result, "format.profile")["status"] == "unknown"


def test_policy_changes_are_visible_in_provenance(write_segy, policy_data):
    path = write_segy()
    first = run(path, policy_data)
    changed = run(path, policy_data | {"sample_interval_us": 1000})
    assert changed["status"] == "rejected"
    assert first["policy"]["sha256"] != changed["policy"]["sha256"]


def test_negative_scalar_preserves_inclusive_decimal_boundary(write_segy, policy_data):
    path = write_segy(traces=[{"x": 35, "y": 0, "scalar": -100, "units": 3}])
    policy_data["coordinates"] = {
        "units": "decimal_degrees",
        "reference": "declared geographic basis",
        "bounds": [0, 0.35, 0, 0],
    }
    policy_data["grid"] = {"inlines": [10], "crosslines": [20]}
    assert run(path, policy_data)["status"] == "accepted"


def test_unit_check_runs_even_when_scalar_is_invalid(write_segy, policy_data):
    path = write_segy(traces=[{"scalar": 3, "units": 0}])
    result = run(path, policy_data)
    assert finding(result, "coordinates.units")["status"] == "unknown"


def test_bounded_evidence_keeps_the_highest_severity(write_segy, policy_data):
    path = write_segy(traces=[{"units": 0}, {"units": 2}])
    result = run(path, policy_data | {"example_limit": 1})
    check = finding(result, "coordinates.units")
    assert check["status"] == "failure"
    assert check["count"] == 2
    assert check["examples"][0]["unit_code"] == 2


def test_oversized_input_has_no_fingerprint_or_acceptance(write_segy, policy_data, monkeypatch):
    from segy_accept import audit as module
    from segy_accept import reader

    monkeypatch.setattr(module, "MAX_BYTES", 1)
    monkeypatch.setattr(reader, "MAX_BYTES", 1)
    result = run(write_segy(), policy_data)
    assert result["status"] == "incomplete"
    assert result["input"]["sha256"] is None
    assert result["scan"]["traces_inspected"] == 0


def test_high_bit_sampling_words_are_not_silently_accepted(write_segy, policy_data):
    path = write_segy(ns=40000, dt=40000)
    result = run(path, policy_data)
    assert result["status"] == "incomplete"
    assert finding(result, "format.profile")["status"] == "failure"


def test_report_policy_can_be_replayed_when_sampling_was_undeclared(write_segy):
    path = write_segy()
    result = run(path, {"schema_version": 1, "name": "inspect", "version": "1"})
    replayed = run(path, result["policy"]["definition"])
    assert replayed == result
