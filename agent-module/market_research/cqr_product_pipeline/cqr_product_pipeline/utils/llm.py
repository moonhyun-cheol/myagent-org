"""LLM structured output helpers."""

from __future__ import annotations

import json
import logging
import os
from typing import TypeVar

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


def stream_text(llm: BaseChatModel, messages: list) -> str:
    """Collect a completion via streaming.

    A long single-shot generation exceeds the OWUI/proxy response timeout (~120s) and
    comes back as an HTML 5xx page, surfaced as InternalServerError. Streaming keeps
    tokens flowing so the connection stays alive.
    """
    parts: list[str] = []
    for chunk in llm.stream(messages):
        content = getattr(chunk, "content", "")
        parts.append(content if isinstance(content, str) else str(content))
    return "".join(parts)


def _schema_hint(schema: type[T]) -> str:
    try:
        return json.dumps(schema.model_json_schema(), ensure_ascii=False)
    except Exception:  # noqa: BLE001 - hint is best effort
        return schema.__name__


def _json_messages(system: str, user: str, schema: type[T]) -> list:
    return [
        SystemMessage(content=system),
        HumanMessage(
            content=(
                f"{user}\n\n"
                f"Return a single JSON object matching this JSON Schema "
                f"(exact field names, no extra keys):\n{_schema_hint(schema)}\n\n"
                "Output JSON only. No prose, no markdown fences."
            )
        ),
    ]


def _streamed_json(llm: BaseChatModel, system: str, user: str, schema: type[T], repair_attempts: int) -> T:
    text = stream_text(llm, _json_messages(system, user, schema))
    for attempt in range(repair_attempts + 1):
        try:
            return schema.model_validate_json(_extract_json(text))
        except (ValidationError, json.JSONDecodeError) as parse_exc:
            if attempt >= repair_attempts:
                raise
            text = stream_text(
                llm,
                [
                    SystemMessage(content="Return valid JSON only. No markdown fences."),
                    HumanMessage(
                        content=(
                            f"Fix this JSON for schema {schema.__name__}:\n{text}\n\n"
                            f"Error: {parse_exc}"
                        )
                    ),
                ],
            )
    raise RuntimeError("unreachable")


def invoke_structured(
    llm: BaseChatModel,
    system: str,
    user: str,
    schema: type[T],
    *,
    repair_attempts: int = 1,
) -> T:
    """Get schema-valid output, preferring streaming so gateways do not time out.

    `with_structured_output` streaming is unusable on the OWUI gateway (chunks carry
    no `role`), and its non-streaming form hits the proxy timeout on long reports —
    so streamed JSON is the primary path and structured output the fallback.
    """
    if os.getenv("CQR_LLM_STREAM_JSON", "1") != "0":
        try:
            return _streamed_json(llm, system, user, schema, repair_attempts)
        except Exception as exc:  # noqa: BLE001 - fall through to structured output
            logger.warning("streamed JSON failed (%s), trying structured output", exc)

    structured = llm.with_structured_output(schema)
    result = structured.invoke([SystemMessage(content=system), HumanMessage(content=user)])
    if isinstance(result, schema):
        return result
    return schema.model_validate(result)


def _extract_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text
