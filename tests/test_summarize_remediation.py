"""Unit tests for scripts/summarize-remediation.py — PR-body summary builder."""
import importlib.util
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "summarize-remediation.py"
_spec = importlib.util.spec_from_file_location("summarize_remediation", _MODULE_PATH)
sr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sr)


def test_summary_counts_confident_and_risky():
    data = {
        "remediated": [
            {"id": "1", "file": "a.py", "line": 1, "vulnerability": "SQL Injection",
             "confidence": "confident", "summary": "parameterized query"},
            {"id": "2", "file": "b.py", "line": 9, "vulnerability": "XSS",
             "confidence": "risky", "summary": "added output encoding"},
        ],
        "secrets_to_rotate": [{"file": "c.py", "line": 3, "note": "rotate"}],
        "unresolved": [],
    }
    out = sr.summarize(data)
    assert "2 finding" in out               # total remediated
    assert "1 risky" in out or "risky: 1" in out.lower()
    assert "SQL Injection" in out
    assert "rotate" in out.lower()


def test_unresolved_findings_are_called_out():
    data = {"remediated": [], "secrets_to_rotate": [],
            "unresolved": [{"id": "9", "reason": "needs more context"}]}
    out = sr.summarize(data)
    assert "unresolved" in out.lower()
    assert "needs more context" in out


def test_handles_agent_failure_marker():
    data = {"agent_status": "failed", "stage": "fix-all"}
    out = sr.summarize(data)
    assert "could not" in out.lower() or "failed" in out.lower()


def test_empty_remediation_is_graceful():
    out = sr.summarize({"remediated": [], "secrets_to_rotate": [], "unresolved": []})
    assert isinstance(out, str)
    assert out.strip()
