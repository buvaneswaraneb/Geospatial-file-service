import geopandas as gpd
from shapely.geometry import LineString, Polygon

from app.services.crs_transformer import CRSTransformerService


def test_normalize_crs_geographic():
    poly = Polygon([(77.59, 12.97), (77.60, 12.97), (77.60, 12.98), (77.59, 12.98), (77.59, 12.97)])
    gdf = gpd.GeoDataFrame([{"geometry": poly}], crs="EPSG:4326")

    gdf_norm, source_crs = CRSTransformerService.normalize_crs(gdf)
    assert source_crs == "EPSG:4326"
    assert gdf_norm.crs.to_epsg() == 4326


def test_normalize_crs_fallback_when_none():
    poly = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
    gdf = gpd.GeoDataFrame([{"geometry": poly}], crs=None)

    gdf_norm, source_crs = CRSTransformerService.normalize_crs(gdf)
    assert "EPSG:4326" in source_crs
    assert gdf_norm.crs is not None


def test_project_geometries_to_utm():
    # 0.01 degree by 0.01 degree polygon near Bangalore
    poly = Polygon([(77.59, 12.97), (77.60, 12.97), (77.60, 12.98), (77.59, 12.98), (77.59, 12.97)])
    gdf = gpd.GeoDataFrame([{"geometry": poly}], crs="EPSG:4326")

    gdf_proj, source_crs, proj_crs = CRSTransformerService.project_geometries(gdf)

    assert source_crs == "EPSG:4326"
    assert "EPSG:32643" in proj_crs or "32643" in proj_crs
    # Calculated area must be non-zero and in meters (around 1.2 square kilometers = 1,200,000 m²)
    area = gdf_proj.geometry.area.iloc[0]
    assert 1_100_000 < area < 1_300_000


def test_project_linestring_meters():
    line = LineString([(77.59, 12.97), (77.60, 12.98)])
    gdf = gpd.GeoDataFrame([{"geometry": line}], crs="EPSG:4326")

    gdf_proj, source_crs, proj_crs = CRSTransformerService.project_geometries(gdf)
    length = gdf_proj.geometry.length.iloc[0]

    # Diagonal distance of ~0.01 deg lon & 0.01 deg lat is ~1,500 meters, definitely not 0.014
    assert 1_300 < length < 1_800
