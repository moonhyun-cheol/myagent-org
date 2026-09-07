#!/usr/bin/env python3
"""Organization-module market research entry for MY Agent (deployed clients).

Host invokes:
  python pipelines/market_research.py research "<brief>" [--output-dir DIR]
  python pipelines/market_research.py feasibility "<brief>" [--output-dir DIR]
  python pipelines/market_research.py plan "<approve text>" [--output-dir DIR]
  python pipelines/market_research.py status
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_ROOT = MODULE_ROOT / "market_research" / "cqr_product_pipeline"
MARKET_ROOT = MODULE_ROOT / "market_research"


def _bootstrap() -> None:
    root = str(PIPELINE_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    os.environ.setdefault("CQR_MANAGER_ROOT", str(MODULE_ROOT))
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")


def _session_file() -> Path:
    return MARKET_ROOT / ".session.json"


def _write_session(meta: dict) -> None:
    MARKET_ROOT.mkdir(parents=True, exist_ok=True)
    _session_file().write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_session() -> dict | None:
    path = _session_file()
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


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
    out = output_dir or (MARKET_ROOT / "output" / session_id)
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
    return {
        "ok": code == 0 and md.is_file(),
        "pipeline": "market_research",
        "phase": "research",
        "session_id": session_id,
        "output_dir": str(out.resolve()),
        "markdown_path": str(md.resolve()) if md.is_file() else None,
        "exit_code": code,
    }


def cmd_feasibility(brief: str, output_dir: Path | None, dry_run: bool) -> dict:
    session_id = uuid.uuid4().hex[:8]
    out = output_dir or (MARKET_ROOT / "output" / session_id)
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
    return {
        "ok": code == 0 and md.is_file(),
        "pipeline": "market_research",
        "phase": "feasibility",
        "session_id": session_id,
        "output_dir": str(out.resolve()),
        "markdown_path": str(md.resolve()) if md.is_file() else None,
        "hitl": True,
        "exit_code": code,
    }


def cmd_plan(approve_text: str, output_dir: Path | None, dry_run: bool) -> dict:
    meta = _read_session()
    if not meta:
        return {
            "ok": False,
            "pipeline": "market_research",
            "phase": "plan",
            "error": "활성 세션이 없습니다. 먼저 /타당성 을 실행하세요.",
        }
    session_id = str(meta.get("thread_id") or meta.get("session_id"))
    out = Path(str(output_dir or meta.get("output_dir") or (MARKET_ROOT / "output" / session_id)))
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
    return {
        "ok": code == 0 and md.is_file(),
        "pipeline": "market_research",
        "phase": "plan",
        "session_id": session_id,
        "output_dir": str(out.resolve()),
        "markdown_path": str(md.resolve()) if md.is_file() else None,
        "exit_code": code,
        "error": None if md.is_file() else "final_product_plan.md 미생성",
    }


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
            result: dict = {"ok": True, "pipeline": "market_research", "phase": "status"}
            meta = _read_session()
            if meta:
                result.update(meta)
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
