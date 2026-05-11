"""Internal normalized representation of KML data.

Pure data definitions. No I/O, no parsing, no transforming. Other modules
import these dataclasses + the StyleRole enum to define their type contracts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StyleRole(str, Enum):
    AERIAL = "aerial"
    UNDERGROUND = "underground"
    REPLACE = "replace"
    MARKUP = "markup"
    EXISTING = "existing"
    BOUNDARY = "boundary"
    POLE = "pole"
    VAULT = "vault"
    STATION = "station"
    UNMAPPED = "unmapped"


@dataclass
class LineStringFeature:
    id: str
    name: str
    attributes: dict[str, Any]
    coordinates: list[tuple[float, float]]
    style_role: StyleRole = StyleRole.UNMAPPED
    folder_path: list[str] = field(default_factory=list)
    description_html: str = ""


@dataclass
class PointFeature:
    id: str
    name: str
    attributes: dict[str, Any]
    coordinates: tuple[float, float]
    style_role: StyleRole = StyleRole.UNMAPPED
    folder_path: list[str] = field(default_factory=list)
    description_html: str = ""


@dataclass
class PolygonFeature:
    id: str
    name: str
    attributes: dict[str, Any]
    outer_ring: list[tuple[float, float]]
    inner_rings: list[list[tuple[float, float]]] = field(default_factory=list)
    # Optional additional polygon parts merged into a single placemark, each
    # being (outer_ring, inner_rings). Used by the polygon-merger transformer
    # when collapsing N polygons-per-PRM into one MultiGeometry placemark.
    extra_parts: list[
        tuple[
            list[tuple[float, float]],
            list[list[tuple[float, float]]],
        ]
    ] = field(default_factory=list)
    style_role: StyleRole = StyleRole.UNMAPPED
    folder_path: list[str] = field(default_factory=list)
    description_html: str = ""
    # Per-feature style override, populated by style_restyler when
    # polygon_handling.style_by maps an attribute value to a custom style.
    # Keys: line, fill, line_width.
    style_override: dict | None = None


@dataclass
class Document:
    source_path: str
    name: str
    description: str
    linestrings: list[LineStringFeature] = field(default_factory=list)
    points: list[PointFeature] = field(default_factory=list)
    polygons: list[PolygonFeature] = field(default_factory=list)

    def all_features(self):
        yield from self.linestrings
        yield from self.points
        yield from self.polygons
