import xml.etree.ElementTree as ET
from pathlib import Path
import geopandas as gpd
import pandas as pd
import pyogrio

from app.core.exceptions import CorruptedFileError, EmptyDatasetError
from app.core.logging import logger


class KMLParserService:
    @classmethod
    def validate_kml_xml(cls, kml_path: Path) -> None:
        """Verifies that the KML file contains syntactically valid XML."""
        try:
            ET.parse(kml_path)
        except ET.ParseError as e:
            raise CorruptedFileError(
                message=f"Malformed XML in KML file: {str(e)}",
                details={"line": e.position[0] if hasattr(e, "position") else None},
            )
        except Exception as e:
            raise CorruptedFileError(
                message=f"Could not parse KML file: {str(e)}",
                details={"error": str(e)},
            )

    @classmethod
    def read_kml(cls, kml_path: Path) -> gpd.GeoDataFrame:
        """
        Reads KML file into a GeoDataFrame, supporting multi-layer KML files.
        """
        cls.validate_kml_xml(kml_path)

        layers_to_read = []
        try:
            layers_info = pyogrio.list_layers(kml_path)
            for row in layers_info:
                if hasattr(row, "__getitem__") and len(row) > 0:
                    layers_to_read.append(str(row[0]))
                else:
                    layers_to_read.append(str(row))
        except Exception as e:
            logger.info("Could not list layers with pyogrio: %s. Reading default layer.", e)

        gdfs = []
        if layers_to_read:
            for layer_name in layers_to_read:
                try:
                    layer_gdf = gpd.read_file(kml_path, layer=str(layer_name), engine="pyogrio")
                    if not layer_gdf.empty:
                        layer_gdf["_layer"] = str(layer_name)
                        gdfs.append(layer_gdf)
                except Exception as e:
                    logger.warning("Could not read KML layer '%s': %s", layer_name, e)
        else:
            try:
                default_gdf = gpd.read_file(kml_path, engine="pyogrio")
                if not default_gdf.empty:
                    gdfs.append(default_gdf)
            except Exception as e:
                logger.warning("Failed default pyogrio read: %s. Trying fallback.", e)
                try:
                    default_gdf = gpd.read_file(kml_path)
                    if not default_gdf.empty:
                        gdfs.append(default_gdf)
                except Exception as e2:
                    raise CorruptedFileError(
                        message=f"Failed to read KML file: {str(e2)}",
                        details={"error": str(e2)},
                    )

        if not gdfs:
            raise EmptyDatasetError("KML file contains zero features or valid layers.")

        if len(gdfs) == 1:
            combined_gdf = gdfs[0]
        else:
            # Concatenate multiple layers
            combined_gdf = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True))
            # Retain crs from first valid
            combined_gdf.crs = gdfs[0].crs

        if combined_gdf.empty:
            raise EmptyDatasetError("KML file contains zero features.")

        return combined_gdf
