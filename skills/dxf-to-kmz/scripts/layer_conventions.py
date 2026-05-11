"""Regex-based layer-name → feature/style classification.

First match wins. Order matters. Adding a rule for a new drafter is a
one-line addition to RULES.

Returned dict keys:
    feature   - "polygon" | "route" | "point" | "label" | None
    subtype   - "boundary" | "aerial" | "underground" | "replace" | "markup"
                | "pole-new" | "vault" | "existing" | "station" | None
    publish   - bool: True for proposed/scope items, False for existing/unmapped
    folder    - "Permit Area" | "Proposed Route/Aerial" | ...
    style     - dict of color/width/dashed/etc. (see DEFAULT_STYLES)
    matched_rule - the regex pattern string that matched (for debugging)
"""
import re
from dataclasses import dataclass, field
from typing import Optional


# ---------- styles ----------

YELLOW_FILL = "4000ffff"   # KML aabbggrr: 25% alpha, yellow
YELLOW_LINE = "ff00ffff"   # KML aabbggrr: opaque yellow
RED_LINE    = "ff0000ff"   # KML aabbggrr: opaque red
ORANGE_LINE = "ff0080ff"
MAGENTA     = "ffff00ff"
GRAY        = "ff888888"
BLUE_FILL   = "ffff0000"   # KML aabbggrr: opaque blue (for vault icons)

DEFAULT_STYLES = {
    "polygon-boundary":   {"line_color": YELLOW_LINE, "fill_color": YELLOW_FILL, "width": 2},
    "route-aerial":       {"color": RED_LINE,    "width": 3, "dashed": True},
    "route-underground":  {"color": RED_LINE,    "width": 3, "dashed": False},
    "route-replace":      {"color": ORANGE_LINE, "width": 3, "dashed": True},
    "route-markup":       {"color": MAGENTA,     "width": 3, "dashed": True},
    "route-existing":     {"color": GRAY,        "width": 2, "dashed": False},
    "point-pole-new":     {"icon": "shaded_dot",  "color": RED_LINE},
    "point-vault":        {"icon": "shaded_dot",  "color": BLUE_FILL},
    "point-existing":     {"icon": "shaded_dot",  "color": GRAY},
    "label-station":      {"text_color": "ff444444", "scale": 0.8},
}

DEFAULT_FOLDERS = {
    "polygon-boundary":   "Permit Area",
    "route-aerial":       "Proposed Route/Aerial",
    "route-underground":  "Proposed Route/Underground",
    "route-replace":      "Proposed Route/Replace",
    "route-markup":       "Proposed Route/Markup",
    "route-existing":     "Existing Infrastructure",
    "point-pole-new":     "Proposed Infrastructure/Poles",
    "point-vault":        "Proposed Infrastructure/Vaults",
    "point-existing":     "Existing Infrastructure",
    "label-station":      "Stations & Labels",
}


# ---------- rules ----------

@dataclass
class Rule:
    pattern: str            # regex (case-insensitive)
    feature: Optional[str]
    subtype: Optional[str]
    publish: bool

    _compiled: re.Pattern = field(init=False, repr=False)

    def __post_init__(self):
        self._compiled = re.compile(self.pattern, re.IGNORECASE)

    def matches(self, layer_name: str) -> bool:
        return bool(self._compiled.search(layer_name))


# Order matters. First match wins.
RULES: list[Rule] = [
    # --- boundaries first (most specific keywords) ---
    Rule(r".*PERMIT.*BOUND.*",             "polygon", "boundary", True),
    Rule(r".*WORK.*AREA.*",                "polygon", "boundary", True),
    Rule(r".*ROW.*LIM.*|.*ROW_LIMITS",     "polygon", "boundary", True),
    # --- existing-infrastructure check BEFORE the route/point rules ---
    # (prevents EX_FIBER from being routed via the FIBER rules)
    # Word-boundary "EX" so we do NOT match TEXT (T-EX-T contains EX)
    Rule(r"(?:^|_)EX(?:_|$)|.*EXIST.*",      None,    "existing", False),
    # --- routes ---
    Rule(r".*FIBER.*AER.*|.*AERIAL.*|.*OVH.*",                "route", "aerial",      True),
    Rule(r".*FIBER.*UG.*|.*UNDERGRD.*|.*BORE.*|.*TRENCH.*",   "route", "underground", True),
    Rule(r".*REPLACE.*",                                      "route", "replace",     True),
    Rule(r".*MARKUP.*|.*REVISION.*|.*REDLINE.*",              "route", "markup",      True),
    # --- points ---
    Rule(r".*PROPOSED.*POLE.*|.*NEW.*POLE.*|^POLE",           "point", "pole-new",    True),
    Rule(r".*VAULT.*|.*HANDHOLE.*|.*\bHH\b.*",                "point", "vault",       True),
    # --- labels ---
    Rule(r".*STATION.*|.*\bSTA\b.*",                          "label", "station",     True),
]


def _resolve_existing(layer_name: str) -> tuple[str, str]:
    """For layers tagged 'existing' by name, infer feature type from later rules."""
    # Look at remaining rules to guess feature
    for rule in RULES:
        if rule.subtype == "existing":
            continue
        if rule.matches(layer_name):
            return rule.feature, "existing"
    # Fall back: if name has FIBER/CABLE -> route, POLE/VAULT -> point, else point
    n = layer_name.upper()
    if any(k in n for k in ("FIBER", "CABLE", "STRAND")):
        return "route", "existing"
    if any(k in n for k in ("POLE", "VAULT", "PED", "HH")):
        return "point", "existing"
    return "point", "existing"


def classify(layer_name: str) -> dict:
    """Apply RULES to a DXF layer name, return feature classification dict."""
    for rule in RULES:
        if rule.matches(layer_name):
            feature = rule.feature
            subtype = rule.subtype

            # Existing rule: feature is None in the rule; resolve it.
            if subtype == "existing":
                feature, subtype = _resolve_existing(layer_name)

            key = f"{feature}-{subtype}" if feature else None
            return {
                "feature": feature,
                "subtype": subtype,
                "publish": rule.publish,
                "folder": DEFAULT_FOLDERS.get(key, "Other"),
                "style": DEFAULT_STYLES.get(key, {}),
                "matched_rule": rule.pattern,
            }

    # Unmapped
    return {
        "feature": None,
        "subtype": None,
        "publish": False,
        "folder": None,
        "style": {},
        "matched_rule": None,
    }
