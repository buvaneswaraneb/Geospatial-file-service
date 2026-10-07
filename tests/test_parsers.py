import pytest

from app.core.exceptions import CorruptedFileError, MissingShapefileComponentsError
from app.services.kml_parser import KMLParserService
from app.services.shapefile_parser import ShapefileParserService


def test_read_valid_kml(sample_kml_file):
    gdf = KMLParserService.read_kml(sample_kml_file)
    assert not gdf.empty
    assert len(gdf) == 3
    # Check geometry types present
    geom_types = set(gdf.geometry.geom_type)
    assert "Polygon" in geom_types
    assert "LineString" in geom_types
    assert "Point" in geom_types


def test_kml_malformed_xml_raises_corrupted_error(tmp_path):
    bad_kml = tmp_path / "bad.kml"
    bad_kml.write_text("<kml><Document><unclosed_tag></kml>", encoding="utf-8")

    with pytest.raises(CorruptedFileError) as exc_info:
        KMLParserService.read_kml(bad_kml)
    assert "Malformed XML" in str(exc_info.value)


def test_read_valid_shapefile(sample_shapefile_zip):
    gdf = ShapefileParserService.read_shapefile(sample_shapefile_zip)
    assert not gdf.empty
    assert len(gdf) == 2


def test_missing_dbf_raises_missing_components_error(incomplete_shapefile_zip):
    with pytest.raises(MissingShapefileComponentsError) as exc_info:
        ShapefileParserService.read_shapefile(incomplete_shapefile_zip)
    assert ".dbf" in str(exc_info.value)
