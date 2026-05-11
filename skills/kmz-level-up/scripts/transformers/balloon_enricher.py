"""balloon_enricher -- generate HTML <description> from feature attributes."""
from __future__ import annotations

import html

from scripts.kml_model import Document


_TABLE_HEAD = (
    '<div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 6px;">'
    '<table style="border-collapse: collapse;">'
)
_TABLE_FOOT = "</table></div>"
_ROW = '<tr><td style="padding: 2px 8px; font-weight: 600;">{key}</td><td style="padding: 2px 8px;">{value}</td></tr>'


def _is_blank_value(v) -> bool:
    """Treat empty string and the literal 'Null' as blank.

    Sphere/ESRI exports stamp 'Null' into every absent field rather than
    leaving the cell empty. Showing those rows clutters the balloon, so
    drop them when generating fresh balloons.
    """
    if v is None:
        return True
    s = str(v).strip()
    return s == "" or s.lower() == "null"


def apply(doc: Document, display_attributes: list[str], preserve_existing: bool) -> None:
    for f in doc.all_features():
        if not f.attributes:
            continue
        if preserve_existing and f.description_html.strip():
            continue
        rows = []
        for key in display_attributes:
            if key not in f.attributes:
                continue
            value = f.attributes[key]
            if _is_blank_value(value):
                continue
            rows.append(_ROW.format(
                key=html.escape(str(key)),
                value=html.escape(str(value)),
            ))
        if not rows:
            continue
        f.description_html = _TABLE_HEAD + "".join(rows) + _TABLE_FOOT
