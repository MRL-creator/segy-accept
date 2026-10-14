"""Independent envelope guard, not a general SEG-Y parser."""

import stat
import struct
from dataclasses import dataclass
from pathlib import Path

MAX_TRACES = 1_000_000
MAX_BYTES = 2 * 1024**3


def regular_file_stat(path):
    info = Path(path).stat()
    if not stat.S_ISREG(info.st_mode):
        raise OSError("input must be a regular file")
    return info


def file_signature(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


class AuditInputError(ValueError):
    def __init__(self, message, status="unknown"):
        super().__init__(message)
        self.status = status


@dataclass(frozen=True)
class Envelope:
    trace_count: int
    samples_per_trace: int
    sample_interval_us: int
    measurement_system: int
    size_bytes: int


def inspect_envelope(path):
    path = Path(path)
    size = regular_file_stat(path).st_size
    if size > MAX_BYTES:
        raise AuditInputError(f"input exceeds initial-release limit of {MAX_BYTES} bytes")
    with path.open("rb") as stream:
        header = stream.read(3600)
    if len(header) < 3600:
        raise AuditInputError("file is shorter than the 3600-byte SEG-Y envelope", "failure")

    def word(offset):
        return struct.unpack_from(">H", header, offset)[0]

    required = [
        (3500, 256, "revision 1.0 / big endian"),
        (3224, 5, "IEEE float format 5"),
        (3502, 1, "fixed-length traces"),
        (3504, 0, "no extended textual headers"),
    ]
    for offset, value, meaning in required:
        if word(offset) != value:
            raise AuditInputError(
                f"unsupported profile: requires {meaning}; byte {offset + 1} is {word(offset)}"
            )
    # Revision 1 section 3.3 defines two's-complement header integers.
    # Some readers accept unsigned extensions; this receiving profile does not.
    ns = struct.unpack_from(">h", header, 3220)[0]
    dt = struct.unpack_from(">h", header, 3216)[0]
    if ns <= 0 or dt <= 0:
        raise AuditInputError("binary sample count and interval must be positive", "failure")
    records, remainder = divmod(size - 3600, 240 + ns * 4)
    if remainder:
        raise AuditInputError(
            "file size does not contain whole fixed-length trace records", "failure"
        )
    if not records:
        raise AuditInputError("file contains no trace records", "failure")
    if records > MAX_TRACES:
        raise AuditInputError(f"trace count exceeds initial-release limit of {MAX_TRACES}")
    return Envelope(records, ns, dt, word(3254), size)
