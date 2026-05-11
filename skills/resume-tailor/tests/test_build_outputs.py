"""Tests for scripts.build_outputs (markdown + reports; docx is exercised opportunistically)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.build_outputs import (
    derive_filename,
    render_coverage_scorecard,
    render_mapping_report,
    slugify,
)
from scripts.parse_jd import parse_jd
from scripts.score_relevance import score_relevance


def test_slugify() -> None:
    assert slugify("Senior Backend Engineer") == "Senior_Backend_Engineer"
    assert slugify("C++ Developer") == "C_Developer"
    assert slugify("") == "X"
    assert slugify(None) == "X"


def test_derive_filename(tailored_md_clean: str, jd_text_typical: str) -> None:
    jd = parse_jd(jd_text_typical)
    name = derive_filename(tailored_md_clean, jd)
    assert "Alex" in name
    assert "Rivera" in name
    assert "Resume" in name


def test_mapping_report_includes_coverage_markers(jd_text_typical: str, inventory_typical: dict) -> None:
    jd = parse_jd(jd_text_typical)
    rel = score_relevance(inventory_typical, jd)
    report = render_mapping_report(rel)
    assert "# Mapping Report" in report
    # at least one of these markers should appear
    assert "STRONG" in report or "PARTIAL" in report or "GAP" in report


def test_coverage_scorecard_includes_keyword_table(jd_text_typical: str, inventory_typical: dict, tailored_md_clean: str) -> None:
    jd = parse_jd(jd_text_typical)
    rel = score_relevance(inventory_typical, jd)
    scorecard = render_coverage_scorecard(jd, rel, tailored_md_clean)
    assert "ATS keyword density" in scorecard
    assert "Python" in scorecard


def test_docx_render(tmp_path: Path, tailored_md_clean: str) -> None:
    """Smoke test for DOCX rendering. Skipped if python-docx isn't installed."""
    pytest.importorskip("docx")
    from scripts.build_outputs import render_docx

    out = tmp_path / "test.docx"
    render_docx(tailored_md_clean, out)
    assert out.exists() and out.stat().st_size > 0
