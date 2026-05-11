"""Tests for scripts.parse_jd."""
from __future__ import annotations

from scripts.parse_jd import parse_jd


def test_parse_jd_extracts_role_title(jd_text_typical: str) -> None:
    a = parse_jd(jd_text_typical)
    assert a["role_title"] is not None
    assert "backend" in a["role_title"].lower()


def test_parse_jd_infers_senior_level(jd_text_typical: str) -> None:
    a = parse_jd(jd_text_typical)
    assert a["level"] == "senior"


def test_parse_jd_separates_required_and_preferred(jd_text_typical: str) -> None:
    a = parse_jd(jd_text_typical)
    required = " ".join(a["required"]).lower()
    preferred = " ".join(a["preferred"]).lower()
    assert "5+ years" in required or "backend" in required
    assert "kafka" in preferred or "graphql" in preferred or "payments" in preferred


def test_parse_jd_extracts_responsibilities(jd_text_typical: str) -> None:
    a = parse_jd(jd_text_typical)
    assert len(a["responsibilities"]) >= 2


def test_parse_jd_finds_known_keywords(jd_text_typical: str) -> None:
    a = parse_jd(jd_text_typical)
    keywords = {k["keyword"] for k in a["keywords"]}
    # synonyms.json keys we expect to be matched
    assert "Python" in keywords
    assert "PostgreSQL" in keywords
    assert "AWS" in keywords or "GCP" in keywords


def test_parse_jd_dealbreakers_detected(jd_text_with_dealbreakers: str) -> None:
    a = parse_jd(jd_text_with_dealbreakers)
    db = a["dealbreakers"]
    assert "clearance" in db
    assert "citizenship" in db
    assert "onsite" in db
    assert "travel" in db


def test_parse_jd_minimal_input(jd_text_minimal: str) -> None:
    a = parse_jd(jd_text_minimal)
    assert a["level"] == "junior"
    keywords = {k["keyword"] for k in a["keywords"]}
    assert "JavaScript" in keywords
    assert "React" in keywords


def test_parse_jd_empty_input() -> None:
    a = parse_jd("")
    assert a["required"] == []
    assert a["level"] is None
    assert a["role_title"] is None


def test_parse_jd_inline_text_no_path_resolution(jd_text_typical: str) -> None:
    """The parser should accept inline text without choking on path resolution."""
    a = parse_jd(jd_text_typical)
    assert a["_raw_text_length"] == len(jd_text_typical.strip())
