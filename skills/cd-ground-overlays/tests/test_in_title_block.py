"""Tests for the title-block exclusion fix."""
import sys
from pathlib import Path

# Allow the test to import build_overlays without packaging the script.
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from build_overlays import in_title_block


def test_text_in_unrotated_bottom_left_is_in_title_block():
    """Title block displays at rendered BR -> unrotated BL (small x, large y).

    For a 270-rotated 792x1224 portrait page, the title block region in
    UNROTATED coords is x_orig small AND y_orig large.
    """
    # MediaBox dimensions for a portrait page stored 792x1224
    page_w_unrotated, page_h_unrotated = 792, 1224
    # A point well inside the title-block region (small x, large y)
    assert in_title_block(50, 1100, page_w_unrotated, page_h_unrotated) is True


def test_text_in_unrotated_top_right_is_not_in_title_block():
    """The opposite corner — large x, small y — is NOT the title block."""
    page_w_unrotated, page_h_unrotated = 792, 1224
    assert in_title_block(700, 100, page_w_unrotated, page_h_unrotated) is False


def test_text_at_unrotated_top_left_is_not_in_title_block():
    """Top-left of unrotated == display TL (or near it after rotation): not the title block."""
    page_w_unrotated, page_h_unrotated = 792, 1224
    assert in_title_block(50, 100, page_w_unrotated, page_h_unrotated) is False
