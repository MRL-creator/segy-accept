"""Check the committed, independently specified corpus and portable output."""

import json
from pathlib import Path

from segy_accept.audit import audit
from segy_accept.cli import load_policy
from segy_accept.report import json_text, render_html


def test_committed_corpus_has_expected_outcomes():
    examples = Path(__file__).resolve().parents[1] / "examples"
    manifest = json.loads((examples / "manifest.json").read_text())
    policy = load_policy(examples / "policy.json")
    for case in manifest["cases"]:
        result = audit(examples / case["file"], policy)
        assert result["status"] == case["expected_status"]
        actual = {f["rule_id"]: f["status"] for f in result["findings"]}
        for rule, status in case["expected_findings"].items():
            assert actual[rule] == status


def test_checked_in_report_matches_current_tool():
    examples = Path(__file__).resolve().parents[1] / "examples"
    result = audit(examples / "readable-broken.sgy", load_policy(examples / "policy.json"))
    assert (examples / "sample-report.json").read_text(encoding="utf-8") == json_text(result)
    assert (examples / "sample-report.html").read_text(encoding="utf-8") == render_html(result)
