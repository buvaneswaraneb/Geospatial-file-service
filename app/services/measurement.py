import json
import math
from typing import Any, Dict, List, Tuple
import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from shapely.geometry import mapping
from shapely.validation import make_valid

from app.core.logging import logger
from app.models.file_record import MeasurementType


def clean_properties(row_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Converts numpy and pandas data types to JSON-safe Python primitives."""
    clean = {}
    for key, val in row_dict.items():
        if key in ("geometry", "_layer"):
            continue
        if pd.isna(val) or val is None:
            clean[key] = None
        elif isinstance(val, (np.integer, int)):
            clean[key] = int(val)
        elif isinstance(val, (np.floating, float)):
            if math.isnan(val) or math.isinf(val):
                clean[key] = None
            else:
                clean[key] = float(val)
        elif isinstance(val, (pd.Timestamp, np.datetime64)):
            clean[key] = str(val)
        elif isinstance(val, (bytes, bytearray)):
            clean[key] = val.decode("utf-8", errors="replace")
        else:
            clean[key] = str(val)
    return clean


class MeasurementService:
    @classmethod
    def process_features_and_measurements(
        cls,
        gdf_original: gpd.GeoDataFrame,
        gdf_projected: gpd.GeoDataFrame,
        projected_crs_name: str,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Processes features, calculates area/length in projected CRS,
        and aggregates dataset summaries.
        """
        features_data: List[Dict[str, Any]] = []

        total_area_sq_m = 0.0
        total_length_m = 0.0
        polygons_measured = 0
        lines_measured = 0
        points_skipped = 0
        unsupported_count = 0

        for idx in range(len(gdf_original)):
            orig_row = gdf_original.iloc[idx]
            proj_row = gdf_projected.iloc[idx]

            orig_geom = orig_row.geometry
            proj_geom = proj_row.geometry

            # Feature properties
            props = clean_properties(orig_row.to_dict())

            # Determine feature identifier
            feat_identifier = (
                props.get("name")
                or props.get("Name")
                or props.get("id")
                or props.get("ID")
                or props.get("FID")
                or f"Feature_{idx}"
            )

            if orig_geom is None or orig_geom.is_empty:
                geom_type = "None"
                geom_geojson = None
                m_type = MeasurementType.UNSUPPORTED
                m_val = None
                m_units = "none"
                additional = {}
                notes = "Empty or missing geometry"
                unsupported_count += 1
            else:
                geom_type = orig_geom.geom_type
                try:
                    geom_geojson = json.dumps(mapping(orig_geom))
                except Exception:
                    geom_geojson = None

                # Attempt repair if geometry is not valid
                if not proj_geom.is_valid:
                    try:
                        proj_geom = make_valid(proj_geom)
                    except Exception as e:
                        logger.warning("Could not repair geometry index %d: %s", idx, e)

                if geom_type in ("Polygon", "MultiPolygon"):
                    m_type = MeasurementType.AREA
                    try:
                        area_m2 = float(proj_geom.area)
                        m_val = round(area_m2, 4)
                        m_units = "square_meters"
                        additional = {
                            "area_sq_km": round(area_m2 / 1_000_000.0, 6),
                            "area_hectares": round(area_m2 / 10_000.0, 4),
                        }
                        notes = "Area computed via metric projected CRS"
                        total_area_sq_m += area_m2
                        polygons_measured += 1
                    except Exception as e:
                        m_type = MeasurementType.UNSUPPORTED
                        m_val = None
                        m_units = "none"
                        additional = {}
                        notes = f"Failed to compute polygon area: {str(e)}"
                        unsupported_count += 1

                elif geom_type in ("LineString", "MultiLineString"):
                    m_type = MeasurementType.LENGTH
                    try:
                        len_m = float(proj_geom.length)
                        m_val = round(len_m, 4)
                        m_units = "meters"
                        additional = {
                            "length_km": round(len_m / 1_000.0, 6),
                        }
                        notes = "Length computed via metric projected CRS"
                        total_length_m += len_m
                        lines_measured += 1
                    except Exception as e:
                        m_type = MeasurementType.UNSUPPORTED
                        m_val = None
                        m_units = "none"
                        additional = {}
                        notes = f"Failed to compute line length: {str(e)}"
                        unsupported_count += 1

                elif geom_type in ("Point", "MultiPoint"):
                    m_type = MeasurementType.NONE
                    m_val = None
                    m_units = "none"
                    additional = {}
                    notes = "Point geometry: no measurement required"
                    points_skipped += 1

                else:
                    m_type = MeasurementType.UNSUPPORTED
                    m_val = None
                    m_units = "none"
                    additional = {}
                    notes = f"Unsupported geometry type '{geom_type}' for measurement calculation"
                    unsupported_count += 1

            features_data.append(
                {
                    "feature_index": idx,
                    "feature_identifier": str(feat_identifier),
                    "geometry_type": geom_type,
                    "geometry_geojson": geom_geojson,
                    "properties": props,
                    "measurement_type": m_type,
                    "measurement_value": m_val,
                    "measurement_units": m_units,
                    "additional_metrics": additional,
                    "projected_crs": projected_crs_name,
                    "notes": notes,
                }
            )

        summary = {
            "total_features": len(gdf_original),
            "polygons_measured": polygons_measured,
            "lines_measured": lines_measured,
            "points_skipped": points_skipped,
            "unsupported_geometries": unsupported_count,
            "total_area_sq_meters": round(total_area_sq_m, 4),
            "total_area_sq_km": round(total_area_sq_m / 1_000_000.0, 6),
            "total_area_hectares": round(total_area_sq_m / 10_000.0, 4),
            "total_length_meters": round(total_length_m, 4),
            "total_length_km": round(total_length_m / 1_000.0, 6),
        }

        return features_data, summary
