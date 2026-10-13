import pytest

from segy_accept.policy import Policy
from segy_accept.reader import AuditInputError, inspect_envelope


def test_independent_bytes_open_in_released_parser(write_segy):
    import segyio

    path = write_segy()
    with segyio.open(str(path), "r", ignore_geometry=True) as data:
        assert data.tracecount == 4
        assert data.header[0][segyio.TraceField.CDP_X] == 10000
        assert list(data.trace[0]) == list(range(8))


def test_supported_envelope_counts_fixed_records(write_segy):
    envelope = inspect_envelope(write_segy())
    assert envelope.trace_count == 4
    assert envelope.samples_per_trace == 8
    assert envelope.sample_interval_us == 2000


def test_truncation_never_passes_preflight(write_segy):
    path = write_segy()
    path.write_bytes(path.read_bytes()[:-1])
    with pytest.raises(AuditInputError, match="record") as error:
        inspect_envelope(path)
    assert error.value.status == "failure"


@pytest.mark.parametrize(
    "options", [{"revision": 512}, {"format_code": 1}, {"fixed": 0}, {"extended": 1}]
)
def test_unsupported_layout_is_explicitly_unknown(write_segy, options):
    with pytest.raises(AuditInputError) as error:
        inspect_envelope(write_segy(**options))
    assert error.value.status == "unknown"


def test_empty_trace_set_is_not_accepted(write_segy):
    with pytest.raises(AuditInputError, match="trace"):
        inspect_envelope(write_segy(traces=[]))


def test_missing_policy_dimensions_stay_optional():
    policy = Policy.from_dict({"schema_version": 1, "name": "minimal", "version": "1"})
    assert policy.coordinates is None
    assert policy.grid is None


def test_complete_policy_is_parsed(policy_data):
    policy = Policy.from_dict(policy_data)
    assert policy.samples_per_trace == 8
    assert policy.grid["inlines"] == [10, 11]


@pytest.mark.parametrize(
    "change",
    [
        {"typo": 1},
        {"schema_version": 2},
        {"sample_interval_us": True},
        {"samples_per_trace": -1},
        {"grid": {"inlines": [1, 1], "crosslines": [2]}},
        {"coordinates": {"units": "metres", "reference": "x", "bounds": [0, float("nan"), 0, 1]}},
    ],
)
def test_policy_rejects_ambiguity_and_mistakes(policy_data, change):
    with pytest.raises(ValueError):
        Policy.from_dict(policy_data | change)
