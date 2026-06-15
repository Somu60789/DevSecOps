"""Unit tests for scripts/collect-findings.py — scanner-output normalization."""
import importlib.util
import json
from pathlib import Path

# Load the hyphenated module by path (not importable via normal import syntax).
_MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "collect-findings.py"
_spec = importlib.util.spec_from_file_location("collect_findings", _MODULE_PATH)
cf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cf)


def _write(tmp_path, name, payload):
    p = tmp_path / name
    p.write_text(json.dumps(payload))
    return p


def test_empty_input_produces_empty_findings(tmp_path):
    result = cf.collect(inputs=[], generated_at="2026-06-16T00:00:00Z")
    assert result["schema_version"] == "1"
    assert result["findings"] == []
    assert result["summary"]["by_severity"] == {}
    assert result["summary"]["scanner_errors"] == []


def test_normalizes_severity_to_five_level_scale():
    assert cf.normalize_severity("ERROR") == "high"
    assert cf.normalize_severity("WARNING") == "medium"
    assert cf.normalize_severity("CRITICAL") == "critical"
    assert cf.normalize_severity("note") == "info"
    assert cf.normalize_severity("totally-unknown") == "info"


def test_stable_id_is_deterministic_and_dedupes():
    a = cf.finding_id("gitleaks", "generic-api-key", "src/app.py", 12)
    b = cf.finding_id("gitleaks", "generic-api-key", "src/app.py", 12)
    c = cf.finding_id("gitleaks", "generic-api-key", "src/app.py", 13)
    assert a == b           # same inputs -> same id
    assert a != c           # different line -> different id


def test_gitleaks_secret_finding(tmp_path):
    gl = _write(tmp_path, "gitleaks.json", [
        {"RuleID": "aws-access-key", "Description": "AWS key",
         "File": "src/conf.py", "StartLine": 7, "Secret": "AKIA..."},
    ])
    result = cf.collect(
        inputs=[{"tool": "gitleaks", "category": "secret", "path": str(gl)}],
        generated_at="2026-06-16T00:00:00Z",
    )
    assert len(result["findings"]) == 1
    f = result["findings"][0]
    assert f["tool"] == "gitleaks"
    assert f["category"] == "secret"
    assert f["file"] == "src/conf.py"
    assert f["line"] == 7
    assert f["rule_id"] == "aws-access-key"
    assert f["severity"] == "critical"   # secrets are always critical


def test_sarif_finding_per_category(tmp_path):
    sarif = _write(tmp_path, "semgrep.sarif", {
        "runs": [{
            "tool": {"driver": {"name": "semgrep", "rules": [
                {"id": "py.lang.security.audit", "defaultConfiguration": {"level": "error"}}
            ]}},
            "results": [{
                "ruleId": "py.lang.security.audit",
                "level": "error",
                "message": {"text": "Possible SQL injection"},
                "locations": [{"physicalLocation": {
                    "artifactLocation": {"uri": "src/db.py"},
                    "region": {"startLine": 42}}}],
            }],
        }],
    })
    result = cf.collect(
        inputs=[{"tool": "semgrep", "category": "sast", "path": str(sarif)}],
        generated_at="2026-06-16T00:00:00Z",
    )
    assert len(result["findings"]) == 1
    f = result["findings"][0]
    assert f["category"] == "sast"
    assert f["file"] == "src/db.py"
    assert f["line"] == 42
    assert f["severity"] == "high"       # SARIF error -> high
    assert "SQL injection" in f["message"]


def test_missing_scanner_output_recorded_as_error(tmp_path):
    result = cf.collect(
        inputs=[{"tool": "trivy", "category": "sca",
                 "path": str(tmp_path / "does-not-exist.json")}],
        generated_at="2026-06-16T00:00:00Z",
    )
    assert result["findings"] == []
    errs = result["summary"]["scanner_errors"]
    assert len(errs) == 1
    assert errs[0]["tool"] == "trivy"


def test_summary_counts_by_severity_and_category(tmp_path):
    gl = _write(tmp_path, "gitleaks.json", [
        {"RuleID": "k", "Description": "d", "File": "a.py", "StartLine": 1, "Secret": "x"},
    ])
    sarif = _write(tmp_path, "s.sarif", {"runs": [{
        "tool": {"driver": {"name": "semgrep"}},
        "results": [{"ruleId": "r", "level": "warning",
                     "message": {"text": "m"},
                     "locations": [{"physicalLocation": {
                         "artifactLocation": {"uri": "b.py"},
                         "region": {"startLine": 2}}}]}],
    }]})
    result = cf.collect(inputs=[
        {"tool": "gitleaks", "category": "secret", "path": str(gl)},
        {"tool": "semgrep", "category": "sast", "path": str(sarif)},
    ], generated_at="2026-06-16T00:00:00Z")
    assert result["summary"]["by_severity"]["critical"] == 1
    assert result["summary"]["by_severity"]["medium"] == 1
    assert result["summary"]["by_category"]["secret"] == 1
    assert result["summary"]["by_category"]["sast"] == 1
