"""Unit tests for scripts/gen-docs.py — stack detection and doc generation."""
import importlib.util
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "gen-docs.py"
_spec = importlib.util.spec_from_file_location("gen_docs", _MODULE_PATH)
gd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gd)


def test_detect_python_and_node(tmp_path):
    (tmp_path / "package.json").write_text("{}")
    (tmp_path / "requirements.txt").write_text("pytest")
    stacks = gd.detect_stack(tmp_path)
    assert "node" in stacks
    assert "python" in stacks


def test_detect_none_for_notes_only_repo(tmp_path):
    (tmp_path / "notes.txt").write_text("just notes")
    assert gd.detect_stack(tmp_path) == set()


def test_generate_writes_full_doc_set(tmp_path):
    out = tmp_path / "docs"
    _, changed = gd.generate(tmp_path, out, check=False)
    for name in ("README.md", "architecture.md", "api.md", "operations.md",
                 "contributing.md", "CHANGELOG.md"):
        assert (out / name).exists()
        assert (out / name).read_text().startswith(gd.BANNER)
    assert "README.md" in changed


def test_notes_only_repo_produces_notes_architecture(tmp_path):
    (tmp_path / "Rajiv.txt").write_text("Lidar\nSensor fusion\nPerception ai")
    out = tmp_path / "docs"
    stacks, _ = gd.generate(tmp_path, out, check=False)
    assert stacks == set()
    arch = (out / "architecture.md").read_text()
    assert "No source stack detected" in arch
    assert "Sensor fusion" in arch


def test_check_mode_reports_out_of_date_without_writing(tmp_path):
    out = tmp_path / "docs"
    _, changed = gd.generate(tmp_path, out, check=True)
    assert changed                      # nothing exists yet -> all out of date
    assert not out.exists()             # check mode wrote nothing


def test_idempotent_second_run_has_no_changes(tmp_path):
    out = tmp_path / "docs"
    gd.generate(tmp_path, out, check=False)
    _, changed = gd.generate(tmp_path, out, check=False)
    assert changed == []
