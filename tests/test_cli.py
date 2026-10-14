import json

import pytest

from segy_accept import __version__
from segy_accept.cli import main
from segy_accept.report import render_html


def invoke(path, tmp_path, policy_data, *extra):
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps(policy_data), encoding="utf-8")
    output = tmp_path / "reports"
    code = main(["audit", str(path), "--policy", str(policy), "--out", str(output), *extra])
    return code, output


def test_cli_creates_reproducible_reports(write_segy, tmp_path, policy_data):
    path = write_segy()
    code, output = invoke(path, tmp_path, policy_data)
    assert code == 0
    original = (output / "audit.json").read_bytes()
    code, _ = invoke(path, tmp_path, policy_data, "--overwrite")
    assert code == 0
    assert (output / "audit.json").read_bytes() == original
    html = (output / "audit.html").read_text(encoding="utf-8")
    assert "accepted" in html.lower()
    assert "sampling.consistency" in html
    assert "http://" not in html and "https://" not in html  # offline report, no assets


def test_existing_report_requires_explicit_overwrite(write_segy, tmp_path, policy_data):
    path = write_segy()
    invoke(path, tmp_path, policy_data)
    code, _ = invoke(path, tmp_path, policy_data)
    assert code == 3


def test_truncated_input_still_creates_actionable_report(write_segy, tmp_path, policy_data):
    path = write_segy()
    path.write_bytes(path.read_bytes()[:100])
    code, output = invoke(path, tmp_path, policy_data)
    assert code == 2
    assert json.loads((output / "audit.json").read_text())["scan"]["complete"] is False


def test_completed_rejection_exit_code(write_segy, tmp_path, policy_data):
    path = write_segy(traces=[{"dt": 9000}])
    assert invoke(path, tmp_path, policy_data)[0] == 1


def test_invalid_policy_has_no_report(write_segy, tmp_path, policy_data):
    code, output = invoke(write_segy(), tmp_path, policy_data | {"typo": 1})
    assert code == 3
    assert not output.exists()


def test_output_must_not_alias_source(write_segy, tmp_path, policy_data):
    path = write_segy(name="audit.json")
    original = path.read_bytes()
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps(policy_data))
    code = main(
        ["audit", str(path), "--policy", str(policy), "--out", str(tmp_path), "--overwrite"]
    )
    assert code == 3
    assert path.read_bytes() == original


def test_output_must_not_alias_policy(write_segy, tmp_path, policy_data):
    path = write_segy()
    policy = tmp_path / "audit.json"
    original = json.dumps(policy_data)
    policy.write_text(original)
    code = main(
        ["audit", str(path), "--policy", str(policy), "--out", str(tmp_path), "--overwrite"]
    )
    assert code == 3
    assert policy.read_text() == original


def test_html_escapes_untrusted_policy_and_filename(write_segy, policy_data):
    from segy_accept.audit import audit
    from segy_accept.policy import Policy

    result = audit(
        write_segy(), Policy.from_dict(policy_data | {"name": "<script>alert(1)</script>"})
    )
    result["input"]["name"] = '<img src=x onerror="alert(1)">'
    html = render_html(result)
    assert "<script>" not in html and "<img src=x" not in html
    assert "&lt;script&gt;" in html and "&lt;img" in html


def test_demo_reproduces_expected_decisions(tmp_path):
    destination = tmp_path / "demo"
    assert main(["demo", str(destination)]) == 0
    manifest = json.loads((destination / "manifest.json").read_text())
    assert len(manifest["cases"]) >= 6
    for case in manifest["cases"]:
        result = json.loads((destination / case["report"] / "audit.json").read_text())
        assert result["status"] == case["expected_status"]
        for rule, expected in case["expected_findings"].items():
            finding = next(x for x in result["findings"] if x["rule_id"] == rule)
            assert finding["status"] == expected
    assert main(["demo", str(destination)]) == 3  # do not clobber an existing directory


