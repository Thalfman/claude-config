"""Tests for scripts.score_relevance."""
from __future__ import annotations

from scripts.parse_jd import parse_jd
from scripts.score_relevance import score_relevance


def test_score_strong_for_directly_demonstrated_skill(jd_text_typical: str, inventory_typical: dict) -> None:
    jd = parse_jd(jd_text_typical)
    rel = score_relevance(inventory_typical, jd)
    # We expect Python/PostgreSQL/AWS coverage to be STRONG since the inventory uses them
    strong_reqs = [r for r in rel["requirements"] if r["coverage"] == "STRONG"]
    assert len(strong_reqs) >= 1


def test_score_finds_kafka_evidence(jd_text_typical: str, inventory_typical: dict) -> None:
    jd = parse_jd(jd_text_typical)
    rel = score_relevance(inventory_typical, jd)
    kafka_reqs = [r for r in rel["requirements"] if "kafka" in r["requirement"].lower()]
    assert kafka_reqs, "Expected Kafka to appear in JD requirements"
    # Inventory mentions Kafka in the orders service migration bullet
    assert any(r["coverage"] in {"STRONG", "PARTIAL"} for r in kafka_reqs)


def test_score_marks_gap_for_unmatched_requirement(inventory_typical: dict) -> None:
    """A JD asking for Rust should be a GAP since the inventory has none."""
    jd_text = """
    Senior Engineer
    Required:
    - 5+ years Rust experience
    - Embedded systems experience
    """
    jd = parse_jd(jd_text)
    rel = score_relevance(inventory_typical, jd)
    rust_reqs = [r for r in rel["requirements"] if "rust" in r["requirement"].lower()]
    assert rust_reqs
    assert all(r["coverage"] == "GAP" for r in rust_reqs)


def test_score_summary_has_required_coverage_pct(jd_text_typical: str, inventory_typical: dict) -> None:
    jd = parse_jd(jd_text_typical)
    rel = score_relevance(inventory_typical, jd)
    s = rel["summary"]
    assert "required_coverage_pct" in s
    assert 0 <= s["required_coverage_pct"] <= 100


def test_score_recency_boost(inventory_typical: dict) -> None:
    """Bullets in the current role should be preferred when scores tie."""
    jd_text = """
    Senior Engineer

    Required:
    - Python
    """
    jd = parse_jd(jd_text)
    rel = score_relevance(inventory_typical, jd)
    py_reqs = [r for r in rel["requirements"] if "python" in r["requirement"].lower()]
    assert py_reqs
    top = py_reqs[0]["evidence"][0]
    assert top["company"] == "Acme Payments"  # current role


def test_score_handles_empty_jd(inventory_typical: dict) -> None:
    rel = score_relevance(inventory_typical, parse_jd(""))
    assert rel["requirements"] == []
    assert rel["summary"]["total_requirements"] == 0
