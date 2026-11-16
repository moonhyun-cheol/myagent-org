#!/usr/bin/env python3
"""Organization-module market research entry for MY Agent (deployed clients).

Host invokes:
  python pipelines/market_research.py research "<brief>" [--output-dir DIR]
  python pipelines/market_research.py feasibility "<brief>" [--output-dir DIR]
  python pipelines/market_research.py plan "<approve text>" [--output-dir DIR]
  python pipelines/market_research.py status

``research`` builds an evidence pack. The brief is read as fields (inline
``품목: … / 시즌: … / 경쟁사: … / 가격: …`` or ``--product`` style flags; the
sentence is only a fallback), the web is searched with those values, page
bodies are fetched and only on-topic excerpts are kept. No LLM runs and nothing
is filled from templates. The target market is the United States: queries are
English and non-US sources are dropped (the search engine takes no region).

Failure contract (stdout JSON, exit 1): ``status`` is one of
``missing_deps`` / ``missing_api_key`` / ``pipeline_failed`` / ``no_session`` /
``needs_brief`` / ``insufficient_evidence`` / ``unavailable`` / ``error``.
The host shows ``error`` verbatim, so it carries the user-facing guidance.

- ``needs_brief``: no product or category could be read (e.g. a follow-up like
  「리포트 형식으로 줘」), or it has no English name to search the US market
  with (``reason: no_english_name``). No search runs, no output folder is
  created and the previous session is kept.
- ``insufficient_evidence``: fewer than the minimum on-topic sources were
  found. No report is written and the previous session is kept.
- ``unavailable``: ``feasibility`` / ``plan`` stay closed while the internal
  corpus (RAG collections) is not wired; they cannot score without it.

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
# Must match cqr_product_pipeline.cli.run_research exit codes.
NEEDS_BRIEF_EXIT = 3
INSUFFICIENT_EVIDENCE_EXIT = 4
# Must match cqr_product_pipeline.agents.evidence_pack.FIELD_KEYS.
FIELD_FLAGS = (
    "product",
    "product_en",
    "category",
    "season",
    "channel",
    "price_band",
    "competitors",
    "focus",
)
FIELD_EXAMPLE = (
    "/심층리서치 품목: 스키바지 / 영문명: ski pants / 시즌: 2027 FW / 경쟁사: Burton, Patagonia / 가격: $90-280"
)
# brief_gate reason -> user-facing guidance (the host shows ``error`` verbatim).
NEEDS_BRIEF_ERRORS = {
    "no_english_name": (
        "미국 시장을 검색할 영문 품목명을 찾지 못해 검색하지 않았습니다. "
        "`영문명:` 필드를 붙여 다시 요청하세요."
    ),
}
NEEDS_BRIEF_DEFAULT_ERROR = "조사할 품목이나 카테고리를 찾지 못해 검색하지 않았습니다. 필드로 다시 요청하세요."
PHASE_CLOSED_ERROR = (
    "타당성·기획서 단계는 지금 사용할 수 없습니다. 내부 자료(제품·원가·브랜드 인덱스)가 "
    "파이프라인에 연결되지 않아 점수와 판정을 낼 근거가 없습니다. "
    "/심층리서치 근거 팩까지만 제공합니다."
)

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
    # ``research`` collects evidence only: it needs no LLM provider or API key.
    uses_llm = phase != "research"
    if phase in {"feasibility", "plan", "status"}:
        required.extend(HITL_MODULES)
    if uses_llm and provider in PROVIDER_MODULES:
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
    if uses_llm and key_env and not dry_run and not os.environ.get(key_env, "").strip():
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


def _internal_corpus_ready() -> bool:
    """feasibility / plan score against internal documents; none are wired today."""
    _bootstrap()
    try:
        from cqr_product_pipeline.rag.collections import COLLECTIONS
    except Exception:  # noqa: BLE001 - missing RAG stack also means "not ready"
        return False
    return len(COLLECTIONS) > 0


def _phase_closed_result(phase: str) -> dict:
    return {
        "ok": False,
        "pipeline": "market_research",
        "phase": phase,
        "status": "unavailable",
        "error": PHASE_CLOSED_ERROR,
    }


def _research_brief(brief: str, fields: dict[str, str]):
    """Parsed brief plus the reason it cannot be researched (None when it can)."""
    _bootstrap()
    from cqr_product_pipeline.agents.evidence_pack import brief_gate, parse_brief

    parsed = parse_brief(brief, fields)
    return parsed, brief_gate(parsed)


def _brief_gate(brief: str) -> str | None:
    """Legacy sentence gate used by ``feasibility`` (same deep-research first step)."""
    _bootstrap()
    from cqr_product_pipeline.agents.deep_research import (
        _parse_brief_hints,
        brief_needs_clarification,
    )

    return brief_needs_clarification(_parse_brief_hints(brief, None))


def _needs_brief_result(phase: str, brief: str, previous: dict | None, reason: str | None = None) -> dict:
    """Failure result that keeps the previous session pointer untouched."""
    result: dict = {
        "ok": False,
        "pipeline": "market_research",
        "phase": phase,
        "status": "needs_brief",
        "reason": reason,
        "brief": brief,
        "error": f"{NEEDS_BRIEF_ERRORS.get(reason or '', NEEDS_BRIEF_DEFAULT_ERROR)} 예: {FIELD_EXAMPLE}",
        "exit_code": NEEDS_BRIEF_EXIT,
    }
    if previous:
        prev_dir = Path(str(previous.get("output_dir") or ""))
        prev_md = prev_dir / "research_report.md"
        result["previous_session"] = {
            "session_id": previous.get("session_id"),
            "brief": previous.get("brief"),
            "markdown_path": str(prev_md) if prev_md.is_file() else None,
        }
        if prev_md.is_file():
            result["error"] += f" 직전 리포트는 그대로 있습니다: {prev_md}"
    return result


def _insufficient_result(brief: str, out: Path, session_id: str) -> dict:
    """Too few on-topic sources: no report, previous session kept."""
    _bootstrap()
    from cqr_product_pipeline.agents.evidence_pack import MIN_EVIDENCE

    stats: dict = {}
    try:
        stats = json.loads((out / "evidence_pack.json").read_text(encoding="utf-8")).get("stats") or {}
    except Exception:  # noqa: BLE001 - stats are optional detail
        pass
    return {
        "ok": False,
        "pipeline": "market_research",
        "phase": "research",
        "status": "insufficient_evidence",
        "brief": brief,
        "session_id": session_id,
        "output_dir": str(out.resolve()),
        "stats": stats,
        "error": (
            f"브리프 주제에 맞는 미국 시장 근거가 {stats.get('evidence', 0)}건뿐이라 리포트를 만들지 않았습니다"
            f"(최소 {MIN_EVIDENCE}건). 검색 {stats.get('queries', 0)}회, 결과 {stats.get('results', 0)}건, "
            f"미국 외 출처라 제외 {stats.get('off_market_dropped', 0)}건, "
            f"주제와 무관해 제외 {stats.get('off_topic_dropped', 0)}건. "
            f"영문명을 미국에서 쓰는 품목명으로 바꾸거나 경쟁사를 필드로 지정해 다시 요청하세요. 예: {FIELD_EXAMPLE}"
        ),
        "exit_code": INSUFFICIENT_EVIDENCE_EXIT,
    }


def cmd_research(
    brief: str,
    output_dir: Path | None,
    dry_run: bool,
    fields: dict[str, str] | None = None,
) -> dict:
    fields = fields or {}
    # Gate before creating any output folder or printing child output, so a
    # follow-up message leaves no empty session dir and stdout stays one JSON.
    parsed, reason = _research_brief(brief, fields)
    if reason:
        return _needs_brief_result("research", brief, _read_session(), reason)
    session_id = uuid.uuid4().hex[:8]
    out = output_dir or _default_output(session_id)
    out.mkdir(parents=True, exist_ok=True)
    # ``--name=value`` keeps values that start with ``-`` or ``$`` intact.
    argv = [f"--brief={brief}", f"--session-id={session_id}", f"--output-dir={out}"]
    argv += [f"--{name.replace('_', '-')}={value}" for name, value in fields.items()]
    if dry_run:
        argv.append("--dry-run")
    previous = _read_session()
    code = _run_module("cqr_product_pipeline.cli.run_research", argv)
    md = out / "research_report.md"
    if code == NEEDS_BRIEF_EXIT:
        # Backstop: the CLI applies the same gate. Keep the previous session.
        return _needs_brief_result("research", brief, previous)
    if code == INSUFFICIENT_EVIDENCE_EXIT:
        return _insufficient_result(brief, out, session_id)
    if md.is_file():
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
        "report_kind": "evidence_pack",
        "session_id": session_id,
        "output_dir": str(out.resolve()),
        "markdown_path": str(md.resolve()) if md.is_file() else None,
        "brief_fields": {
            "product": parsed.product,
            "product_en": parsed.product_en,
            "category": parsed.category,
            "season": parsed.season,
            "channel": parsed.channel,
            "price_band": parsed.price_band,
            "competitors": parsed.competitors,
            "focus": parsed.focus,
        },
        "exit_code": code,
    }, md)


def cmd_feasibility(brief: str, output_dir: Path | None, dry_run: bool) -> dict:
    # /타당성 starts with the same deep research step, so the same gate applies.
    if _brief_gate(brief):
        return _needs_brief_result("feasibility", brief, _read_session())
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
    for name in FIELD_FLAGS:
        parser.add_argument("--" + name.replace("_", "-"), type=str, default=None)
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
            result["phases"] = {
                "research": "evidence_pack",
                "feasibility": "ready" if _internal_corpus_ready() else "unavailable",
                "plan": "ready" if _internal_corpus_ready() else "unavailable",
            }
        elif args.phase in {"feasibility", "plan"} and not _internal_corpus_ready():
            result = _phase_closed_result(args.phase)
        elif (failure := preflight(args.phase, args.dry_run)) is not None:
            result = failure
        elif args.phase == "research":
            fields = {name: getattr(args, name) for name in FIELD_FLAGS if getattr(args, name)}
            if not args.brief.strip() and not fields:
                raise SystemExit("brief required")
            result = cmd_research(args.brief, args.output_dir, args.dry_run, fields)
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
