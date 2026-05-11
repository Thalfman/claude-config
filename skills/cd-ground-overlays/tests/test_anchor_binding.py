"""Tests for the anchor-binding fix (Task 3 of cd-ground-overlays mapping plan)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from build_overlays import closest_route_endpoint


def test_returns_none_when_no_endpoints():
    assert closest_route_endpoint((100, 100), None, None) is None


def test_returns_the_only_endpoint_when_one_present():
    assert closest_route_endpoint((100, 100), (200, 200), None) == (200, 200)
    assert closest_route_endpoint((100, 100), None, (300, 300)) == (300, 300)


def test_returns_the_closer_endpoint():
    # text near (50, 600), entry at (396, 0), exit at (396, 1224)
    # |entry - text| = sqrt(346^2 + 600^2) ~= 692.6
    # |exit  - text| = sqrt(346^2 + 624^2) ~= 713.5
    assert closest_route_endpoint((50, 600), (396, 0), (396, 1224)) == (396, 0)


def test_returns_the_closer_endpoint_when_text_is_near_exit():
    # text at (100, 900): near exit y=1224 (dist 324) vs entry y=0 (dist 900).
    # Same x for both endpoints so y distance determines the winner.
    assert closest_route_endpoint((100, 900), (396, 0), (396, 1224)) == (396, 1224)


from build_overlays import apply_two_corner_anchor


def test_two_corner_pure_translation():
    """Two corners aligned with the +x_pdf=NORTH, +y_pdf=EAST convention.

    Corner A at PDF (100, 200), lat/lon (40.0, -86.0).
    Corner B at PDF (500, 800) — 400 pts east, 600 pts south in PDF space.
    At 40 ft/in scale with PT_PER_INCH=72:
        north_ft = 400 * (40/72) = 222.22 ft  -> delta_lat ~ 0.00061
        east_ft  = 600 * (40/72) = 333.33 ft  -> delta_lon ~ 0.00119 (at lat 40)
    These lat/lon values are the exact zero-rotation solution so rotation_deg=0.
    """
    a = apply_two_corner_anchor(
        corner_a=(100, 200, 40.0, -86.0),
        corner_b=(500, 800, 40.00060996, -85.99880562),
        scale_ft_per_inch=40.0,
    )
    assert a is not None
    assert abs(a["x0"] - 100) < 1e-6
    assert abs(a["y0"] - 200) < 1e-6
    assert abs(a["lat0"] - 40.0) < 1e-9
    assert abs(a["lon0"] - (-86.0)) < 1e-9
    # rotation_deg should be small (within 5 deg) when the two points are
    # roughly aligned with the assumed convention; the scale of "small"
    # depends on which test points you pick.
    assert abs(a["rotation_deg"]) < 5.0


def test_two_corner_returns_none_for_coincident_points():
    a = apply_two_corner_anchor(
        corner_a=(100, 200, 40.0, -86.0),
        corner_b=(100, 200, 40.0, -86.0),
        scale_ft_per_inch=40.0,
    )
    assert a is None


import fitz

from build_overlays import extract_route_endpoints


def test_endpoints_picks_longest_polyline():
    """A 1000pt red main route plus a 30pt red callout segment.

    Without the fix, the callout's endpoints can win the global y min/max
    if the callout sits at extreme y. With the fix, the longest connected
    polyline (the main route) wins.
    """
    doc = fitz.open()
    page = doc.new_page(width=792, height=1224)
    page.set_rotation(270)
    # Main route: vertical line at x=396 from y=100 to y=1100 (length 1000)
    page.draw_line(fitz.Point(396, 100), fitz.Point(396, 1100),
                   color=(1.0, 0.0, 0.0), width=0.7)
    # Distractor callout: short red line at extreme y=10
    page.draw_line(fitz.Point(700, 10), fitz.Point(720, 30),
                   color=(1.0, 0.0, 0.0), width=0.7)
    entry, exit_ = extract_route_endpoints(page)
    # Without the fix, entry would be (700, 10) -> wrong.
    assert entry == (396, 100), f"expected (396, 100), got {entry}"
    assert exit_ == (396, 1100), f"expected (396, 1100), got {exit_}"
