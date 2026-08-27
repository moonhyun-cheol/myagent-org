"""Parse natural-language HITL approval into HumanFeedback."""

from __future__ import annotations

import re

from cqr_product_pipeline.schemas.models import HumanFeedback, HumanFeedbackDecision, Verdict

_CONCEPT_ID = r"[A-Z][A-Z0-9_-]*\d{2,}"
_ACTION = r"(?:승인|approve|ok|go|진행|채택|거절|reject|kill|제외|빼|수정|revise|보완|재검토)"

_APPROVE = re.compile(
    rf"(?:concept\s*)?({_CONCEPT_ID}|[A-Z]|\d{{2,}})\s*(?:승인|approve|ok|go|진행|채택)",
    re.I,
)
_REJECT = re.compile(
    rf"(?:concept\s*)?({_CONCEPT_ID}|[A-Z]|\d{{2,}})\s*(?:거절|reject|kill|제외|빼)",
    re.I,
)
_REVISE = re.compile(
    rf"(?:concept\s*)?({_CONCEPT_ID}|[A-Z]|\d{{2,}})\s*(?:수정|revise|보완|재검토)",
    re.I,
)
_OVERRIDE_VERDICT = re.compile(
    r"(?:override|verdict)\s*(GO|HOLD|KILL)",
    re.I,
)
_REQUEST_RESEARCH = re.compile(
    r"(?:추가\s*조사|more\s*research|request\s*research)[:：]?\s*(.+)$",
    re.I | re.M,
)
_APPROVE_ALL = re.compile(
    r"(?:둘\s*다|모두|전부|all)\s*(?:승인|approve|진행)",
    re.I,
)


def _resolve_concept_ref(ref: str, default_concept_ids: list[str] | None) -> str:
    ref = ref.strip()
    if not default_concept_ids:
        return ref.upper() if len(ref) == 1 and ref.isalpha() else ref

    if ref in default_concept_ids:
        return ref

    upper = ref.upper()
    if len(upper) == 1 and upper.isalpha():
        idx = ord(upper) - ord("A")
        if 0 <= idx < len(default_concept_ids):
            return default_concept_ids[idx]

    if ref.isdigit():
        for cid in default_concept_ids:
            if cid.endswith(ref) or cid.endswith(f"-{ref}"):
                return cid

    return ref


def parse_approve_text(text: str, *, default_concept_ids: list[str] | None = None) -> HumanFeedback:
    """Heuristic NL → HumanFeedback. Falls back to approve-all if only generic approval."""
    text = text.strip()
    decisions: list[HumanFeedbackDecision] = []
    seen: set[str] = set()

    for pattern, action in (
        (_APPROVE, "approve"),
        (_REJECT, "reject"),
        (_REVISE, "revise"),
    ):
        for match in pattern.finditer(text):
            cid = _resolve_concept_ref(match.group(1), default_concept_ids)
            if cid in seen:
                continue
            seen.add(cid)
            decisions.append(HumanFeedbackDecision(concept_id=cid, action=action))

    if not decisions and default_concept_ids:
        lower = text.lower()
        approve_all = _APPROVE_ALL.search(text) or any(
            k in lower for k in ("승인", "approve", "진행", "ok", "go")
        )
        if approve_all:
            reject_refs = {m.group(1) for m in _REJECT.finditer(text)}
            reject_ids = {
                _resolve_concept_ref(r, default_concept_ids) for r in reject_refs
            }
            for cid in default_concept_ids:
                if cid in reject_ids or cid in seen:
                    continue
                decisions.append(HumanFeedbackDecision(concept_id=cid, action="approve"))

    override_notes = None
    if "TLP" in text or "$" in text or "형제" in text or "sibling" in text.lower():
        override_notes = text

    request_research = None
    m = _REQUEST_RESEARCH.search(text)
    if m:
        request_research = m.group(1).strip()

    override_verdict = None
    vm = _OVERRIDE_VERDICT.search(text)
    if vm:
        override_verdict = Verdict(vm.group(1).upper())
        if decisions:
            decisions[0] = decisions[0].model_copy(update={"override_verdict": override_verdict})

    return HumanFeedback(
        decisions=decisions,
        override_notes=override_notes,
        request_research=request_research,
    )
