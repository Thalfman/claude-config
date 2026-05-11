"""End-to-end tests: inspect -> build -> assert KMZ structure."""

import zipfile
from pathlib import Path

import pytest

from scripts.inspect_kmz import inspect
from scripts.build_kmz import build


def _read_doc_kml(kmz: Path) -> str:
    with zipfile.ZipFile(kmz) as zf:
        return zf.read("doc.kml").decode("utf-8")


def test_e2e_civil3d_input_produces_family_folder_hierarchy(tmp_path, kmz_civil3d_style):
    out = tmp_path / "out.kmz"
    mapping = inspect(kmz_civil3d_style)
    build(kmz_civil3d_style, mapping, out)
    kml = _read_doc_kml(out)
    assert "<name>Permit Area</name>" in kml
    assert "<name>Proposed Route</name>" in kml
    assert "<name>Aerial</name>" in kml
    assert "<name>Underground</name>" in kml


def test_e2e_qgis_input_classifies_lowercase_attributes(tmp_path, kmz_qgis_style):
    out = tmp_path / "out.kmz"
    mapping = inspect(kmz_qgis_style)
    assert "construction_type" in mapping["attribute_roles"].values()
    build(kmz_qgis_style, mapping, out)
    kml = _read_doc_kml(out)
    assert "<name>Aerial</name>" in kml  # qgis "aerial" was classified


def test_e2e_handbuilt_input_infers_permit_area(tmp_path, kmz_handbuilt):
    out = tmp_path / "out.kmz"
    mapping = inspect(kmz_handbuilt)
    build(kmz_handbuilt, mapping, out)
    kml = _read_doc_kml(out)
    assert "Permit Area" in kml
    assert "inferred" in kml.lower()


def test_e2e_handbuilt_preserves_existing_description(tmp_path, kmz_handbuilt):
    out = tmp_path / "out.kmz"
    mapping = inspect(kmz_handbuilt)
    # Default mapping has preserve_existing_descriptions: True
    build(kmz_handbuilt, mapping, out)
    kml = _read_doc_kml(out)
    assert "Hand-traced from satellite imagery." in kml


def test_e2e_doc_description_is_minimal_provenance_only(tmp_path, kmz_civil3d_style):
    """Doc description carries Input filename + CRS, no skill commentary."""
    out = tmp_path / "out.kmz"
    mapping = inspect(kmz_civil3d_style)
    build(kmz_civil3d_style, mapping, out)
    kml = _read_doc_kml(out).lower()
    assert "input:" in kml
    assert "wgs84" in kml
    assert "civil 3d" not in kml
    assert "engineering layout" not in kml
    assert "not certified" not in kml


def test_e2e_idempotent_on_already_conformant_input(tmp_path, kmz_already_conformant):
    """Running on an already-conformant KMZ should not duplicate folders/features."""
    out1 = tmp_path / "out1.kmz"
    out2 = tmp_path / "out2.kmz"
    mapping = inspect(kmz_already_conformant)
    build(kmz_already_conformant, mapping, out1)

    # Re-run on the output. Should be stable.
    mapping2 = inspect(out1)
    build(out1, mapping2, out2)
    kml2 = _read_doc_kml(out2)

    # Should still have one Permit Area folder, not two.
    assert kml2.count("<name>Permit Area</name>") == 1


def test_e2e_per_placemark_override_pins_role(tmp_path, kmz_civil3d_style):
    """Editing override_role in mapping should pin the role through build."""
    out = tmp_path / "out.kmz"
    mapping = inspect(kmz_civil3d_style)
    # Pin the aerial route to underground via override.
    for pm in mapping["placemarks"]:
        if pm["id"] == "aerial_1":
            pm["override_role"] = "underground"
    build(kmz_civil3d_style, mapping, out)
    kml = _read_doc_kml(out)
    # The route should now be in Underground folder.
    assert "<name>Underground</name>" in kml


def test_e2e_publish_false_drops_placemark(tmp_path, kmz_civil3d_style):
    out = tmp_path / "out.kmz"
    mapping = inspect(kmz_civil3d_style)
    for pm in mapping["placemarks"]:
        if pm["id"] == "aerial_1":
            pm["publish"] = False
    build(kmz_civil3d_style, mapping, out)
    kml = _read_doc_kml(out)
    # The dropped feature's name should not appear.
    assert "Aerial Run 1" not in kml
