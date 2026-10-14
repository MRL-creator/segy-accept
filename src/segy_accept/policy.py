"""Strict, deliberately small receiving-workflow policy."""

import math
from dataclasses import dataclass

MAX_CELLS = 1_000_000


def finite_number(value):
    if type(value) not in [int, float]:
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def integer(value, label, minimum=1, maximum=65535):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{label} must be an integer between {minimum} and {maximum}")
    return value


def keys(data, allowed, required, label):
    if not isinstance(data, dict) or set(data) - allowed or required - set(data):
        raise ValueError(f"{label} requires {sorted(required)}; allowed keys: {sorted(allowed)}")


@dataclass(frozen=True)
class Policy:
    name: str
    version: str
    sample_interval_us: int | None = None
    samples_per_trace: int | None = None
    coordinates: dict | None = None
    grid: dict | None = None
    example_limit: int = 5

    @classmethod
    def from_dict(cls, data):
        required = {"schema_version", "name", "version"}
        allowed = required | {
            "sample_interval_us",
            "samples_per_trace",
            "coordinates",
            "grid",
            "example_limit",
        }
        keys(data, allowed, required, "policy")
        if type(data["schema_version"]) is not int or data["schema_version"] != 1:
            raise ValueError("schema_version must be 1")
        for label in ["name", "version"]:
            if not isinstance(data[label], str) or not data[label].strip():
                raise ValueError(f"{label} must be a nonempty string")
        for label in ["sample_interval_us", "samples_per_trace"]:
            if data.get(label) is not None:
                integer(data[label], label, maximum=32767)
        coordinates = data.get("coordinates")
        if coordinates is not None:
            required_coords = {"units", "reference", "bounds"}
            keys(coordinates, required_coords, required_coords, "coordinates")
            if coordinates["units"] not in ["metres", "feet", "decimal_degrees"]:
                raise ValueError("coordinates.units must be metres, feet, or decimal_degrees")
            if (
                not isinstance(coordinates["reference"], str)
                or not coordinates["reference"].strip()
            ):
                raise ValueError(
                    "coordinates.reference must explicitly describe the coordinate basis"
                )
            bounds = coordinates["bounds"]
            if (
                not isinstance(bounds, list)
                or len(bounds) != 4
                or not all(finite_number(v) for v in bounds)
            ):
                raise ValueError("bounds must be four finite numbers: xmin,xmax,ymin,ymax")
            if bounds[0] > bounds[1] or bounds[2] > bounds[3]:
                raise ValueError("bounds minima must not exceed maxima")
            if coordinates["units"] == "decimal_degrees" and not (
                -180 <= bounds[0] <= bounds[1] <= 180 and -90 <= bounds[2] <= bounds[3] <= 90
            ):
                raise ValueError("decimal-degree bounds exceed longitude/latitude limits")
        grid = data.get("grid")
        if grid is not None:
            keys(grid, {"inlines", "crosslines"}, {"inlines", "crosslines"}, "grid")
            for label, values in grid.items():
                if not isinstance(values, list) or not values or len(values) > MAX_CELLS:
                    raise ValueError(
                        f"grid.{label} must be a nonempty list of at most {MAX_CELLS} values"
                    )
                for value in values:
                    integer(value, label, -(2**31), 2**31 - 1)
                if len(set(values)) != len(values):
                    raise ValueError(f"grid.{label} contains duplicate values")
            if len(grid["inlines"]) * len(grid["crosslines"]) > MAX_CELLS:
                raise ValueError(f"expected grid exceeds {MAX_CELLS} cells")
        example_limit = integer(data.get("example_limit", 5), "example_limit", 1, 100)
        return cls(
            data["name"],
            data["version"],
            data.get("sample_interval_us"),
            data.get("samples_per_trace"),
            coordinates,
            grid,
            example_limit,
        )
