#!/usr/bin/env python3
"""Organization-module market research entry for MY Agent (deployed clients).

Host invokes:
  python pipelines/market_research.py research "<brief>" [--output-dir DIR]
  python pipelines/market_research.py feasibility "<brief>" [--output-dir DIR]
  python pipelines/market_research.py plan "<approve text>" [--output-dir DIR]
  python pipelines/market_research.py status

Failure contract (stdout JSON, exit 1): ``status`` is one of
``missing_deps`` / ``missing_api_key`` / ``pipeline_failed`` / ``no_session`` /
``error`` so the host can show *why* it fell back to chat.

Mutable state (session pointer, LangGraph checkpoints, default output) lives
outside the module folder so module updates never overwrite it:
``CQR_MARKET_STATE_DIR`` → ``%LOCALAPPDATA%/MYAgent/organization/market_research``
→ ``~/.myagent/organization/market_research``.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import uuid
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_ROOT = MODULE_ROOT / "market_research" / "cqr_product_pipeline"
MARKET_ROOT = MODULE_ROOT / "market_research"

# (import name, pip package) — checked before the pipeline is imported so a
# bare system Python yields ``missing_deps`` instead of an opaque ImportError.
REQUIRED_MODULES: list[tuple[str, str]] = [
    ("langgraph", "langgraph"),
    ("langchain_core", "langchain"),
    ("langchain_community", "langchain-community"),
    ("langchain_text_splitters", "langchain-text-splitters"),
    ("chromadb", "chromadb"),
    ("pydantic", "pydantic"),
    ("pydantic_settings", "pydantic-settings"),
    ("ddgs", "ddgs"),
]
# feasibility → plan resumes a LangGraph thread via SqliteSaver; research does not.
HITL_MODULES: list[tuple[str, str]] = [
    ("langgraph.checkpoint.sqlite", "langgraph-checkpoint-sqlite"),
]
PROVIDER_MODULES: dict[str, tuple[str, str]] = {
    "openai": ("langchain_openai", "langchain-openai"),
    "ollama": ("langchain_ollama", "langchain-ollama"),
    "anthropic": ("langchain_anthropic", "langchain-anthropic"),
}
PROVIDER_KEYS: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
}


def _bootstrap() -> None:
    root = str(PIPELINE_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    os.environ.setdefault("CQR_MANAGER_ROOT", str(MODULE_ROOT))
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")
    # pydantic-settings reads CHECKPOINT_PATH; keep resumable state out of the module.
    os.environ.setdefault("CHECKPOINT_PATH", str(_state_dir() / ".checkpoints" / "pipeline.db"))


def _state_dir() -> Path:
    env = os.environ.get("CQR_MARKET_STATE_DIR")
    if env:
        base = Path(env)
    elif os.environ.get("LOCALAPPDATA"):
        base = Path(os.environ["LOCALAPPDATA"]) / "MYAgent" / "organization" / "market_research"
    else:
        base = Path.home() / ".myagent" / "organization" / "market_research"
    base.mkdir(parents=True, exist_ok=True)
    return base


def _llm_provider() -> str:
    return (os.environ.get("LLM_PROVIDER") or "ollama").strip().lower()


def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def preflight(phase: str, dry_run: bool) -> dict | None:
    """Return a failure result when the runtime cannot run the pipeline, else None."""
    provider = _llm_provider()
    required = list(REQUIRED_MODULES)
    if phase in {"feasibility", "plan", "status"}:
        required.extend(HITL_MODULES)
    if provider in PROVIDER_MODULES:
        required.append(PROVIDER_MODULES[provider])
    missing = sorted({pkg for mod, pkg in required if not _module_available(mod)})
    base = {"ok": False, "pipeline": "market_research", "phase": phase, "python": sys.executable}
    if missing:
        return {
            **base,
            "status": "missing_deps",
            "missing": missing,
            "error": "시장조사 파이프라인 실행 환경에 필요한 패키지가 없습니다: " + ", ".join(missing),
            "hint": "시장조사 기능(Feature Pack)을 설치하거나 CQR_PIPELINE_PYTHON 을 venv python 으로 지정하세요.",
        }
    key_env = PROVIDER_KEYS.get(provider)
    if key_env and not dry_run and not os.environ.get(key_env, "").strip():
        return {
            **base,
            "status": "missing_api_key",
            "provider": provider,
            "missing": [key_env],
            "error": f"LLM_PROVIDER={provider} 인데 {key_env} 가 설정되지 않았습니다.",
            "hint": "호스트 앱의 LLM 연결 설정을 확인하세요.",
        }
    return None


def _session_file() -> Path:
    return _state_dir() / ".session.json"


def _write_session(meta: dict) -> None:
    _session_file().write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_session() -> dict | None:
    # Legacy location (inside the module) is read once for continuity.
    for path in (_session_file(), MARKET_ROOT / ".session.json"):
        if not path.is_file():
            continue
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
    return None


def _default_output(session_id: str) -> Path:
    return _state_dir() / "output" / session_id


def _finish(result: dict, md: Path) -> dict:
    if result["ok"]:
        result["status"] = "ok"
    else:
        result["status"] = "pipeline_failed"
        result.setdefault("error", f"{md.name} 미생성 (exit {result.get('exit_code')})")
    return result


def _run_module(module: str, argv: list[str]) -> int:
    _bootstrap()
    old = sys.argv
    try:
        sys.argv = [module, *argv]
        if module.endswith("run_research"):
            from cqr_product_pipeline.cli.run_research import main
        else:
            from cqr_product_pipeline.cli.run_pipeline import main
        main()
        return 0
    except SystemExit as exc:
        code = exc.code
        return int(code) if isinstance(code, int) else (0 if code is None else 1)
    finally:
        sys.argv = old


def cmd_research(brief: str, output_dir: Path | None, dry_run: bool) -> dict:
    session_id = uuid.uuid4().hex[:8]
    out = output_dir or _default_output(session_id)
    out.mkdir(parents=True, exist_ok=True)
    argv = [
        "--brief",
        brief,
        "--session-id",
        session_id,
        "--output-dir",
        str(out),
    ]
    if dry_run:
        argv.append("--dry-run")
    code = _run_module("cqr_product_pipeline.cli.run_research", argv)
    md = out / "research_report.md"
    _write_session(
        {
            "session_id": session_id,
            "brief": brief,
            "mode": "research",
            "output_dir": str(out.resolve()),
            "thread_id": session_id,
        }
    )
    return _finish({
        "ok": code == 0 and md.is_file(),
        "pipeline": "market_research",
        "phase": "research",
        "session_id": session_id,
        "output_dir": str(out.resolve()),
        "markdown_path": str(md.resolve()) if md.is_file() else None,
        "exit_code": code,
    }, md)


def cmd_feasibility(brief: str, output_dir: Path | None, dry_run: bool) -> dict:
    session_id = uuid.uuid4().hex[:8]
    out = output_dir or _default_output(session_id)
    out.mkdir(parents=True, exist_ok=True)
    argv = [
        "--brief",
        brief,
        "--thread-id",
        session_id,
        "--output-dir",
        str(out),
    ]
    if dry_run:
        argv.append("--dry-run")
    code = _run_module("cqr_product_pipeline.cli.run_pipeline", argv)
    md = out / "feasibility_review.md"
    _write_session(
        {
            "session_id": session_id,
            "brief": brief,
            "mode": "pipeline",
            "output_dir": str(out.resolve()),
            "thread_id": session_id,
        }
    )
    return _finish({
        "ok": code == 0 and md.is_file(),
        "pipeline": "market_research",
        "phase": "feasibility",
        "session_id": session_id,
        "output_dir": str(out.resolve()),
        "markdown_path": str(md.resolve()) if md.is_file() else None,
        "hitl": True,
        "exit_code": code,
    }, md)


def cmd_plan(approve_text: str, output_dir: Path | None, dry_run: bool) -> dict:
    meta = _read_session()
    if not meta:
        return {
            "ok": False,
            "pipeline": "market_research",
            "phase": "plan",
            "status": "no_session",
            "error": "활성 세션이 없습니다. 먼저 /타당성 을 실행하세요.",
        }
    session_id = str(meta.get("thread_id") or meta.get("session_id"))
    out = Path(str(output_dir or meta.get("output_dir") or _default_output(session_id)))
    out.mkdir(parents=True, exist_ok=True)
    argv = [
        "--resume",
        "--approve-text",
        approve_text,
        "--thread-id",
        session_id,
        "--output-dir",
        str(out),
    ]
    if dry_run:
        argv.append("--dry-run")
    code = _run_module("cqr_product_pipeline.cli.run_pipeline", argv)
    md = out / "final_product_plan.md"
    return _finish({
        "ok": code == 0 and md.is_file(),
        "pipeline": "market_research",
        "phase": "plan",
        "session_id": session_id,
        "output_dir": str(out.resolve()),
        "markdown_path": str(md.resolve()) if md.is_file() else None,
        "exit_code": code,
    }, md)


def main() -> int:
    parser = argparse.ArgumentParser(description="CQR market research pipeline entry")
    parser.add_argument("phase", choices=["research", "feasibility", "plan", "status"])
    parser.add_argument("brief", nargs="?", default="")
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json-only", action="store_true")
    args = parser.parse_args()

    try:
        if args.phase == "status":
            result: dict = {"ok": True, "pipeline": "market_research", "phase": "status", "status": "ok"}
            meta = _read_session()
            if meta:
                result.update(meta)
            failure = preflight("status", dry_run=True)
            result["runtime"] = failure["status"] if failure else "ready"
            if failure:
                result["missing"] = failure["missing"]
        elif (failure := preflight(args.phase, args.dry_run)) is not None:
            result = failure
        elif args.phase == "research":
            if not args.brief.strip():
                raise SystemExit("brief required")
            result = cmd_research(args.brief, args.output_dir, args.dry_run)
        elif args.phase == "feasibility":
            if not args.brief.strip():
                raise SystemExit("brief required")
            result = cmd_feasibility(args.brief, args.output_dir, args.dry_run)
        else:
            result = cmd_plan(args.brief or "승인", args.output_dir, args.dry_run)
    except Exception as exc:  # noqa: BLE001
        result = {
            "ok": False,
            "pipeline": "market_research",
            "phase": args.phase,
            "status": "error",
            "error": f"{type(exc).__name__}: {exc}",
        }
        print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
        return 1

    # Never print full Korean markdown to cp949 consoles — host reads the file.
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    if result.get("markdown_path"):
        print(f"MD={result['markdown_path']}", flush=True)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
