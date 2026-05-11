"""
Render every markdown deliverable in output/JB##########/ to PDF.

Usage:
    python render_all.py [output_root]

Default output_root is ./output. Renders:
  - {root}/{jb}/cd_scrubs.md, open_items.md, qc_report.md
  - {root}/{jb}/{NN_Entity}/cover_letter.md (with letterhead)
  - {root}/{jb}/{NN_Entity}/application_form.md
  - {root}/{jb}/{NN_Entity}/research.md
  - {root}/{jb}/{NN_Entity}/fee_calculation.md
  - {root}/{jb}/{NN_Entity}/traffic_control_plan.md
  - {root}/{jb}/{NN_Entity}/coi.md
  - {root}/{jb}/{NN_Entity}/route_map.md
  - {root}/{jb}/{NN_Entity}/transmittal_index.md
"""
from __future__ import annotations
import os, re, sys
from pathlib import Path

try:
    from .render_md_to_pdf import render  # package-style invocation: python -m scripts.render_all
except ImportError:
    from render_md_to_pdf import render   # script-style invocation: python render_all.py

DOC_TITLES = {
    'cover_letter':       'Cover Letter',
    'application_form':   'Permit Application (prefill)',
    'research':           'Entity Research & Verification',
    'fee_calculation':    'Permit Fee Calculation',
    'traffic_control_plan': 'Traffic Control Plan',
    'coi':                'Certificate of Insurance (placeholder)',
    'route_map':          'Route Map (specification)',
    'transmittal_index':  'Transmittal Index',
    'cd_scrubs':          'CD Scrub Recipe',
    'open_items':         'Open Items',
    'qc_report':          'Quality Check Report',
}


def entity_label(folder_name: str) -> str:
    # 01_MDOT_Grand_Region -> MDOT Grand Region
    parts = folder_name.split('_', 1)
    if len(parts) == 2 and parts[0].isdigit():
        return parts[1].replace('_', ' ')
    return folder_name.replace('_', ' ')


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else 'output')
    if not root.is_dir():
        print(f'error: {root} is not a directory', file=sys.stderr)
        sys.exit(1)

    rendered = []
    for jb_dir in sorted(root.iterdir()):
        if not jb_dir.is_dir() or not jb_dir.name.startswith('JB'):
            continue
        jb = jb_dir.name

        # JB-level markdowns (cd_scrubs, open_items, qc_report)
        for md in sorted(jb_dir.glob('*.md')):
            stem = md.stem
            title = DOC_TITLES.get(stem, stem.replace('_', ' ').title())
            pdf = md.with_suffix('.pdf')
            try:
                render(md, pdf, cover_letter=False, jb_number=jb,
                       entity='(project-wide)', doc_title=title)
                rendered.append(str(pdf))
            except Exception as e:
                print(f'  FAIL {md}: {e}')

        # Per-entity markdowns
        for ent_dir in sorted(jb_dir.iterdir()):
            if not ent_dir.is_dir(): continue
            ent_label = entity_label(ent_dir.name)
            for md in sorted(ent_dir.glob('*.md')):
                stem = md.stem
                title = DOC_TITLES.get(stem, stem.replace('_', ' ').title())
                pdf = md.with_suffix('.pdf')
                cover = (stem == 'cover_letter')
                try:
                    render(md, pdf, cover_letter=cover, jb_number=jb,
                           entity=ent_label, doc_title=title)
                    rendered.append(str(pdf))
                except Exception as e:
                    print(f'  FAIL {md}: {e}')
    print(f'\nRendered {len(rendered)} PDFs:')
    for p in rendered:
        sz = os.path.getsize(p)
        print(f'  {p}  ({sz:,} bytes)')


if __name__ == '__main__':
    main()
