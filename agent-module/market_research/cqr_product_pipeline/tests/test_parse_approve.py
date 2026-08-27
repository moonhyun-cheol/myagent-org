"""Tests for NL HITL parser."""

from cqr_product_pipeline.cli.parse_approve_text import parse_approve_text
from cqr_product_pipeline.schemas.models import HumanFeedback


def test_parse_approve_reject():
    fb = parse_approve_text("A 승인, B 거절")
    assert isinstance(fb, HumanFeedback)
    actions = {d.concept_id: d.action for d in fb.decisions}
    assert actions.get("A") == "approve"
    assert actions.get("B") == "reject"


def test_parse_generic_approve_with_defaults():
    fb = parse_approve_text("진행해줘", default_concept_ids=["A", "B"])
    ids = {d.concept_id for d in fb.decisions if d.action == "approve"}
    assert "A" in ids
    assert "B" in ids


def test_parse_request_research():
    fb = parse_approve_text("추가 조사: GRAMICCI cargo shorts")
    assert fb.request_research
    assert "GRAMICCI" in fb.request_research


def test_parse_letter_maps_to_concept_ids():
    ids = ["LIB-SUM-CARGO-01", "LIB-SUM-CARGO-02"]
    fb = parse_approve_text("A 승인, B 거절", default_concept_ids=ids)
    actions = {d.concept_id: d.action for d in fb.decisions}
    assert actions["LIB-SUM-CARGO-01"] == "approve"
    assert actions["LIB-SUM-CARGO-02"] == "reject"


def test_parse_numeric_suffix_and_full_id():
    ids = ["LIB-SUM-CARGO-01", "LIB-SUM-CARGO-02"]
    fb = parse_approve_text(
        "LIB-SUM-CARGO-02 승인, 01 거절",
        default_concept_ids=ids,
    )
    actions = {d.concept_id: d.action for d in fb.decisions}
    assert actions["LIB-SUM-CARGO-02"] == "approve"
    assert actions["LIB-SUM-CARGO-01"] == "reject"
