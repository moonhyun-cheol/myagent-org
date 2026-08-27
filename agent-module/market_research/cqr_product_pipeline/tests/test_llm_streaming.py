"""invoke_structured must stream first (gateway times out on long single-shot calls)."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from cqr_product_pipeline.utils.llm import invoke_structured


class Tiny(BaseModel):
    a: int


class _Chunk:
    def __init__(self, content: str) -> None:
        self.content = content


class _StreamingStub:
    def __init__(self, parts: list[str]) -> None:
        self.parts = parts
        self.structured_calls = 0

    def stream(self, _messages):
        for part in self.parts:
            yield _Chunk(part)

    def with_structured_output(self, _schema):
        self.structured_calls += 1
        raise AssertionError("structured output must not be used when streaming works")


class _BrokenStreamStub:
    def __init__(self, result: Tiny) -> None:
        self.result = result

    def stream(self, _messages):
        raise RuntimeError("stream unsupported")
        yield  # pragma: no cover - generator marker

    def with_structured_output(self, _schema):
        outer = self

        class _Structured:
            def invoke(self, _messages):
                return outer.result

        return _Structured()


def test_streamed_json_is_the_primary_path():
    stub = _StreamingStub(['{"a"', ": 4", "2}"])
    assert invoke_structured(stub, "sys", "user", Tiny) == Tiny(a=42)
    assert stub.structured_calls == 0


def test_schema_is_included_in_the_prompt():
    captured: list = []

    class _Capture(_StreamingStub):
        def stream(self, messages):
            captured.append(messages)
            return super().stream(messages)

    invoke_structured(_Capture(['{"a": 1}']), "sys", "user", Tiny)
    prompt = captured[0][-1].content
    assert '"properties"' in prompt and '"a"' in prompt
    assert "JSON only" in prompt


def test_falls_back_to_structured_output_when_streaming_fails():
    stub = _BrokenStreamStub(Tiny(a=7))
    assert invoke_structured(stub, "sys", "user", Tiny) == Tiny(a=7)


def test_repair_attempt_runs_on_invalid_json():
    class _RepairStub(_StreamingStub):
        def __init__(self) -> None:
            super().__init__([])
            self.calls = 0

        def stream(self, _messages):
            self.calls += 1
            text = "not json" if self.calls == 1 else '{"a": 5}'
            yield _Chunk(text)

    stub = _RepairStub()
    assert invoke_structured(stub, "sys", "user", Tiny) == Tiny(a=5)
    assert stub.calls == 2


def test_raises_when_repair_and_structured_both_fail():
    class _FailStub(_StreamingStub):
        def stream(self, _messages):
            yield _Chunk("still not json")

        def with_structured_output(self, _schema):
            class _Structured:
                def invoke(self, _messages):
                    raise RuntimeError("structured also failed")

            return _Structured()

    with pytest.raises(RuntimeError, match="structured also failed"):
        invoke_structured(_FailStub([]), "sys", "user", Tiny)
