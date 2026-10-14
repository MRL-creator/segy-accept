"""Changing inputs must never produce trusted acceptance or an unbounded read."""

import hashlib
import os
import stat
from pathlib import Path

import pytest

from segy_accept import audit as module
from segy_accept.audit import audit, sha256_file
from segy_accept.cli import load_policy
from segy_accept.policy import Policy
from segy_accept.reader import AuditInputError, inspect_envelope


@pytest.mark.parametrize("operation", [inspect_envelope, sha256_file, load_policy])
def test_nonregular_input_is_refused_before_opening(tmp_path, monkeypatch, operation):
    def forbidden_open(*args, **kwargs):
        pytest.fail("a directory or special input must not be opened")

    monkeypatch.setattr(Path, "open", forbidden_open)
    with pytest.raises(OSError, match="regular file"):
        operation(tmp_path)


@pytest.mark.parametrize("mode", [stat.S_IFIFO, stat.S_IFCHR, stat.S_IFSOCK])
@pytest.mark.parametrize("operation", [inspect_envelope, sha256_file, load_policy])
def test_special_input_is_refused_without_waiting_for_a_stream(
    tmp_path, monkeypatch, operation, mode
):
    monkeypatch.setattr(
        Path, "stat", lambda self: os.stat_result((mode, 1, 1, 1, 0, 0, 0, 0, 0, 0))
    )
    monkeypatch.setattr(Path, "open", lambda *args, **kwargs: pytest.fail("special input opened"))
    with pytest.raises(OSError, match="regular file"):
        operation(tmp_path / "special")


def test_changed_input_invalidates_passed_rules_and_fingerprint(
    write_segy, policy_data, monkeypatch
):
    path = write_segy()
    original = module.sha256_file

    def change_then_hash(source, *args, **kwargs):
        data = bytearray(source.read_bytes())
        data[-1] ^= 1
        source.write_bytes(data)
        current = source.stat()
        os.utime(source, ns=(current.st_atime_ns, current.st_mtime_ns + 1_000_000))
        return original(source, *args, **kwargs)

    monkeypatch.setattr(module, "sha256_file", change_then_hash)
    result = audit(path, Policy.from_dict(policy_data))
    assert result["status"] == "incomplete"
    assert result["scan"]["complete"] is False
    assert result["input"]["sha256"] is None
    assert all(item["status"] != "pass" for item in result["findings"])
    assert any(
        "changed" in example.get("reason", "")
        for item in result["findings"]
        for example in item["examples"]
    )


def test_replaced_input_is_detected_even_with_matching_size_and_mtime(
    write_segy, policy_data, monkeypatch
):
    path = write_segy()
    original = module.sha256_file

    def replace_then_hash(source, *args, **kwargs):
        previous = source.stat()
        replacement = source.with_suffix(".replacement")
        replacement.write_bytes(source.read_bytes())
        os.utime(replacement, ns=(previous.st_atime_ns, previous.st_mtime_ns))
        os.replace(replacement, source)
        return original(source, *args, **kwargs)

    monkeypatch.setattr(module, "sha256_file", replace_then_hash)
    result = audit(path, Policy.from_dict(policy_data))
    assert result["status"] == "incomplete"
    assert result["input"]["sha256"] is None


def test_hash_refuses_a_file_that_exceeds_the_size_guard(tmp_path, monkeypatch):
    path = tmp_path / "large"
    path.write_bytes(b"abcd")
    monkeypatch.setattr(module, "MAX_BYTES", 3)
    with pytest.raises(AuditInputError, match="limit"):
        sha256_file(path)


def test_hash_detects_growth_without_reading_to_an_unbounded_eof(tmp_path, monkeypatch):
    path = tmp_path / "growing"
    path.write_bytes(b"abc")
    original_open = Path.open
    reads = []

    class GrowingStream:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            return self

        def __exit__(self, *args):
            self.stream.close()

        def fileno(self):
            return self.stream.fileno()

        def read(self, count):
            reads.append(count)
            with original_open(path, "ab") as writer:
                writer.write(b"x")
            if len(reads) > 3:
                pytest.fail("hash continued consuming a growing input")
            return self.stream.read(count)

    monkeypatch.setattr(
        Path,
        "open",
        lambda self, *args, **kwargs: GrowingStream(original_open(self, *args, **kwargs)),
    )
    with pytest.raises(AuditInputError, match="changed"):
        sha256_file(path)
    assert sum(reads) <= 4  # original three bytes plus a one-byte growth probe


def test_stable_hash_matches_standard_sha256(tmp_path):
    path = tmp_path / "stable"
    data = b"x" * (1024 * 1024 + 37)
    path.write_bytes(data)
    assert sha256_file(path) == hashlib.sha256(data).hexdigest()


def test_policy_growth_cannot_bypass_the_read_limit(tmp_path, monkeypatch):
    path = tmp_path / "policy.json"
    path.write_text('{"schema_version":1,"name":"p","version":"1"}')
    original_open = Path.open

    def grow_then_open(self, *args, **kwargs):
        with original_open(self, "ab") as writer:
            writer.write(b" " * (1024 * 1024))
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", grow_then_open)
    with pytest.raises(ValueError, match="1 MiB"):
        load_policy(path)


def test_disappearing_input_still_produces_an_incomplete_result(
    write_segy, policy_data, monkeypatch
):
    path = write_segy()
    original = module.sha256_file

    def remove_then_hash(source):
        source.unlink()
        return original(source)

    monkeypatch.setattr(module, "sha256_file", remove_then_hash)
    result = audit(path, Policy.from_dict(policy_data))
    assert result["status"] == "incomplete"
    assert result["input"]["sha256"] is None
    assert not result["coordinate_examples"]
