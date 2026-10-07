import zipfile
from pathlib import Path
from typing import List
import geopandas as gpd

from app.core.exceptions import (
    CorruptedFileError,
    EmptyDatasetError,
    MissingShapefileComponentsError,
)
from app.core.logging import logger


class ShapefileParserService:
    REQUIRED_EXTENSIONS = {".shp", ".shx", ".dbf"}

    @classmethod
    def validate_zip_components(cls, zip_path: Path) -> List[str]:
        """
        Verifies that the ZIP file contains .shp, .shx, and .dbf components.
        Returns the list of found shapefile base stems.
        """
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                namelist = zf.namelist()
        except Exception as e:
            raise CorruptedFileError(
                message=f"Could not open zip archive: {str(e)}",
                details={"path": str(zip_path)},
            )

        found_extensions = {Path(name).suffix.lower() for name in namelist}
        missing = cls.REQUIRED_EXTENSIONS - found_extensions

        if missing:
            raise MissingShapefileComponentsError(
                message=(
                    "The uploaded zip archive must contain .shp, .shx, and .dbf files. "
                    f"Missing components: {sorted(list(missing))}"
                ),
                details={
                    "required": sorted(list(cls.REQUIRED_EXTENSIONS)),
                    "found": sorted(list(found_extensions)),
                    "missing": sorted(list(missing)),
                },
            )

        # Return files ending in .shp
        shp_files = [f for f in namelist if f.lower().endswith(".shp")]
        return shp_files

    @classmethod
    def read_shapefile(cls, zip_path: Path) -> gpd.GeoDataFrame:
        """Reads shapefile from zip archive into a GeoDataFrame."""
        cls.validate_zip_components(zip_path)

        uri = f"zip://{zip_path.resolve()}"
        try:
            gdf = gpd.read_file(uri, engine="pyogrio")
        except Exception as e:
            logger.warning("pyogrio read failed: %s. Attempting fallback.", e)
            try:
                gdf = gpd.read_file(uri)
            except Exception as e2:
                logger.error("Failed to read Shapefile: %s", e2)
                raise CorruptedFileError(
                    message=f"Failed to read Shapefile features: {str(e2)}",
                    details={"error": str(e2)},
                )

        if gdf.empty:
            raise EmptyDatasetError("Shapefile contains zero features.")

        return gdf
