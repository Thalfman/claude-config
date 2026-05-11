#!/usr/bin/env python3
"""
merge_kmz.py - Merge multiple per-PRM KMZ files into one combined KMZ for a JB.

Usage:
    python merge_kmz.py JB123/PRM*/PRM*.kmz --job-label "JB123" \
        --output JB123/JB123_combined.kmz

Output tree:
    JB123 (Document)
    ├── PRM456 (Folder, copied from input)
    │   ├── By Sheet
    │   ├── All Routes Combined
    │   └── QC: Anchors
    ├── PRM789
    │   ├── ...
    └── Combined Route (all PRMs merged into one folder, with PRM-prefixed linestring names)
"""

import argparse
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

NS = 'http://www.opengis.net/kml/2.2'
ET.register_namespace('', NS)


def kml_tag(local_name):
    return f'{{{NS}}}{local_name}'


def parse_kmz(path):
    """Open a .kmz, extract the doc.kml content, return the parsed root Element."""
    with zipfile.ZipFile(path, 'r') as zf:
        kml_names = [n for n in zf.namelist() if n.lower().endswith('.kml')]
        if not kml_names:
            raise RuntimeError(f"No .kml inside {path}")
        # Prefer doc.kml if present; otherwise first
        kml_name = 'doc.kml' if 'doc.kml' in kml_names else kml_names[0]
        with zf.open(kml_name) as f:
            tree = ET.parse(f)
    return tree.getroot()


def find_document(root):
    """Return the <Document> element of a KML root."""
    if root.tag == kml_tag('Document'):
        return root
    return root.find(kml_tag('Document'))


def get_text_child(elem, tag_local):
    child = elem.find(kml_tag(tag_local))
    return child.text if child is not None else None


def write_combined(out_path, combined_root):
    """Write a KMZ containing a single doc.kml."""
    out_path = Path(out_path)
    if out_path.suffix.lower() != '.kmz':
        out_path = out_path.with_suffix('.kmz')
    tree = ET.ElementTree(combined_root)
    # Write doc.kml inside the zip
    with zipfile.ZipFile(out_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Serialize the tree to a string
        from io import BytesIO
        buf = BytesIO()
        tree.write(buf, xml_declaration=True, encoding='utf-8')
        zf.writestr('doc.kml', buf.getvalue())
    return out_path


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    ap.add_argument('inputs', nargs='+', help='Input per-PRM KMZ files (glob OK)')
    ap.add_argument('--job-label', default=None, help='JB display name')
    ap.add_argument('--output', required=True, help='Combined KMZ output path')
    args = ap.parse_args()

    job_label = args.job_label or 'Combined Job'

    # Build the new KML root
    new_root = ET.Element(kml_tag('kml'))
    new_doc = ET.SubElement(new_root, kml_tag('Document'))
    name_el = ET.SubElement(new_doc, kml_tag('name'))
    name_el.text = job_label

    # Folder for combined-everything
    combined_folder = ET.SubElement(new_doc, kml_tag('Folder'))
    cf_name = ET.SubElement(combined_folder, kml_tag('name'))
    cf_name.text = 'Combined Route (all PRMs)'

    summary_lines = [f"Job: {job_label}"]
    n_inputs = 0

    for inp in args.inputs:
        path = Path(inp)
        if not path.exists():
            print(f"WARN: {path} not found, skipping", file=sys.stderr)
            continue

        try:
            in_root = parse_kmz(path)
        except Exception as e:
            print(f"WARN: failed to parse {path}: {e}", file=sys.stderr)
            continue

        in_doc = find_document(in_root)
        if in_doc is None:
            print(f"WARN: no Document in {path}, skipping", file=sys.stderr)
            continue

        # Determine PRM label from the input doc's <name> or from the parent folder name
        prm_label = get_text_child(in_doc, 'name')
        if not prm_label:
            prm_label = path.parent.name

        # Add a PRM folder to the new doc and copy all child Folders/Placemarks into it
        prm_folder = ET.SubElement(new_doc, kml_tag('Folder'))
        prm_name = ET.SubElement(prm_folder, kml_tag('name'))
        prm_name.text = prm_label

        copied_polylines = 0
        copied_points = 0

        for child in list(in_doc):
            tag = child.tag
            if tag in (kml_tag('name'), kml_tag('description'), kml_tag('Style'),
                       kml_tag('StyleMap'), kml_tag('open'), kml_tag('visibility')):
                continue
            # Copy folder/placemark wholesale into PRM folder
            prm_folder.append(child)

            # Also extract LineStrings/Points into the combined folder for cross-PRM display
            for ls in child.iter(kml_tag('LineString')):
                pm_parent = ET.SubElement(combined_folder, kml_tag('Placemark'))
                pm_name = ET.SubElement(pm_parent, kml_tag('name'))
                # Try to take the placemark name from the LineString's parent Placemark
                parent_pm = None
                for p in child.iter(kml_tag('Placemark')):
                    if any(ls is el for el in p.iter(kml_tag('LineString'))):
                        parent_pm = p
                        break
                pm_label = None
                if parent_pm is not None:
                    name_node = parent_pm.find(kml_tag('name'))
                    if name_node is not None and name_node.text:
                        pm_label = name_node.text
                pm_name.text = pm_label or f"{prm_label} segment"
                # Clone the LineString
                from copy import deepcopy
                pm_parent.append(deepcopy(ls))
                # Reuse style if present on the source placemark
                if parent_pm is not None:
                    style_node = parent_pm.find(kml_tag('Style'))
                    if style_node is not None:
                        pm_parent.append(deepcopy(style_node))
                copied_polylines += 1

        summary_lines.append(f"  {prm_label}: {copied_polylines} linestrings copied to combined")
        n_inputs += 1

    if n_inputs == 0:
        print("ERROR: no valid input KMZs", file=sys.stderr)
        sys.exit(1)

    desc = ET.SubElement(new_doc, kml_tag('description'))
    desc.text = '\n'.join(summary_lines)

    out_path = write_combined(args.output, new_root)
    print(f"Wrote {out_path}", file=sys.stderr)
    for line in summary_lines:
        print(line, file=sys.stderr)


if __name__ == '__main__':
    main()
