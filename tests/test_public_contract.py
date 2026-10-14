"""Exercise the installed CLI and assert the schema-1 consumer contract."""

import hashlib
import json
import os
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

import pytest

from segy_accept import __version__
from segy_accept.policy import Policy

RULE_IDS = {
    "format.profile",
    "sampling.consistency",
    "sampling.policy",
    "coordinates.units",
    "coordinates.scalar",
    "coordinates.bounds",
    "geometry.grid",
}
ROOT_KEYS = {
    "schema_version",
    "tool",
    "input",
    "policy",
    "scan",
    "status",
    "coordinate_examples",
    "scope",
    "findings",
}


@pytest.fixture(scope="module")
def corpus(tmp_path_factory):
    directory = tmp_path_factory.mktemp("public-contract") / "demo"
    subprocess.run(
        [sys.executable, "-m", "segy_accept", "demo", str(directory)],
        check=True,
        capture_output=True,
        timeout=30,
    )
    return directory


@pytest.mark.parametrize(
    "name,status",
    [
        ("clean", "accepted"),
        ("readable-broken", "rejected"),
        ("outside-bounds", "rejected"),
        ("unknown-units", "incomplete"),
        ("missing-cell", "rejected"),
        ("truncated", "incomplete"),
        ("unsupported-revision", "incomplete"),
    ],
)
def test_schema_one_is_usable_by_a_json_consumer(corpus, tmp_path, name, status):
    output = tmp_path / "audit"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "segy_accept",
            "audit",
            str(corpus / f"{name}.sgy"),
            "--policy",
            str(corpus / "policy.json"),
            "--out",
            str(output),
        ],
        capture_output=True,
        timeout=30,
    )
    assert completed.returncode == {"accepted": 0, "rejected": 1, "incomplete": 2}[status]
    report = json.loads((output / "audit.json").read_text(encoding="utf-8"))
    assert ROOT_KEYS <= report.keys()
    assert type(report["schema_version"]) is int and report["schema_version"] == 1
    assert report["status"] == status
    assert report["tool"]["version"] == __version__
    assert report["tool"]["name"] == "segy-accept"
    assert type(report["input"]["size_bytes"]) is int
    assert (
        report["input"]["sha256"]
        == hashlib.sha256((corpus / f"{name}.sgy").read_bytes()).hexdigest()
    )
    definition = report["policy"]["definition"]
    Policy.from_dict(definition)  # the emitted policy must be valid replay input
    canonical = json.dumps(
        definition, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()
    assert report["policy"]["sha256"] == hashlib.sha256(canonical).hexdigest()
    assert {f["rule_id"] for f in report["findings"]} == RULE_IDS
    assert len(report["findings"]) == len(RULE_IDS)
    for finding in report["findings"]:
        assert {"rule_id", "title", "status", "count", "examples", "next_step"} <= finding.keys()
        assert finding["status"] in ["pass", "warning", "failure", "unknown"]
        assert type(finding["count"]) is int and finding["count"] >= 0
        assert len(finding["examples"]) <= definition["example_limit"]
    scan = report["scan"]
    assert type(scan["complete"]) is bool and scan["mode"] == "full"
    assert type(scan["traces_inspected"]) is int and scan["traces_inspected"] >= 0
    assert scan["traces_expected"] is None or type(scan["traces_expected"]) is int
    statuses = {finding["status"] for finding in report["findings"]}
    if status == "accepted":
        assert scan["complete"] and not statuses.intersection({"failure", "unknown"})
    elif status == "rejected":
        assert scan["complete"] and "failure" in statuses
    else:
        assert not scan["complete"] or "unknown" in statuses
    assert (output / "audit.html").is_file()


def test_installed_console_exposes_version_and_invocation_errors():
    assert version("segy-accept") == __version__
    command = Path(sys.executable).with_name(
        "segy-accept.exe" if os.name == "nt" else "segy-accept"
    )
    result = subprocess.run([str(command), "--version"], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0 and result.stdout.strip() == f"segy-accept {__version__}"
    result = subprocess.run([str(command), "audit"], capture_output=True, timeout=30)
    assert result.returncode == 3
