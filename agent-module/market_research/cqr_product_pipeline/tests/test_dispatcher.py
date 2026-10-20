"""Contract tests for the organization-module entry pipelines/market_research.py."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ENTRY = Path(__file__).resolve().parents[3] / "pipelines" / "market_research.py"


def _load():
    spec = importlib.util.spec_from_file_location("mr_entry", ENTRY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run(args, env_extra, tmp_path):
    import os

    env = {k: v for k, v in os.environ.items() if k not in {"OPENAI_API_KEY", "CHECKPOINT_PATH"}}
    env.update(
        {
            "CQR_MARKET_STATE_DIR": str(tmp_path / "state"),
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
            **env_extra,
        }
    )
    proc = subprocess.run(
        [sys.executable, str(ENTRY), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=300,
    )
    # The pipeline may log to stdout first; the entry's result is the last top-level object.
    out = proc.stdout.replace("\r\n", "\n").split("\nMD=")[0]
    start = 0 if out.startswith("{") else out.rfind("\n{\n") + 1
    assert start >= 0 and out[start:].startswith("{"), proc.stdout[-2000:] + proc.stderr[-2000:]
    return proc.returncode, json.loads(out[start:])


def test_missing_deps_is_reported(monkeypatch, tmp_path):
    mod = _load()
    monkeypatch.setenv("CQR_MARKET_STATE_DIR", str(tmp_path))
    monkeypatch.setattr(mod, "REQUIRED_MODULES", [("cqr_no_such_module_xyz", "cqr-fake")])
    result = mod.preflight("research", dry_run=False)
    assert result["status"] == "missing_deps"
    assert result["missing"] == ["cqr-fake"]


def test_missing_api_key_is_reported(tmp_path):
    code, result = _run(["research", "summer cargo pants"], {"LLM_PROVIDER": "openai"}, tmp_path)
    assert code == 1
    assert result["status"] == "missing_api_key"
    assert result["missing"] == ["OPENAI_API_KEY"]


def test_dry_run_writes_report_and_state_outside_module(tmp_path):
    code, result = _run(
        ["research", "summer cargo pants Amazon review pain", "--dry-run"],
        {"LLM_PROVIDER": "openai"},
        tmp_path,
    )
    assert code == 0, result
    assert result["status"] == "ok"
    md = Path(result["markdown_path"])
    assert md.name == "research_report.md" and md.is_file()
    state = tmp_path / "state"
    assert (state / ".session.json").is_file()
    assert Path(result["output_dir"]).is_relative_to(state)
