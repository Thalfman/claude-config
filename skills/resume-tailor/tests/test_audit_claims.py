"""Tests for scripts.audit_claims — the fabrication firewall."""
from __future__ import annotations

from scripts.audit_claims import audit, render_report


def test_audit_clean_resume_passes(tailored_md_clean: str, inventory_typical: dict) -> None:
    result = audit(tailored_md_clean, inventory_typical)
    # No fabricated numbers, all skills traceable, all companies in inventory.
    bad = [i for i in result["issues"] if i["kind"] != "ORPHAN_BULLET"]
    assert bad == [], f"Expected no fabrication issues, got: {bad}"


def test_audit_flags_fabricated_number(tailored_md_with_fabrication: str, inventory_typical: dict) -> None:
    result = audit(tailored_md_with_fabrication, inventory_typical)
    nums = [i for i in result["issues"] if i["kind"] == "NUMBERS_NOT_IN_INVENTORY"]
    assert nums, "Expected the fabricated 50% number to be flagged"
    assert any("50%" in i["snippet"] for i in nums)


def test_audit_flags_skill_not_in_inventory(tailored_md_with_fabrication: str, inventory_typical: dict) -> None:
    result = audit(tailored_md_with_fabrication, inventory_typical)
    skills = [i for i in result["issues"] if i["kind"] == "SKILLS_NOT_IN_INVENTORY"]
    snippets = {i["snippet"].lower() for i in skills}
    # Rust and Cassandra and GraphQL aren't in inventory_typical's skills
    assert "rust" in snippets or "cassandra" in snippets or "graphql" in snippets


def test_audit_flags_company_not_in_inventory(tailored_md_with_fabrication: str, inventory_typical: dict) -> None:
    result = audit(tailored_md_with_fabrication, inventory_typical)
    drift = [i for i in result["issues"] if i["kind"] == "ENTITY_DRIFT"]
    snippets = {i["snippet"].lower() for i in drift}
    assert "megacorp" in snippets


def test_render_report_clean(tailored_md_clean: str, inventory_typical: dict) -> None:
    result = audit(tailored_md_clean, inventory_typical)
    report = render_report(result)
    if not [i for i in result["issues"] if i["kind"] != "ORPHAN_BULLET"]:
        # Either fully clean (the more common branch) or has only orphan bullets.
        assert "Audit Report" in report


def test_render_report_with_issues(tailored_md_with_fabrication: str, inventory_typical: dict) -> None:
    result = audit(tailored_md_with_fabrication, inventory_typical)
    report = render_report(result)
    assert "Issues flagged" in report
    assert "NUMBERS_NOT_IN_INVENTORY" in report or "SKILLS_NOT_IN_INVENTORY" in report
