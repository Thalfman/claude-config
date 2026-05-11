"""
Scrub a Comcast/MasTec construction-drawing PDF for the canonical boilerplate
errors documented in references/known_boilerplate_errors.md, and stamp every
affected page with a visible REVISION NOTE banner naming the corrections.

What this scrub does
--------------------
1. Removes wrong-state 811 callouts and out-of-state phone numbers, generic
   notice-period strings ("48HRS IN ADVANCE"), and SEFNCO legal-boilerplate
   references that older drafter templates carry.
2. Adds a yellow-bordered REVISION NOTE on every page that had a redaction,
   containing the corrected wording so a permit reviewer can read the right
   text without paging back to the cover sheet.
3. Adds a larger REVISION NOTE on the cover sheet quoting the corrected
   General Notes Note 1 and Note 17 in full.

What this scrub does NOT do
---------------------------
In-line text replacement at the redacted spot. The CD pages are stored
portrait 792x1224 with rotation flag 270 to render as landscape 1224x792.
PyMuPDF's insert_textbox does not place rotated-text-rect content at the
right pixel position without bespoke rotation math, so the v1 scrub leaves
visible gaps where wrong text was redacted, and supplies the corrected
text in the REVISION NOTE banners. For final-final submission the drafter
should regenerate the General Notes sheet from the source .dwg.

CLI
---

    python -m scripts.scrub_cd <input.pdf> <output.pdf> [--state MI]

Default state is MI; the corrected 811 callout currently hard-codes Miss Dig
811. To extend to other states, add an entry to STATE_811 below.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Tuple


STATE_811: Dict[str, Dict[str, str]] = {
    "MI": {
        "name": "MISS DIG 811",
        "phone": "(800) 482-7171",
        "notice": "three working days prior",
        "authority": "Public Act 174 of 2013",
    },
    "IN": {
        "name": "Indiana 811",
        "phone": "(800) 382-5544",
        "notice": "two working days prior",
        "authority": "IC 8-1-26",
    },
    "IL": {
        "name": "JULIE",
        "phone": "(800) 892-0123",
        "notice": "two working days prior",
        "authority": "220 ILCS 50",
    },
}


# Patterns to redact unconditionally regardless of correct state.
COMMON_REDACT_PATTERNS = [
    "SEFNCO HEREBY",
    "SEFNCO COMMUNICATION INC.",
    "SEFNCO COMMUNICATIONS INC.",
    "SEFNCO COMMUNICATION, INC.",
    "SEFNCO",
]

# Patterns to redact only when they don't match the state of work. The
# "Indiana 811" / "JULIE" / etc. literal strings get redacted when state != source.
# Plus the unbranded Indiana / out-of-state phone-number-with-48hr fingerprint
# that appeared in the JB0002479252 canonical reference.
WRONG_STATE_REDACT = {
    "MI": [
        "Indiana 811",
        "INDIANA 811",
        "Indiana One Call",
        "DIG ALERT",
        "JULIE",
        "1-800-424-5555",   # generic out-of-state placeholder seen in canonical ref
        "1-800-382-5544",   # IN
        "800-892-0123",     # IL
        "48HRS IN ADVANCE",
        "48 HOURS BEFORE YOU DIG",
    ],
}


def _shrink(r, dx, dy):
    import fitz
    return fitz.Rect(r.x0 + dx, r.y0 + dy, r.x1 - dx, r.y1 - dy)


def scrub(input_pdf: Path, output_pdf: Path, state: str = "MI") -> Dict:
    """
    Apply the v1 redact-and-banner scrub. Returns a dict with QC results
    suitable for logging.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError as e:
        raise SystemExit(
            "PyMuPDF (fitz) is required for the CD scrub. "
            "Install with: pip install pymupdf"
        ) from e

    if state not in STATE_811:
        raise SystemExit(f"unknown state {state}; supported: {sorted(STATE_811)}")
    s = STATE_811[state]

    doc = fitz.open(str(input_pdf))
    patterns: List[str] = []
    patterns.extend(COMMON_REDACT_PATTERNS)
    patterns.extend(WRONG_STATE_REDACT.get(state, []))

    hit_log: List[Tuple[int, str]] = []
    for pno in range(doc.page_count):
        page = doc[pno]
        for pat in patterns:
            for r in page.search_for(pat):
                page.add_redact_annot(r, fill=(1, 1, 1))
                hit_log.append((pno + 1, pat))
    for pno in range(doc.page_count):
        doc[pno].apply_redactions()

    pages_with_redaction = sorted(set(p for p, _ in hit_log))

    per_page_stamp = (
        f"REVISION (MasTec permitting): General Notes 811 callout corrected to "
        f"{s['name']}, {s['phone']}, {s['notice']}, per {s['authority']}. "
        f"Predecessor drafter-template legal boilerplate replaced with "
        f"MASTEC COMMUNICATIONS GROUP and COMCAST CABLE COMMUNICATIONS, LLC. "
        f"Original CD retained for audit; full change log in cd_scrubs.md."
    )
    for pno in pages_with_redaction:
        page = doc[pno - 1]
        rect = fitz.Rect(20, 5, 720, 42)
        page.draw_rect(rect, color=(0.7, 0, 0), width=0.7, fill=(1, 1, 0.85))
        inner = _shrink(rect, 3, 3)
        rc = page.insert_textbox(inner, per_page_stamp,
                                 fontname="helv", fontsize=6.5,
                                 color=(0.5, 0, 0), align=fitz.TEXT_ALIGN_LEFT)
        if rc < 0:
            page.insert_textbox(inner, per_page_stamp,
                                fontname="helv", fontsize=5.5, color=(0.5, 0, 0))

    cover_text = (
        f"PERMIT-PACKAGE REVISION NOTE  --  generated by MasTec permitting team.\n"
        f"Two corrections were applied to this CD before bundling into permit packages:\n"
        f"(1) The General Notes 811 callout (Note 17) had a wrong-state phone number and "
        f"a non-{state} notice period. The correct text for {state} work, per "
        f"{s['authority']}, is: 'CALL {s['name']} A MINIMUM OF "
        f"{s['notice'].upper().replace('PRIOR','')}TO ANY EXCAVATION. "
        f"DIAL 811 IN-{state} OR {s['phone']}.'\n"
        f"(2) Predecessor drafter-template legal boilerplate naming a third-party "
        f"company was replaced. General Notes Note 1 should now be read as: "
        f"'THE LOCATIONS OF UTILITIES SHOWN ON THESE DRAWINGS ARE ONLY APPROXIMATE. "
        f"MASTEC COMMUNICATIONS GROUP HEREBY DISCLAIMS ANY RESPONSIBILITY ...' "
        f"Title-block footer block on every sheet should be read as: 'PROPERTY OF "
        f"COMCAST CABLE COMMUNICATIONS, LLC. ...'\n"
        f"Original CD retained for audit; full change log in cd_scrubs.md."
    )
    page = doc[0]
    rect = fitz.Rect(20, 5, 20 + 760, 5 + 135)
    page.draw_rect(rect, color=(0.7, 0, 0), width=1.0, fill=(1, 1, 0.85))
    page.insert_textbox(_shrink(rect, 5, 5), cover_text,
                        fontname="helv", fontsize=7.5,
                        color=(0.5, 0, 0), align=fitz.TEXT_ALIGN_LEFT)

    doc.save(str(output_pdf), garbage=4, deflate=True)
    doc.close()

    # QC verification
    doc2 = fitz.open(str(output_pdf))
    qc_targets_present: List[Tuple[str, int]] = []
    for pat in patterns:
        for pno in range(doc2.page_count):
            if pat.lower() in doc2[pno].get_text().lower():
                qc_targets_present.append((pat, pno + 1))
    doc2.close()

    return {
        "input": str(input_pdf),
        "output": str(output_pdf),
        "state": state,
        "pages_with_redaction": pages_with_redaction,
        "redaction_count": len(hit_log),
        "qc_failed_pages": qc_targets_present,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("input_pdf", type=Path)
    parser.add_argument("output_pdf", type=Path)
    parser.add_argument("--state", default="MI", help="State of work (MI, IN, IL, ...)")
    args = parser.parse_args()

    result = scrub(args.input_pdf, args.output_pdf, state=args.state)
    n_redact = result["redaction_count"]
    n_pages = len(result["pages_with_redaction"])
    print(f"Scrubbed {args.input_pdf} -> {args.output_pdf}")
    print(f"  {n_redact} redactions across {n_pages} page(s)")
    if result["qc_failed_pages"]:
        print(f"  QC failed: target strings still present:")
        for pat, pno in result["qc_failed_pages"]:
            print(f"    page {pno}: {pat!r}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
