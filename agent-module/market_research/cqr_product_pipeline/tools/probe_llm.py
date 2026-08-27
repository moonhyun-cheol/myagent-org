"""Probe the configured chat model end-to-end (params, structured output, payload size).

Run via CQR_PA: node tools/probe-pipeline-llm.mjs
Reads OPENAI_API_KEY / OPENAI_BASE_URL / LLM_MODEL from env.
"""

from __future__ import annotations

import os

from langchain_core.messages import HumanMessage, SystemMessage


def _report(name: str, fn) -> None:
    try:
        out = fn()
        text = out if isinstance(out, str) else str(out)
        print(f"{name} -> OK {text[:120]!r}")
    except Exception as exc:  # noqa: BLE001 - probe reports every failure shape
        print(f"{name} -> FAIL {type(exc).__name__}: {str(exc)[:400]}")


def main() -> None:
    from langchain_openai import ChatOpenAI

    model = os.getenv("LLM_MODEL", "")
    base_url = (os.getenv("OPENAI_BASE_URL") or "").rstrip("/")
    print(f"model={model}")
    print(f"base_url={base_url}")

    common = {"model": model, "base_url": base_url, "timeout": 120.0, "max_retries": 0}

    llm = ChatOpenAI(**common)
    _report("1 chat.completions   ", lambda: llm.invoke("Reply with the single word OK.").content)

    llm_resp = ChatOpenAI(**common, use_responses_api=True)
    _report("2 responses API      ", lambda: llm_resp.invoke("Reply with OK.").content)

    from pydantic import BaseModel

    class Tiny(BaseModel):
        a: int

    _report("3 structured (default)", lambda: llm.with_structured_output(Tiny).invoke("Return a=1"))
    _report(
        "4 structured json_mode",
        lambda: llm.with_structured_output(Tiny, method="json_mode").invoke(
            'Return only JSON: {"a": 1}'
        ),
    )

    filler = "ski pants waterproof venting review snippet. " * 2000  # ~90KB
    _report(
        "5 large payload      ",
        lambda: llm.invoke(
            [
                SystemMessage(content="Summarize in one short Korean sentence."),
                HumanMessage(content=filler),
            ]
        ).content,
    )


if __name__ == "__main__":
    main()
