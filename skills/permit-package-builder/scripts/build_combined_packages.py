"""
Build a single combined PDF per (JB, entity) for submission convenience.

Concatenates per-package PDFs in the minimal-skill submission order:
  1. cover_letter
  2. application_form
  3. transmittal
  4. fee_calculation
  5. construction_drawings (the scrubbed CD)
  6. (optional) traffic_control_plan — only when custom design is required
  7. reference_* (any reference PDFs the entity website provides)

Output: output/JB##########/{NN_Entity}/SUBMISSION_PACKAGE.pdf
"""
from __future__ import annotations
import os, sys, glob
from pathlib import Path
import fitz

ORDER = [
    'cover_letter.pdf',
    'application_form.pdf',     # ROW permit packages
    'notification_form.pdf',    # pole-attachment packages
    'pole_list.pdf',            # pole-attachment packages
    'transmittal.pdf',
    'fee_calculation.pdf',      # ROW permit packages
    'construction_drawings.pdf',
    'traffic_control_plan.pdf', # only when custom design required
]


def combine_entity_package(ent_dir: Path, jb: str) -> Path | None:
    out = ent_dir / 'SUBMISSION_PACKAGE.pdf'
    doc = fitz.open()
    pages_added = 0
    for name in ORDER:
        p = ent_dir / name
        if not p.exists():
            print(f'  [skip] {p.name} not found')
            continue
        src = fitz.open(str(p))
        doc.insert_pdf(src)
        pages_added += src.page_count
        src.close()
    # Append reference_* pdfs at the end
    for ref in sorted(ent_dir.glob('reference_*.pdf')):
        src = fitz.open(str(ref))
        doc.insert_pdf(src)
        pages_added += src.page_count
        src.close()
    if pages_added == 0:
        doc.close()
        return None
    doc.set_metadata({
        'title': f'{jb} — {ent_dir.name.replace("_", " ")} — Permit Submission Package',
        'author': 'MasTec Communications Group',
        'subject': 'Right-of-way permit submission',
        'keywords': f'{jb}, permit, right-of-way, MasTec, Comcast',
    })
    doc.save(str(out), garbage=4, deflate=True)
    doc.close()
    return out


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else 'output')
    for jb_dir in sorted(root.iterdir()):
        if not jb_dir.is_dir() or not jb_dir.name.startswith('JB'):
            continue
        jb = jb_dir.name
        for ent_dir in sorted(jb_dir.iterdir()):
            if not ent_dir.is_dir(): continue
            print(f'\n=== {jb} / {ent_dir.name} ===')
            out = combine_entity_package(ent_dir, jb)
            if out:
                print(f'  -> {out}  ({os.path.getsize(out):,} bytes)')


if __name__ == '__main__':
    main()
