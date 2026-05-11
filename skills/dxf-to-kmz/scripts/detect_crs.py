"""CRS detection for DXF files. Three tiers, fall through automatically."""
import json
from pathlib import Path
from typing import Optional

import ezdxf
from pyproj import CRS
from pyproj.exceptions import CRSError


DEFAULT_REGIONAL_DEFAULTS = Path(__file__).parent / "dxf_crs_defaults.json"


def _wkt_to_epsg(wkt: str) -> Optional[dict]:
    """Parse WKT, attempt to identify a known EPSG code. Returns dict or None."""
    try:
        crs = CRS.from_wkt(wkt)
    except CRSError:
        return None

    epsg = crs.to_epsg()
    label = crs.name
    if epsg:
        return {"epsg": f"EPSG:{epsg}", "label": label, "wkt": wkt}
    # CRS has no canonical EPSG (rare for State Plane) - keep WKT
    return {"epsg": None, "label": label, "wkt": wkt}


def detect_from_prj_sidecar(dxf_path: Path) -> Optional[dict]:
    """Look for {dxf_basename}.prj next to the DXF; parse as ESRI WKT."""
    prj = dxf_path.with_suffix(".prj")
    if not prj.exists():
        return None
    wkt = prj.read_text().strip()
    parsed = _wkt_to_epsg(wkt)
    if parsed is None:
        return None
    return {**parsed, "source": "prj_sidecar", "confidence": "HIGH"}


def detect_from_geodata(dxf_path: Path) -> Optional[dict]:
    """Read GEODATA xrecord from modelspace via ezdxf."""
    try:
        doc = ezdxf.readfile(str(dxf_path))
        msp = doc.modelspace()
        geodata = msp.get_geodata()
    except (IOError, ezdxf.DXFError):
        return None

    if geodata is None:
        return None

    wkt = geodata.coordinate_system_definition
    if not wkt:
        return None

    parsed = _wkt_to_epsg(wkt)
    if parsed is None:
        return None
    return {**parsed, "source": "geodata_xrecord", "confidence": "HIGH"}


def detect_from_regional_default(dxf_path: Path,
                                  defaults_path: Path = DEFAULT_REGIONAL_DEFAULTS) -> Optional[dict]:
    """Substring-match DXF filename against keys in defaults JSON."""
    if not defaults_path.exists():
        return None
    try:
        defaults = json.loads(defaults_path.read_text())
    except json.JSONDecodeError:
        return None
    # Normalize separators so a key like "Indiana-West" matches a filename
    # like "PERU_INDIANA_WEST_FIBER.dxf" (hyphens vs underscores).
    name = dxf_path.stem.upper().replace("-", "_")

    for region, epsg in sorted(defaults.items(), key=lambda kv: -len(kv[0])):
        if region.upper().replace("-", "_") in name:
            label = CRS(epsg).name if epsg else region
            return {
                "epsg": epsg,
                "label": label,
                "source": f"regional_default:{region}",
                "confidence": "MEDIUM",
                "matched_region": region,
            }
    return None


def detect_crs(dxf_path: Path,
               defaults_path: Path = DEFAULT_REGIONAL_DEFAULTS) -> dict:
    """Run tiers 1, 2, then return Tier 3 manual stub if both fail."""
    # Tier 1
    for fn in (detect_from_prj_sidecar, detect_from_geodata):
        result = fn(dxf_path)
        if result is not None:
            return {**result, "tier": 1}

    # Tier 2
    result = detect_from_regional_default(dxf_path, defaults_path)
    if result is not None:
        return {**result, "tier": 2}

    # Tier 3: caller must run build_anchors.py
    return {
        "tier": 3,
        "epsg": None,
        "label": None,
        "source": "manual_anchors_required",
        "confidence": "MANUAL",
    }