@pytest.mark.parametrize("argv", [[], ["audit", "missing"], ["invalid"]])
def test_invalid_invocation_is_code_three(argv):
    assert main(argv) == 3


def test_oversized_numeric_bound_is_an_invalid_policy(write_segy, tmp_path, policy_data):
    policy_data["coordinates"]["bounds"][1] = 10**400
    code, _ = invoke(write_segy(), tmp_path, policy_data)
    assert code == 3


def test_duplicate_policy_keys_are_refused(write_segy, tmp_path):
    path = write_segy()
    policy = tmp_path / "policy.json"
    policy.write_text('{"schema_version":1,"name":"first","name":"second","version":"1"}')
    assert main(["audit", str(path), "--policy", str(policy), "--out", str(tmp_path / "out")]) == 3


def test_overwrite_cannot_truncate_a_hardlinked_source(write_segy, tmp_path, policy_data):
    import os

    path = write_segy()
    original = path.read_bytes()
    output = tmp_path / "reports"
    output.mkdir()
    os.link(path, output / "audit.json")
    assert invoke(path, tmp_path, policy_data, "--overwrite")[0] == 3
    assert path.read_bytes() == original


@pytest.mark.parametrize("depth", [1200, 20000])
def test_deeply_nested_json_is_an_invalid_policy(write_segy, tmp_path, depth):
    path = write_segy()
    policy = tmp_path / "policy.json"
    policy.write_text("[" * depth + "0" + "]" * depth)
    assert main(["audit", str(path), "--policy", str(policy), "--out", str(tmp_path / "out")]) == 3


def test_terminal_explains_rejection_and_points_to_reports(
    write_segy, tmp_path, policy_data, capsys
):
    path = write_segy(traces=[{"dt": 4000}])
    code, output = invoke(path, tmp_path, policy_data | {"grid": None})
    assert code == 1
    text = capsys.readouterr().out
    assert "FAILURE sampling.consistency" in text
    assert "Confirm sample count/interval with the producer" in text
    assert "UNKNOWN geometry.grid" in text
    assert text.index("FAILURE sampling.consistency") < text.index("UNKNOWN geometry.grid")
    assert str((output / "audit.html").resolve()) in text
    assert str((output / "audit.json").resolve()) in text


def test_terminal_explains_missing_expectations(write_segy, tmp_path, capsys):
    code, _ = invoke(
        write_segy(), tmp_path, {"schema_version": 1, "name": "minimal", "version": "1"}
    )
    assert code == 2
    text = capsys.readouterr().out
    assert "UNKNOWN sampling.policy" in text
    assert "Supply both sampling expectations" in text


def test_accepted_terminal_result_does_not_suggest_repairs(
    write_segy, tmp_path, policy_data, capsys
):
    assert invoke(write_segy(), tmp_path, policy_data)[0] == 0
    text = capsys.readouterr().out
    assert "accepted" in text
    assert "FAILURE" not in text and "UNKNOWN" not in text
    assert "No blocking findings" in text


def test_terminal_explains_unsupported_input(write_segy, tmp_path, policy_data, capsys):
    code, _ = invoke(write_segy(revision=512), tmp_path, policy_data)
    assert code == 2
    text = capsys.readouterr().out
    assert "unsupported profile: requires revision 1.0" in text
    assert "Scan incomplete" in text


def test_accepted_with_warning_still_surfaces_the_warning(
    write_segy, tmp_path, policy_data, capsys
):
    path = write_segy(traces=[{"scalar": 0, "x": 1000, "y": 2000}])
    policy_data["grid"] = {"inlines": [10], "crosslines": [20]}
    assert invoke(path, tmp_path, policy_data)[0] == 0
    text = capsys.readouterr().out
    assert "WARNING coordinates.scalar" in text
    assert "No blocking findings" in text


def test_cli_identifies_its_version_without_an_input(capsys):
    assert main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == f"segy-accept {__version__}"
