"""First-match-wins regex rules for attribute name -> role and attribute
value -> StyleRole. Existing-infrastructure check fires before route
classification, mirroring dxf-to-kmz/layer_conventions.py.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from scripts.kml_model import StyleRole, LineStringFeature, PointFeature, PolygonFeature


@dataclass(frozen=True)
class NameRule:
    pattern: re.Pattern
    role: str  # "construction_type" | "chainage" | "span_length" | "owner" | "sheet_id" | "existing_flag"


@dataclass(frozen=True)
class ValueRule:
    pattern: re.Pattern
    style_role: StyleRole


# Order matters: first match wins.
NAME_RULES: list[NameRule] = [
    NameRule(re.compile(r"const.*type|mat.*type|method", re.I), "construction_type"),
    NameRule(re.compile(r"\btype\b", re.I), "construction_type"),
    NameRule(re.compile(r"chain|station|\bsta\b", re.I), "chainage"),
    NameRule(re.compile(r"span|length|\bft\b", re.I), "span_length"),
    NameRule(re.compile(r"owner|\bprm\b|entity", re.I), "owner"),
    NameRule(re.compile(r"sheet|(?<![a-zA-Z])sht(?![a-zA-Z])|(?<![a-zA-Z])fid(?![a-zA-Z])", re.I), "sheet_id"),
    NameRule(re.compile(r"existing|^ex$", re.I), "existing_flag"),
]


CONSTRUCTION_VALUE_RULES: list[ValueRule] = [
    ValueRule(re.compile(r"aerial|\bovh\b|overhead|overlash|strand", re.I), StyleRole.AERIAL),
    ValueRule(re.compile(r"underground|\bug\b|bore|trench|directional", re.I), StyleRole.UNDERGROUND),
    ValueRule(re.compile(r"replace|rplc", re.I), StyleRole.REPLACE),
    ValueRule(re.compile(r"markup|revision|redline|\bred\b", re.I), StyleRole.MARKUP),
]


# Word-boundary EX prefix: matches "EX_*" or "*_EX_*" but not "TEXT".
_EX_NAME_PATTERN = re.compile(r"(?:^|_)EX(?:_|$)", re.I)


def classify_attribute_name(key: str) -> str | None:
    """Return the role for an attribute name, or None if unmatched."""
    for rule in NAME_RULES:
        if rule.pattern.search(key):
            return rule.role
    return None


def classify_construction_value(value: str) -> StyleRole:
    """Map a construction-type attribute value to a StyleRole."""
    for rule in CONSTRUCTION_VALUE_RULES:
        if rule.pattern.search(value):
            return rule.style_role
    return StyleRole.UNMAPPED


def classify_feature(
    feature: LineStringFeature | PointFeature | PolygonFeature,
    role_map: dict[str, str],
) -> StyleRole:
    """Classify a feature into a StyleRole.

    Existing-infrastructure check fires first:
      - placemark name matches `EX_*` (word-boundary) -> EXISTING
      - any attribute mapped to `existing_flag` is truthy -> EXISTING

    Then construction-type check:
      - find the attribute key whose role is `construction_type`
      - run its value through CONSTRUCTION_VALUE_RULES

    Otherwise UNMAPPED.
    """
    # Existing check by name
    if _EX_NAME_PATTERN.search(feature.name or ""):
        return StyleRole.EXISTING

    # Existing check by attribute: explicit role_map mapping first, then
    # fall back to scanning attribute keys with classify_attribute_name so
    # an attribute like `existing=True` is detected even when the user's
    # role_map only contains primary mappings (e.g. construction_type).
    for key, role in role_map.items():
        if role == "existing_flag" and feature.attributes.get(key):
            return StyleRole.EXISTING

    for key, value in feature.attributes.items():
        if key in role_map:
            continue  # already considered via role_map above
        if classify_attribute_name(key) == "existing_flag" and value:
            return StyleRole.EXISTING

    # Construction-type lookup
    for key, role in role_map.items():
        if role == "construction_type":
            value = feature.attributes.get(key)
            if value is not None:
                return classify_construction_value(str(value))

    return StyleRole.UNMAPPED
