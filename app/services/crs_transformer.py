from typing import Tuple
import geopandas as gpd
import pyproj

from app.config import settings
from app.core.exceptions import CRSTransformationError
from app.core.logging import logger


class CRSTransformerService:
    @classmethod
    def normalize_crs(cls, gdf: gpd.GeoDataFrame) -> Tuple[gpd.GeoDataFrame, str]:
        """
        Ensures the dataset has a recognized CRS.
        If missing, assigns DEFAULT_FALLBACK_CRS (EPSG:4326).
        """
        if gdf.crs is None:
            logger.warning(
                "Source dataset has no CRS specified. Defaulting to fallback CRS %s.",
                settings.DEFAULT_FALLBACK_CRS,
            )
            gdf = gdf.set_crs(settings.DEFAULT_FALLBACK_CRS)
            source_crs_str = f"{settings.DEFAULT_FALLBACK_CRS} (assumed fallback)"
        else:
            try:
                epsg = gdf.crs.to_epsg()
                source_crs_str = f"EPSG:{epsg}" if epsg else gdf.crs.to_string()
            except Exception:
                source_crs_str = gdf.crs.to_string()

        return gdf, source_crs_str

    @classmethod
    def get_optimal_projected_crs(cls, gdf: gpd.GeoDataFrame) -> pyproj.CRS:
        """
        Determines the most accurate projected CRS for metric calculations.
        If already projected, returns the existing CRS.
        If geographic (degrees), computes local UTM or Lambert Azimuthal Equal Area (LAEA).
        """
        if gdf.empty:
            return pyproj.CRS.from_user_input(settings.DEFAULT_FALLBACK_CRS)

        # If already projected (units are linear/meters)
        if gdf.crs and gdf.crs.is_projected:
            return gdf.crs

        # Strategy 1: Attempt local UTM projection estimation
        try:
            utm_crs = gdf.estimate_utm_crs()
            if utm_crs is not None:
                return utm_crs
        except Exception as e:
            logger.info("Could not determine UTM CRS via estimate_utm_crs: %s. Using LAEA fallback.", e)

        # Strategy 2: Fallback to custom Lambert Azimuthal Equal Area (LAEA) projection
        # LAEA provides true equal-area preservation globally centered on the dataset centroid.
        try:
            minx, miny, maxx, maxy = gdf.total_bounds
            lon_0 = (minx + maxx) / 2.0
            lat_0 = (miny + maxy) / 2.0
            laea_proj_string = (
                f"+proj=laea +lat_0={lat_0:.6f} +lon_0={lon_0:.6f} "
                f"+datum=WGS84 +units=m +no_defs"
            )
            return pyproj.CRS.from_proj4(laea_proj_string)
        except Exception as e:
            logger.error("Failed to construct LAEA projection: %s", e)
            raise CRSTransformationError(
                message=f"Failed to determine appropriate projected CRS: {str(e)}",
                details={"bounds": list(gdf.total_bounds) if not gdf.empty else []},
            )

    @classmethod
    def project_geometries(
        cls, gdf: gpd.GeoDataFrame
    ) -> Tuple[gpd.GeoDataFrame, str, str]:
        """
        Normalizes dataset CRS, finds optimal projected CRS, and returns:
        (gdf_projected, source_crs_name, projected_crs_name)
        """
        gdf, source_crs_name = cls.normalize_crs(gdf)

        if gdf.empty:
            return gdf, source_crs_name, source_crs_name

        target_crs = cls.get_optimal_projected_crs(gdf)

        try:
            gdf_projected = gdf.to_crs(target_crs)
            target_epsg = target_crs.to_epsg()
            projected_crs_name = (
                f"EPSG:{target_epsg}" if target_epsg else target_crs.to_string()
            )
            return gdf_projected, source_crs_name, projected_crs_name
        except Exception as e:
            logger.error("Error transforming geometries to projected CRS: %s", e)
            raise CRSTransformationError(
                message=f"Coordinate transformation failed: {str(e)}",
                details={"source_crs": source_crs_name, "target_crs": str(target_crs)},
            )
