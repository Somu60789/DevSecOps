"""Unit tests for scripts/check-coverage.py — coverage threshold enforcement."""
import importlib.util
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check-coverage.py"
_spec = importlib.util.spec_from_file_location("check_coverage", _MODULE_PATH)
cc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cc)

# Cobertura-style XML (produced by coverage.py, jacoco->cobertura, nyc, gocover-cobertura).
COBERTURA = """<?xml version="1.0" ?>
<coverage line-rate="0.8734" branch-rate="0.5" version="1.9">
  <packages/>
</coverage>
"""

# JaCoCo XML (Gradle/Java default).
JACOCO = """<?xml version="1.0"?>
<report name="app">
  <counter type="INSTRUCTION" missed="120" covered="880"/>
  <counter type="LINE" missed="10" covered="90"/>
</report>
"""


def test_parse_cobertura_line_rate(tmp_path):
    p = tmp_path / "coverage.xml"
    p.write_text(COBERTURA)
    assert round(cc.parse_coverage(str(p)), 2) == 87.34


def test_parse_jacoco_line_counter(tmp_path):
    p = tmp_path / "jacoco.xml"
    p.write_text(JACOCO)
    # LINE: 90 covered / 100 total = 90.0
    assert cc.parse_coverage(str(p)) == 90.0


def test_meets_threshold_true_and_false():
    assert cc.meets_threshold(87.3, 80.0) is True
    assert cc.meets_threshold(79.9, 80.0) is False
    assert cc.meets_threshold(80.0, 80.0) is True  # equal passes


def test_main_passes_when_above_threshold(tmp_path, capsys):
    p = tmp_path / "coverage.xml"
    p.write_text(COBERTURA)
    rc = cc.main(["--file", str(p), "--min", "80"])
    assert rc == 0
    assert "87.34" in capsys.readouterr().out


def test_main_fails_when_below_threshold(tmp_path):
    p = tmp_path / "coverage.xml"
    p.write_text(COBERTURA)
    assert cc.main(["--file", str(p), "--min", "95"]) == 1


def test_main_missing_file_is_nonfatal_when_min_zero(tmp_path):
    missing = str(tmp_path / "nope.xml")
    assert cc.main(["--file", missing, "--min", "0"]) == 0


def test_main_missing_file_fails_when_threshold_set(tmp_path):
    missing = str(tmp_path / "nope.xml")
    assert cc.main(["--file", missing, "--min", "80"]) == 1
