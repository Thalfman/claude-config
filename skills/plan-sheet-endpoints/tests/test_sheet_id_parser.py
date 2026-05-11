from scripts.sheet_id_parser import (
    ContinuationRef,
    parse_continuation_refs,
    parse_sheet_id,
)


def test_parse_sheet_id_sheet_n_of_m():
    assert parse_sheet_id("SHEET 12 OF 25") == "12"


def test_parse_sheet_id_site_plan_dash_n():
    assert parse_sheet_id("SITE PLAN - 5") == "5"


def test_parse_sheet_id_sp_n():
    assert parse_sheet_id("SP-12") == "12"


def test_parse_sheet_id_s_dash_n():
    assert parse_sheet_id("S-3") == "3"


def test_parse_sheet_id_returns_none_for_no_match():
    assert parse_sheet_id("just some text with no sheet identifier") is None


def test_parse_continuation_refs_match_to_sheet():
    refs = parse_continuation_refs("MATCH TO SHEET 11")
    assert len(refs) == 1
    assert refs[0] == ContinuationRef(direction="to", target="11", original="MATCH TO SHEET 11")


def test_parse_continuation_refs_see_sheet():
    refs = parse_continuation_refs("SEE SHEET 5")
    assert refs[0].direction == "to"
    assert refs[0].target == "5"


def test_parse_continuation_refs_match_to_site_plan_dash_n():
    refs = parse_continuation_refs("MATCH TO SITE PLAN - 12")
    assert refs[0].target == "12"
    assert refs[0].direction == "to"


def test_parse_continuation_refs_continued_from():
    refs = parse_continuation_refs("CONTINUED FROM SHEET 7")
    assert refs[0].direction == "from"
    assert refs[0].target == "7"


def test_parse_continuation_refs_multiple_in_one_text():
    text = "MATCH TO SHEET 11. CONTINUED FROM SHEET 9."
    refs = parse_continuation_refs(text)
    assert len(refs) == 2
    targets = {r.target for r in refs}
    assert targets == {"11", "9"}


def test_parse_continuation_refs_returns_empty_for_no_match():
    assert parse_continuation_refs("plain text") == []
