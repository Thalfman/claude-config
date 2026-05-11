# scripts/coord_parser.py
"""Parse coordinate strings into WGS84 decimal degrees.

Three text formats are handled (in this priority order):
  1. Hemisphere-suffixed decimal degrees:  "34.123456° N, 118.123456° W"
  2. LAT/LON labeled decimals:             "LAT: 34.123456 LON: -118.123456"
  3. Bare signed decimal pair:             "34.123456, -118.123456"

A unified `parse_coords` (added in Task 5) tries decimal degrees, then DMS,
then UTM, and reports which format won.
"""
import re
from typing import List, Optional, Tuple

from pyproj import Transformer


_DD_HEMI_RE = re.compile(
    r"(?P<lat>\d{1,2}\.\d{2,10})\s*°?\s*(?P<lat_h>[NS])"
    r"\s*[,;/]?\s*"
    r"(?P<lon>\d{1,3}\.\d{2,10})\s*°?\s*(?P<lon_h>[EW])",
    re.IGNORECASE,
)

_DD_LABELED_RE = re.compile(
    r"LAT(?:ITUDE)?\s*[:=]?\s*(?P<lat>[+-]?\d{1,2}\.\d{2,10})\s*°?\s*(?P<lat_h>[NS])?"
    r".{0,80}?"
    r"LON(?:GITUDE|G)?\s*[:=]?\s*(?P<lon>[+-]?\d{1,3}\.\d{2,10})\s*°?\s*(?P<lon_h>[EW])?",
    re.IGNORECASE | re.DOTALL,
)

_DD_SIGNED_RE = re.compile(
    r"(?<![A-Za-z\d.])"
    r"(?P<lat>[+-]?\d{1,2}\.\d{2,10})"
    r"\s*[,;]\s*"
    r"(?P<lon>[+-]?\d{1,3}\.\d{2,10})"
    r"(?![A-Za-z\d.])"
)


def parse_decimal_degrees(text: str) -> Optional[Tuple[float, float]]:
    """Return the first lat/lon pair found in decimal-degree form, else None."""
    for pattern in (_DD_HEMI_RE, _DD_LABELED_RE, _DD_SIGNED_RE):
        for m in pattern.finditer(text):
            lat = float(m.group("lat"))
            lon = float(m.group("lon"))
            groups = m.groupdict()
            if (groups.get("lat_h") or "").upper() == "S":
                lat = -abs(lat)
            if (groups.get("lon_h") or "").upper() == "W":
                lon = -abs(lon)
            if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                return (lat, lon)
    return None


_DMS_RE = re.compile(
    r"(?P<lat_d>\d{1,2})\s*[°d\-]\s*(?P<lat_m>\d{1,2})\s*[′'m\-]\s*(?P<lat_s>\d{1,2}(?:\.\d+)?)\s*[″\"s]?\s*(?P<lat_h>[NS])"
    r"\s*[,;/\s]+\s*"
    r"(?P<lon_d>\d{1,3})\s*[°d\-]\s*(?P<lon_m>\d{1,2})\s*[′'m\-]\s*(?P<lon_s>\d{1,2}(?:\.\d+)?)\s*[″\"s]?\s*(?P<lon_h>[EW])",
    re.IGNORECASE,
)


def _dms_to_decimal(d: str, m: str, s: str, hemi: str) -> float:
    decimal = float(d) + float(m) / 60.0 + float(s) / 3600.0
    if hemi.upper() in ("S", "W"):
        decimal = -decimal
    return decimal


def parse_dms(text: str) -> Optional[Tuple[float, float]]:
    """Return the first lat/lon pair found in DMS form, else None."""
    m = _DMS_RE.search(text)
    if not m:
        return None
    lat = _dms_to_decimal(m.group("lat_d"), m.group("lat_m"), m.group("lat_s"), m.group("lat_h"))
    lon = _dms_to_decimal(m.group("lon_d"), m.group("lon_m"), m.group("lon_s"), m.group("lon_h"))
    if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
        return (lat, lon)
    return None


_UTM_RE = re.compile(
    r"(?:ZONE|UTM)\s*(?P<zone>\d{1,2})\s*(?P<band>[A-HJ-NP-Z])"
    r"[,\s]*"
    r"(?P<easting>\d{6,7})\s*E?"
    r"[,\s]+"
    r"(?P<northing>\d{6,7})\s*N?",
    re.IGNORECASE,
)


def parse_utm(text: str) -> Optional[Tuple[float, float]]:
    """Return the first lat/lon pair found in UTM form, else None.

    Band letters N..X are northern hemisphere, C..M are southern.
    """
    m = _UTM_RE.search(text)
    if not m:
        return None
    zone = int(m.group("zone"))
    band = m.group("band").upper()
    easting = float(m.group("easting"))
    northing = float(m.group("northing"))

    is_north = band >= "N"
    epsg = 32600 + zone if is_north else 32700 + zone
    transformer = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
    lon, lat = transformer.transform(easting, northing)
    if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
        return (lat, lon)
    return None


def parse_coords(text: str) -> Optional[Tuple[float, float, str]]:
    """Try decimal degrees, then DMS, then UTM. Return (lat, lon, format) or None.

    `format` is one of: "decimal_degrees", "dms", "utm".
    """
    dd = parse_decimal_degrees(text)
    if dd is not None:
        return (dd[0], dd[1], "decimal_degrees")
    dms = parse_dms(text)
    if dms is not None:
        return (dms[0], dms[1], "dms")
    utm = parse_utm(text)
    if utm is not None:
        return (utm[0], utm[1], "utm")
    return None


def find_all_coords(text: str) -> List[Tuple[float, float, str]]:
    """Find every coord-pair occurrence in text across all three formats.

    Used by sheet_extractor to detect 1+ stamps on a plan sheet so start/end
    coords can be assigned independently.
    """
    results: List[Tuple[float, float, str]] = []

    for pattern in (_DD_HEMI_RE, _DD_LABELED_RE, _DD_SIGNED_RE):
        for m in pattern.finditer(text):
            lat = float(m.group("lat"))
            lon = float(m.group("lon"))
            groups = m.groupdict()
            if (groups.get("lat_h") or "").upper() == "S":
                lat = -abs(lat)
            if (groups.get("lon_h") or "").upper() == "W":
                lon = -abs(lon)
            if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                results.append((lat, lon, "decimal_degrees"))

    for m in _DMS_RE.finditer(text):
        lat = _dms_to_decimal(m.group("lat_d"), m.group("lat_m"), m.group("lat_s"), m.group("lat_h"))
        lon = _dms_to_decimal(m.group("lon_d"), m.group("lon_m"), m.group("lon_s"), m.group("lon_h"))
        if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
            results.append((lat, lon, "dms"))

    for m in _UTM_RE.finditer(text):
        zone = int(m.group("zone"))
        band = m.group("band").upper()
        easting = float(m.group("easting"))
        northing = float(m.group("northing"))
        is_north = band >= "N"
        epsg = 32600 + zone if is_north else 32700 + zone
        transformer = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
        lon, lat = transformer.transform(easting, northing)
        if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
            results.append((lat, lon, "utm"))

    return results
