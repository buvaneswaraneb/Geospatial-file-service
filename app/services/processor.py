from pathlib import Path
from typing import Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.core.exceptions import GeospatialProcessingError
from app.core.logging import logger
from app.models.file_record import (
    FeatureRecord,
    FileRecord,
    FileStatus,
    FileType,
)
from app.services.crs_transformer import CRSTransformerService
from app.services.kml_parser import KMLParserService
from app.services.measurement import MeasurementService
from app.services.shapefile_parser import ShapefileParserService


class GeospatialProcessorService:
    @classmethod
    def process_and_persist_file(
        cls,
        db: Session,
        file_id: str,
        filename: str,
        file_path: Path,
        file_type: str,
        file_size: int,
    ) -> Tuple[FileRecord, Dict[str, Any]]:
        """
        Coordinates full file ingestion pipeline:
        1. Creates initial FileRecord (PENDING).
        2. Parses geospatial features (KML or Shapefile).
        3. Normalizes and reprojects coordinates to projected CRS.
        4. Calculates area/length measurements.
        5. Persists records to database and marks status COMPLETED.
        """
        # Create initial record
        file_record = FileRecord(
            id=file_id,
            filename=filename,
            file_type=file_type,
            file_size_bytes=file_size,
            storage_path=str(file_path),
            status=FileStatus.PROCESSING,
        )
        db.add(file_record)
        db.commit()
        db.refresh(file_record)

        try:
            # Step 1: Read dataset
            logger.info("Reading dataset '%s' (type: %s)", filename, file_type)
            if file_type == FileType.SHAPEFILE:
                gdf_original = ShapefileParserService.read_shapefile(file_path)
            elif file_type == FileType.KML:
                gdf_original = KMLParserService.read_kml(file_path)
            else:
                raise GeospatialProcessingError(f"Unsupported file type: {file_type}")

            # Step 2: Reproject to metric CRS
            logger.info("Reprojecting geometries for '%s'", filename)
            (
                gdf_projected,
                source_crs_name,
                projected_crs_name,
            ) = CRSTransformerService.project_geometries(gdf_original)

            # Step 3: Compute measurements
            logger.info(
                "Calculating measurements using projected CRS '%s'", projected_crs_name
            )
            features_data, summary = MeasurementService.process_features_and_measurements(
                gdf_original, gdf_projected, projected_crs_name
            )

            # Step 4: Persist features in bulk
            db_features = [
                FeatureRecord(file_id=file_id, **feat) for feat in features_data
            ]
            db.bulk_save_objects(db_features)

            # Update file record status
            file_record.feature_count = len(features_data)
            file_record.source_crs = source_crs_name
            file_record.status = FileStatus.COMPLETED
            db.commit()
            db.refresh(file_record)

            logger.info(
                "Successfully processed '%s': %d features extracted.",
                filename,
                len(features_data),
            )
            return file_record, summary

        except Exception as e:
            db.rollback()
            # Mark file record as FAILED with error message
            file_record.status = FileStatus.FAILED
            file_record.error_message = str(e)
            db.commit()
            logger.error("Processing failed for file %s: %s", filename, e)
            raise
