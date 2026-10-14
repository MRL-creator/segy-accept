"""Reproducible isolated-process measurements; optional psutil dependency."""

import argparse
import hashlib
import json
import math
import os
import platform
import statistics
import struct
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from .audit import audit, sha256_file
from .cli import load_policy
from .policy import integer
from .reader import MAX_BYTES, MAX_TRACES
from .report import json_text


def generate_workload(destination, traces, samples):
    """Write one record at a time; never allocate a seismic cube."""
    integer(traces, "traces", maximum=MAX_TRACES)
    integer(samples, "samples", maximum=32767)
    file_bytes = 3600 + traces * (240 + samples * 4)
    if file_bytes > MAX_BYTES:
        raise ValueError("benchmark file exceeds the auditor's 2 GiB limit")
    rows = math.isqrt(traces)
    while traces % rows:
        rows -= 1
    columns = traces // rows
    policy = {
        "schema_version": 1,
        "name": "generated-benchmark",
        "version": "1",
        "samples_per_trace": samples,
        "sample_interval_us": 2000,
        "coordinates": {
            "units": "metres",
            "reference": "synthetic benchmark grid",
            "bounds": [0, rows * 10, 0, columns * 10],
        },
        "grid": {"inlines": list(range(1, rows + 1)), "crosslines": list(range(1, columns + 1))},
    }
    policy_json = json_text(policy)
    if len(policy_json.encode()) > 1024 * 1024:
        raise ValueError("benchmark grid policy exceeds the 1 MiB policy limit")
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    path = destination / "input.sgy"
    envelope = bytearray(b" " * 3200 + bytes(400))
    for offset, value in [
        (3216, 2000),
        (3220, samples),
        (3224, 5),
        (3254, 1),
        (3500, 256),
        (3502, 1),
    ]:
        struct.pack_into(">H", envelope, offset, value)
    payload = bytes(samples * 4)
    with path.open("xb") as stream:
        stream.write(envelope)
        for i in range(1, rows + 1):
            for j in range(1, columns + 1):
                header = bytearray(240)
                for offset, value in [(70, 1), (88, 1), (114, samples), (116, 2000)]:
                    struct.pack_into(">h", header, offset, value)
                for offset, value in [(180, i * 10), (184, j * 10), (188, i), (192, j)]:
                    struct.pack_into(">i", header, offset, value)
                stream.write(header)
                stream.write(payload)
    (destination / "policy.json").write_text(policy_json, encoding="utf-8")
    return {
        "traces": traces,
        "samples": samples,
        "file_bytes": file_bytes,
        "input_sha256": sha256_file(path),
        "grid_shape": [rows, columns],
    }


def worker(path, policy_path):
    policy = load_policy(policy_path)
    start = time.perf_counter()
    result = audit(path, policy)
    elapsed = time.perf_counter() - start
    print(
        json_text(
            {
                "audit_seconds": elapsed,
                "status": result["status"],
                "traces_inspected": result["scan"]["traces_inspected"],
                "input_sha256": result["input"]["sha256"],
            }
        ),
        end="",
    )


def validate_measurement_options(interval, timeout):
    if not math.isfinite(interval) or not 0 < interval <= 1:
        raise ValueError("RSS sampling interval must be finite and between 0 and 1 second")
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be finite and positive")


def measure_process(path, policy_path, interval=0.005, timeout=120):
    """RSS is sampled over child startup + audit; audit timing excludes imports/output."""
    import psutil

    validate_measurement_options(interval, timeout)
    command = [
        sys.executable,
        "-m",
        "segy_accept.benchmark",
        "--worker",
        str(path),
        str(policy_path),
    ]
    peak, samples = 0, 0
    started = time.perf_counter()
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(command, stdout=output, stderr=errors)
        try:
            monitored = psutil.Process(process.pid)
            while process.poll() is None:
                if time.perf_counter() - started > timeout:
                    raise TimeoutError("benchmark worker exceeded its timeout")
                try:
                    peak = max(peak, monitored.memory_info().rss)
                    samples += 1
                except psutil.NoSuchProcess:
                    break
                time.sleep(interval)
            process.wait(timeout=timeout)
            if process.returncode:
                errors.seek(0)
                raise RuntimeError(
                    f"benchmark worker failed: {errors.read(4096).decode(errors='replace')}"
                )
            output.seek(0)
            result = json.load(output)
            if not samples or not peak:
                raise RuntimeError("no usable RSS samples were collected")
            result.update(
                sampled_peak_rss_bytes=peak,
                rss_samples=samples,
                process_seconds=time.perf_counter() - started,
            )
            return result
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()


