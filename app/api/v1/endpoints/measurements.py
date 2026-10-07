from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_file_or_404
from app.db.session import get_db
from app.models.file_record import FeatureRecord, FileRecord, MeasurementType
from app.schemas.measurement import (
    FileMeasurementsResponse,
    MeasurementItemResponse,
    MeasurementSummary,
)

router = APIRouter(prefix="/files", tags=["Measurements"])


@router.get(
    "/{file_id}/measurements/",
    response_model=FileMeasurementsResponse,
    summary="Get calculated measurements for file features",
    description="Returns area for Polygons/MultiPolygons, length for LineStrings/MultiLineStrings, skips Points gracefully, and provides comprehensive aggregate metrics.",
)
def get_file_measurements(
    limit: int = Query(100, ge=1, le=1000, description="Number of measurement records to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    file_record: FileRecord = Depends(get_file_or_404),
    db: Session = Depends(get_db),
) -> FileMeasurementsResponse:
    # Query all features for this file to compute full dataset summary
    all_features = (
        db.query(FeatureRecord)
        .filter(FeatureRecord.file_id == file_record.id)
        .order_by(FeatureRecord.feature_index)
        .all()
    )

    total_features = len(all_features)
    polygons_measured = 0
    lines_measured = 0
    points_skipped = 0
    unsupported_count = 0
    total_area_sq_m = 0.0
    total_length_m = 0.0

    for f in all_features:
        if f.measurement_type == MeasurementType.AREA:
            polygons_measured += 1
            if f.measurement_value is not None:
                total_area_sq_m += f.measurement_value
        elif f.measurement_type == MeasurementType.LENGTH:
            lines_measured += 1
            if f.measurement_value is not None:
                total_length_m += f.measurement_value
        elif f.measurement_type == MeasurementType.NONE:
            points_skipped += 1
        else:
            unsupported_count += 1

    summary = MeasurementSummary(
        total_features=total_features,
        polygons_measured=polygons_measured,
        lines_measured=lines_measured,
        points_skipped=points_skipped,
        unsupported_geometries=unsupported_count,
        total_area_sq_meters=round(total_area_sq_m, 4),
        total_area_sq_km=round(total_area_sq_m / 1_000_000.0, 6),
        total_area_hectares=round(total_area_sq_m / 10_000.0, 4),
        total_length_meters=round(total_length_m, 4),
        total_length_km=round(total_length_m / 1_000.0, 6),
    )

    # Paginate feature measurements
    paginated_features = all_features[offset : offset + limit]
    measurement_items = []
    for f in paginated_features:
        measurement_items.append(
            MeasurementItemResponse(
                feature_index=f.feature_index,
                feature_identifier=f.feature_identifier,
                geometry_type=f.geometry_type,
                measurement_type=f.measurement_type,
                value=f.measurement_value,
                units=f.measurement_units,
                additional_metrics=f.additional_metrics or {},
                projected_crs=f.projected_crs,
                notes=f.notes,
                properties=f.properties or {},
            )
        )

    return FileMeasurementsResponse(
        file_id=file_record.id,
        filename=file_record.filename,
        source_crs=file_record.source_crs,
        summary=summary,
        measurements=measurement_items,
        total=total_features,
        limit=limit,
        offset=offset,
    )
