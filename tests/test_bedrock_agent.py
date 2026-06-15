"""Unit tests for scripts/agents/bedrock-agent.py — the Bedrock AGENT_CMD adapter.

These avoid any real AWS call: boto3 is stubbed via sys.modules so the adapter's
request/response shaping is verified offline.
"""
import importlib.util
import io
import sys
import types
from pathlib import Path

_MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "agents" / "bedrock-agent.py"


def _load():
    spec = importlib.util.spec_from_file_location("bedrock_agent", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_help_exits_zero(capsys):
    mod = _load()
    assert mod.main(["--help"]) == 0


def test_empty_stdin_returns_error(monkeypatch):
    mod = _load()
    monkeypatch.setattr(sys, "stdin", io.StringIO("   \n"))
    assert mod.main([]) == 2


def test_run_shapes_converse_request_and_extracts_text(monkeypatch):
    mod = _load()
    captured = {}

    class FakeClient:
        def converse(self, **kwargs):
            captured.update(kwargs)
            return {"output": {"message": {"content": [
                {"text": "[{\"id\": \"x\"}]"}]}}}

    fake_boto3 = types.SimpleNamespace(client=lambda *a, **k: FakeClient())
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)

    out = mod.run("hello prompt", model_id="m1", region="us-east-1", max_tokens=128)
    assert out == "[{\"id\": \"x\"}]"
    assert captured["modelId"] == "m1"
    assert captured["messages"][0]["role"] == "user"
    assert captured["messages"][0]["content"][0]["text"] == "hello prompt"
    assert captured["inferenceConfig"]["maxTokens"] == 128


def test_main_writes_model_text_to_stdout(monkeypatch, capsys):
    mod = _load()
    monkeypatch.setattr(sys, "stdin", io.StringIO("prompt body"))

    class FakeClient:
        def converse(self, **kwargs):
            return {"output": {"message": {"content": [{"text": "RESULT"}]}}}

    monkeypatch.setitem(sys.modules, "boto3",
                        types.SimpleNamespace(client=lambda *a, **k: FakeClient()))
    rc = mod.main([])
    assert rc == 0
    assert "RESULT" in capsys.readouterr().out


def test_main_returns_1_on_bedrock_failure(monkeypatch):
    mod = _load()
    monkeypatch.setattr(sys, "stdin", io.StringIO("prompt body"))

    def boom(*a, **k):
        raise RuntimeError("no credentials")

    monkeypatch.setitem(sys.modules, "boto3", types.SimpleNamespace(client=boom))
    assert mod.main([]) == 1
