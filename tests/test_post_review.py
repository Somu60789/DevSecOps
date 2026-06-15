"""Unit tests for scripts/post-review.py — combined-comment assembly + idempotency."""
import importlib.util
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "post-review.py"
_spec = importlib.util.spec_from_file_location("post_review", _MODULE_PATH)
pr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pr)


def _findings(*items):
    by_sev, by_cat = {}, {}
    for f in items:
        by_sev[f["severity"]] = by_sev.get(f["severity"], 0) + 1
        by_cat[f["category"]] = by_cat.get(f["category"], 0) + 1
    return {"schema_version": "1", "findings": list(items),
            "summary": {"by_severity": by_sev, "by_category": by_cat, "scanner_errors": []}}


def test_clean_repo_all_sections_pass():
    body = pr.build_comment("abc1234", _findings(), verdicts=[], optimize={"suggestions": []})
    assert "## Bot Review: abc1234" in body
    for section in ("Documentation", "Security", "Code Quality", "Test Coverage", "Clean Code"):
        assert f"### {section}" in body
    assert body.count("✅ Pass") >= 5
    assert "**Overall:** ✅ Pass" in body


def test_security_finding_appears_and_counts_failure():
    f = {"id": "1", "tool": "gitleaks", "category": "secret", "severity": "critical",
         "file": "conf.py", "line": 3, "rule_id": "aws-key", "message": "AWS key found"}
    body = pr.build_comment("abc1234", _findings(f), verdicts=[], optimize={"suggestions": []})
    assert "AWS key found" in body
    assert "conf.py" in body
    assert "❌ Failures: 1" in body


def test_clean_code_finding_routed_to_clean_code_section():
    f = {"id": "2", "tool": "lizard", "category": "complexity", "severity": "medium",
         "file": "big.py", "line": 10, "rule_id": "ccn", "message": "cyclomatic complexity 14 > 10"}
    body = pr.build_comment("abc1234", _findings(f), verdicts=[], optimize={"suggestions": []})
    clean_section = body.split("### Clean Code")[1].split("---")[0]
    assert "complexity 14" in clean_section
    assert "⚠️ Warnings: 1" in body


def test_optimize_suggestions_appear_in_code_quality():
    opt = {"suggestions": [
        {"file": "a.py", "line": 5, "risk": "safe-to-show", "title": "use a set",
         "rationale": "O(1) membership", "before": "x in list", "after": "x in set"}]}
    body = pr.build_comment("abc1234", _findings(), verdicts=[], optimize=opt)
    cq = body.split("### Code Quality")[1].split("### Test Coverage")[0]
    assert "use a set" in cq


def test_marker_present_for_idempotent_upsert():
    body = pr.build_comment("abc1234", _findings(), verdicts=[], optimize={"suggestions": []})
    assert pr.comment_marker("abc1234") in body


def test_find_existing_comment_by_marker():
    marker = pr.comment_marker("abc1234")
    comments = [
        {"id": 1, "body": "a human comment"},
        {"id": 2, "body": f"{marker}\n## Bot Review: abc1234"},
    ]
    assert pr.find_marked_comment(comments, marker)["id"] == 2
    assert pr.find_marked_comment(comments, pr.comment_marker("zzz9999")) is None


def test_degraded_comment_notes_skipped_triage():
    body = pr.build_comment("abc1234", _findings(), verdicts=None, optimize=None)
    assert "triage was skipped" in body.lower()


def test_summary_table_has_all_categories():
    table = pr.build_summary_table({"Documentation": "✅", "Security": "❌",
                                    "Code Quality": "✅", "Test Coverage": "✅",
                                    "Clean Code": "⚠️"})
    assert pr.SUMMARY_MARKER in table
    for cat in ("Documentation", "Security", "Code Quality", "Test Coverage", "Clean Code"):
        assert cat in table
