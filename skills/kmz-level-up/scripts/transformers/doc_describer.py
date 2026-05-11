"""doc_describer -- write the top-level Document description."""
from __future__ import annotations

from pathlib import Path

from scripts.kml_model import Document


def apply(doc: Document, derivation_log: dict[str, str]) -> None:
    """Set doc.description to minimal provenance only (input filename + CRS).

    No classification summary, derivation log, unmapped count, or quality-bar
    disclaimer — those are commentary. Deliverables stay clean.
    """
    parts = [
        f"<p><strong>Input:</strong> {Path(doc.source_path).name}</p>",
        f"<p><strong>CRS:</strong> WGS84 (EPSG:4326)</p>",
    ]
    doc.description = "\n".join(parts)
