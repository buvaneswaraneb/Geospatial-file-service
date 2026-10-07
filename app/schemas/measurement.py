from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MeasurementItemResponse(BaseModel):
    feature_index: int = Field(..., description="0-based feature index in the dataset")
    feature_identifier: Optional[str] = Field(None, description="Feature ID or Placemark Name")
    geometry_type: str = Field(..., description="Geometry type, e.g. Polygon, LineString, Point")
    measurement_type: str = Field(..., description="AREA, LENGTH, NONE, or UNSUPPORTED")
    value: Optional[float] = Field(None, description="Primary calculated measurement value")
    units: Optional[str] = Field(None, description="Measurement units (square_meters, meters, none)")
    additional_metrics: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Formatted metrics (e.g. sq_km, hectares, km)",
    )
    projected_crs: Optional[str] = Field(
        None,
        description="Target projected coordinate reference system used for metric calculation",
    )
    notes: Optional[str] = Field(
        None,
        description="Informational note for point geometries or unmeasured types",
    )
    properties: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Original attributes/properties extracted from the feature",
    )

    model_config = {"from_attributes": True}


class MeasurementSummary(BaseModel):
    total_features: int = Field(..., description="Total features in file")
    polygons_measured: int = Field(..., description="Count of polygons/multipolygons measured")
    lines_measured: int = Field(..., description="Count of linestrings/multilinestrings measured")
    points_skipped: int = Field(..., description="Count of points/multipoints skipped gracefully")
    unsupported_geometries: int = Field(..., description="Count of unsupported geometries")
    total_area_sq_meters: float = Field(..., description="Sum of all polygon areas in square meters")
    total_area_sq_km: float = Field(..., description="Sum of all polygon areas in square kilometers")
    total_area_hectares: float = Field(..., description="Sum of all polygon areas in hectares")
    total_length_meters: float = Field(..., description="Sum of all linestring lengths in meters")
    total_length_km: float = Field(..., description="Sum of all linestring lengths in kilometers")


class FileMeasurementsResponse(BaseModel):
    file_id: str
    filename: str
    source_crs: Optional[str] = None
    summary: MeasurementSummary
    measurements: List[MeasurementItemResponse]
    total: int
    limit: int
    offset: int


class FeatureDetailResponse(BaseModel):
    feature_index: int
    feature_identifier: Optional[str]
    geometry_type: str
    geometry_geojson: Optional[Dict[str, Any]]
    properties: Optional[Dict[str, Any]]
    measurement_type: str
    measurement_value: Optional[float]
    measurement_units: Optional[str]
    additional_metrics: Optional[Dict[str, Any]]
    projected_crs: Optional[str]
    notes: Optional[str]

    model_config = {"from_attributes": True}
