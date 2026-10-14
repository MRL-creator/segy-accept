import hashlib
import runpy
import subprocess
import sys
import tempfile
import venv
from contextlib import nullcontext
from pathlib import Path

import pytest


def test_field_integrity_checks_remain_active_with_python_optimization():
    script = Path(__file__).resolve().parents[1] / "tools" / "validate_f3.py"
    result = subprocess.run(
        [
            sys.executable,
            "-O",
            "-c",
            f"import runpy; m=runpy.run_path({str(script)!r}); m['inspect_independently'](b'x'*m['SIZE'])",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode != 0
    assert "fingerprint" in result.stderr


@pytest.mark.parametrize("duplicate", [False, True])
def test_similarity_oracle_independently_checks_grid_uniqueness(write_segy, monkeypatch, duplicate):
    module = runpy.run_path(str(Path(__file__).resolve().parents[1] / "tools" / "validate_f3.py"))
    traces = None if not duplicate else [{"inline": 10, "crossline": 20}] * 4
    data = write_segy(traces=traces, ns=51, dt=4000).read_bytes()
    spec = module["SAMPLES"]["similarity"] | {
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "grid": [10, 11, 20, 21],
    }
    monkeypatch.setitem(module["SAMPLES"], "similarity", spec)
    if duplicate:
        with pytest.raises(ValueError, match="duplicate"):
            module["inspect_independently"](data, "similarity")
    else:
        observed = module["inspect_independently"](data, "similarity")
        assert observed["traces"] == 4
        assert observed["inline_range"] == [10, 11]


def test_field_sampling_case_cannot_pass_due_to_an_unrelated_grid_failure(
    write_segy, tmp_path, monkeypatch
):
    module = runpy.run_path(str(Path(__file__).resolve().parents[1] / "tools" / "validate_f3.py"))
    namespace = module["validate"].__globals__
    path = write_segy(ns=51, dt=4000)
    fingerprint = hashlib.sha256(path.read_bytes()).hexdigest()
    monkeypatch.setitem(
        module["SAMPLES"],
        "similarity",
        module["SAMPLES"]["similarity"] | {"size": path.stat().st_size, "sha256": fingerprint},
    )
    monkeypatch.setitem(namespace, "inspect_independently", lambda *args: {"traces": 4})
    monkeypatch.setitem(namespace, "save_reports", lambda *args: None)

    def incorrect_audit(path, policy):
        status = (
            "rejected"
            if policy.sample_interval_us == 2000
            else "incomplete"
            if policy.grid is None
            else "rejected"
            if len(policy.grid["inlines"]) == 201
            else "accepted"
        )
        return {
            "status": status,
            "scan": {"complete": True, "traces_inspected": 4},
            "input": {"sha256": fingerprint},
            "findings": [
                {"rule_id": "geometry.grid", "status": "failure", "count": 12515},
                {"rule_id": "sampling.policy", "status": "pass", "examples": []},
            ],
        }

    monkeypatch.setitem(namespace, "audit", incorrect_audit)
    with pytest.raises(ValueError, match="sampling-policy"):
        module["validate"](path, tmp_path / "reports", sample="similarity")


def test_wheel_checker_selects_current_version_when_older_artifacts_remain(tmp_path, monkeypatch):
    from segy_accept import __version__

    script = Path(__file__).resolve().parents[1] / "tools" / "check_wheel.py"
    commands = []
    monkeypatch.setattr(tempfile, "TemporaryDirectory", lambda: nullcontext(str(tmp_path)))
    monkeypatch.setattr(venv.EnvBuilder, "create", lambda *args: None)
    monkeypatch.setattr(Path, "is_file", lambda self: True)
    monkeypatch.setattr(
        Path,
        "glob",
        lambda self, pattern: [
            self / "segy_accept-0.1.0-py3-none-any.whl",
            self / f"segy_accept-{__version__}-py3-none-any.whl",
        ],
    )

    def record(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", record)
    runpy.run_path(str(script))
    assert any(
        str(arg).endswith(f"segy_accept-{__version__}-py3-none-any.whl")
        for command in commands
        for arg in command
    )