def summarize(runs):
    elapsed = [r["audit_seconds"] for r in runs]
    return {
        "median_audit_seconds": statistics.median(elapsed),
        "min_audit_seconds": min(elapsed),
        "max_audit_seconds": max(elapsed),
        "max_sampled_peak_rss_bytes": max(r["sampled_peak_rss_bytes"] for r in runs),
    }


def git_metadata(source):
    """Only report provenance when this source belongs to a tracked checkout."""

    def run(*args):
        return subprocess.run(["git", *args], cwd=source, capture_output=True, text=True)

    try:
        tracked = run("ls-files", "--error-unmatch", "benchmark.py")
        if tracked.returncode:
            return None, None
        revision = run("rev-parse", "HEAD")
        dirty = run("status", "--porcelain")
    except OSError:
        return None, None
    return (
        revision.stdout.strip() if revision.returncode == 0 else None,
        bool(dirty.stdout.strip()) if dirty.returncode == 0 else None,
    )


def environment():
    import psutil

    source = Path(__file__).parent
    digest = hashlib.sha256()
    for file in sorted(source.glob("*.py")):
        digest.update(file.name.encode() + b"\0" + file.read_bytes())
    revision, dirty = git_metadata(source)
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "logical_cpus": psutil.cpu_count(),
        "physical_cpus": psutil.cpu_count(logical=False),
        "total_ram_bytes": psutil.virtual_memory().total,
        "versions": {p: version(p) for p in ["segyio", "numpy", "psutil"]},
        "thread_environment": {
            k: os.environ.get(k)
            for k in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]
        },
        "git_revision": revision,
        "git_dirty": dirty,
        "package_source_sha256": digest.hexdigest(),
    }


def run_suite(destination, traces, samples=256, repeats=5, interval=0.005, timeout=120):
    validate_measurement_options(interval, timeout)
    integer(repeats, "repeats", maximum=20)
    if not traces or any(type(n) is not int or not 1 <= n <= MAX_TRACES for n in traces):
        raise ValueError(
            "trace counts must be nonempty positive integers within the supported limit"
        )
    integer(samples, "samples", maximum=32767)
    if sum(3600 + n * (240 + samples * 4) for n in traces) > 512 * 1024**2:
        raise ValueError("benchmark suite exceeds its 512 MiB generated-data budget")
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    result = {
        "schema_version": 1,
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": environment(),
        "rss_sample_interval_seconds": interval,
        "method": "One discarded warm-up per case; independent fresh process per repeat; cache not flushed. Generation/reporting excluded from audit time. RSS includes process startup and may miss transients.",
        "cases": [],
    }
    for index, count in enumerate(traces):
        directory = destination / f"case-{index}"
        case = generate_workload(directory, count, samples)
        path, policy = directory / "input.sgy", directory / "policy.json"
        warmup = measure_process(path, policy, interval, timeout)
        runs = [measure_process(path, policy, interval, timeout) for _ in range(repeats)]
        for observation in [warmup, *runs]:
            if (
                observation["status"] != "accepted"
                or observation["traces_inspected"] != count
                or observation["input_sha256"] != case["input_sha256"]
            ):
                raise ValueError("benchmark correctness/fingerprint check failed")
        case.update(warmup=warmup, runs=runs, summary=summarize(runs))
        result["cases"].append(case)
        (destination / "results.json").write_text(json_text(result), encoding="utf-8")
        print(
            f"{count} traces: median {case['summary']['median_audit_seconds']:.3f}s; sampled peak {case['summary']['max_sampled_peak_rss_bytes'] / 1024**2:.1f} MiB",
            flush=True,
        )
    return result


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) == 3 and argv[0] == "--worker":
        worker(argv[1], argv[2])
        return 0
    parser = argparse.ArgumentParser(
        description="Measure audit time and sampled process RSS on generated data"
    )
    parser.add_argument("directory", type=Path)
    parser.add_argument("--traces", type=int, nargs="+", default=[1000, 10000, 100000])
    parser.add_argument("--samples", type=int, default=256)
    parser.add_argument("--repeats", type=int, default=5)
    args = parser.parse_args(argv)
    try:
        run_suite(args.directory, args.traces, args.samples, args.repeats)
    except (OSError, ValueError, RuntimeError, ImportError, TimeoutError) as error:
        parser.exit(3, f"benchmark: {error}\nInstall .[benchmark] if psutil is missing.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
