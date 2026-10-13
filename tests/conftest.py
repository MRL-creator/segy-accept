"""Independent stdlib byte writer: no segyio calls define the test oracle."""

import struct

import pytest


@pytest.fixture
def write_segy(tmp_path):
    def write(
        name="survey.sgy",
        traces=None,
        ns=8,
        dt=2000,
        revision=256,
        format_code=5,
        fixed=1,
        extended=0,
        measurement=1,
    ):
        if traces is None:
            traces = [
                {
                    "inline": i,
                    "crossline": j,
                    "x": 10000 + (i - 10) * 100,
                    "y": 20000 + (j - 20) * 100,
                }
                for i in [10, 11]
                for j in [20, 21]
            ]
        data = bytearray(b" " * 3200 + bytes(400))
        for offset, fmt, value in [
            (3216, "H", dt),
            (3220, "H", ns),
            (3224, "H", format_code),
            (3254, "H", measurement),
            (3500, "H", revision),
            (3502, "H", fixed),
            (3504, "h", extended),
        ]:
            struct.pack_into(">" + fmt, data, offset, value)
        fields = {
            "scalar": (70, "h", -10),
            "units": (88, "h", 1),
            "ns": (114, "H", ns),
            "dt": (116, "H", dt),
            "x": (180, "i", 10000),
            "y": (184, "i", 20000),
            "inline": (188, "i", 10),
            "crossline": (192, "i", 20),
        }
        for trace in traces:
            header = bytearray(240)
            for key, (offset, fmt, default) in fields.items():
                struct.pack_into(">" + fmt, header, offset, trace.get(key, default))
            data.extend(header)
            data.extend(struct.pack(">" + "f" * ns, *range(ns)))
        path = tmp_path / name
        path.write_bytes(data)
        return path

    return write


@pytest.fixture
def policy_data():
    return {
        "schema_version": 1,
        "name": "synthetic-poststack",
        "version": "1",
        "sample_interval_us": 2000,
        "samples_per_trace": 8,
        "coordinates": {
            "units": "metres",
            "reference": "synthetic local grid",
            "bounds": [900, 1100, 1900, 2100],
        },
        "grid": {"inlines": [10, 11], "crosslines": [20, 21]},
    }
