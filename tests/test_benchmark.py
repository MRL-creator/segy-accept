import json
import subprocess
from pathlib import Path

import pytest

from segy_accept.audit import audit
from segy_accept.benchmark import (
    generate_workload,
    git_metadata,
    measure_process,
    run_suite,
    stop_process_tree,
    summarize,
)
from segy_accept.cli import load_policy


def test_benchmark_generator_is_streamed_and_matches_declared_workload(tmp_path):
    case = generate_workload(tmp_path / "case", traces=12, samples=32)
    path = tmp_path / "case" / "input.sgy"
    assert path.stat().st_size == 3600 + 12 * (240 + 32 * 4)
    result = audit(path, load_policy(tmp_path / "case" / "policy.json"))
    assert result["status"] == "accepted"
    assert result["scan"]["traces_inspected"] == 12
    assert case["file_bytes"] == path.stat().st_size


@pytest.mark.parametrize(
    "traces,samples",
    [(0, 32), (True, 32), (12, 0), (12, 40000), (1_000_001, 32), (1_000_000, 32767)],
)
def test_benchmark_rejects_invalid_or_excessive_workload_before_writing(tmp_path, traces, samples):
    destination = tmp_path / "case"
    with pytest.raises(ValueError):
        generate_workload(destination, traces, samples)
    assert not destination.exists()


def test_benchmark_never_overwrites_an_existing_directory(tmp_path):
    with pytest.raises(FileExistsError):
        generate_workload(tmp_path, 10, 32)


def test_summary_retains_raw_repeats_and_reports_spread():
    runs = [{"audit_seconds": n, "sampled_peak_rss_bytes": n * 1000} for n in [1, 2, 3, 4, 5]]
    summary = summarize(runs)
    assert summary["median_audit_seconds"] == 3
    assert summary["min_audit_seconds"] == 1
    assert summary["max_audit_seconds"] == 5
    assert summary["max_sampled_peak_rss_bytes"] == 5000


def test_isolated_measurement_produces_resource_evidence(tmp_path):
    directory = tmp_path / "case"
    generate_workload(directory, 30, 16)
    run = measure_process(
        directory / "input.sgy", directory / "policy.json", interval=0.005, timeout=30
    )
    assert run["status"] == "accepted"
    assert run["traces_inspected"] == 30
    assert run["audit_seconds"] > 0
    assert run["sampled_peak_rss_bytes"] > 0
    assert run["rss_samples"] > 0
    assert run["process_seconds"] >= run["audit_seconds"]
    assert run["worker_pid"] in run["rss_processes_observed"]
    json.dumps(run, allow_nan=False)


@pytest.mark.parametrize("options", [{"interval": 0}, {"timeout": float("nan")}])
def test_invalid_measurement_options_do_not_create_output(tmp_path, options):
    directory = tmp_path / "invalid"
    with pytest.raises(ValueError):
        run_suite(directory, [10], **options)
    assert not directory.exists()


def test_suite_persists_reproducible_workload_and_raw_repeats(tmp_path):
    directory = tmp_path / "suite"
    result = run_suite(directory, [12], samples=16, repeats=2)
    saved = json.loads((directory / "results.json").read_text())
    assert saved == result
    case = saved["cases"][0]
    assert len(case["runs"]) == 2
    assert case["warmup"]["status"] == "accepted"
    assert all(run["input_sha256"] == case["input_sha256"] for run in case["runs"])
    assert case["summary"] == summarize(case["runs"])


def test_failed_worker_is_reported(tmp_path):
    with pytest.raises(RuntimeError, match="benchmark worker failed"):
        measure_process(tmp_path / "missing.sgy", tmp_path / "missing.json")


def test_git_metadata_is_optional_when_git_is_unavailable(tmp_path, monkeypatch):
    def missing(*args, **kwargs):
        raise FileNotFoundError("git unavailable")

    monkeypatch.setattr(subprocess, "run", missing)
    assert git_metadata(tmp_path) == (None, None)


def test_git_metadata_uses_tracked_package_source_not_callers_directory(tmp_path, monkeypatch):
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        output = "abc123\n" if command[1] == "rev-parse" else ""
        return subprocess.CompletedProcess(command, 0, output, "")

    monkeypatch.setattr(subprocess, "run", run)
    source = Path(__file__).parent.parent / "src" / "segy_accept"
    assert git_metadata(source) == ("abc123", False)
    assert all(kwargs["cwd"] == source for _, kwargs in calls)
    assert calls[0][0][1:] == ["ls-files", "--error-unmatch", "benchmark.py"]


def test_untracked_installed_source_does_not_claim_enclosing_repository(tmp_path, monkeypatch):
    monkeypatch.setattr(
        subprocess, "run", lambda command, **kwargs: subprocess.CompletedProcess(command, 1, "", "")
    )
    assert git_metadata(tmp_path) == (None, None)


def test_timeout_cleanup_discovers_unsampled_child_and_cleans_orphans(monkeypatch):
    import psutil

    killed = []

    class Process:
        def __init__(self, pid, children=()):
            self.pid, self.descendants = pid, children

        def children(self, recursive):
            return self.descendants

        def kill(self):
            killed.append(self.pid)

    child = Process(2)
    root = Process(1, [child])
    monkeypatch.setattr(psutil, "wait_procs", lambda processes, timeout: (processes, []))
    stop_process_tree(root, {})
    assert killed == [2, 1]
    killed.clear()
    stop_process_tree(None, {child.pid: child})
    assert killed == [2]


def test_worker_timeout_is_reported(tmp_path):
    with pytest.raises(TimeoutError, match="exceeded its timeout"):
        measure_process(tmp_path / "missing.sgy", tmp_path / "missing.json", timeout=0.000001)
