import hashlib
import struct

import numpy as np
from obspy import read

from segy_accept.audit import audit
from segy_accept.cli import load_policy
from segy_accept.validation import generate_independent


def test_independent_writer_output_is_accepted_and_readable(tmp_path):
    destination = tmp_path / "independent"
    manifest = generate_independent(destination)
    path = destination / manifest["input"]
    original = path.read_bytes()
    result = audit(path, load_policy(destination / "policy.json"))
    assert result["status"] == "accepted"
    assert result["scan"]["traces_inspected"] == 4
    assert path.read_bytes() == original
    assert manifest["input_sha256"] == hashlib.sha256(original).hexdigest()
    assert manifest["writer"]["name"] == "ObsPy"
    assert manifest["synthetic"] is True
    assert manifest["fixture_license"] == "MIT"
    # Independent byte inspection and a second reader verify the writer contract.
    assert struct.unpack_from(">H", original, 3500)[0] == 256
    assert struct.unpack_from(">h", original, 3502)[0] == 1
    assert struct.unpack_from(">i", original, 3600 + 180)[0] == 10000
    stream = read(str(path), format="SEGY")
    assert len(stream) == 4
    np.testing.assert_array_equal(stream[0].data, np.arange(64, dtype=np.float32) / 64)


def test_independent_writer_geometry_fault_is_explained(tmp_path):
    destination = tmp_path / "independent"
    manifest = generate_independent(destination)
    result = audit(
        destination / manifest["contradictory_input"], load_policy(destination / "policy.json")
    )
    assert result["status"] == "rejected"
    check = next(f for f in result["findings"] if f["rule_id"] == "geometry.grid")
    assert check["count"] == 2
    assert {e["kind"] for e in check["examples"]} == {"duplicate", "missing"}


def test_independent_generation_refuses_existing_destination(tmp_path):
    import pytest

    with pytest.raises(FileExistsError):
        generate_independent(tmp_path)
