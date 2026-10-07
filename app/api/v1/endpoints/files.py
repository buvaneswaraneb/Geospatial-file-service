import json
from typing import Optional
from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_file_or_404
from app.db.session import get_db
from app.models.file_record import FeatureRecord, FileRecord
from app.schemas.file import FileInformationResponse, FileListResponse
from app.schemas.measurement import FeatureDetailResponse
from app.services.file_storage import FileStorageService
from app.services.processor import GeospatialProcessorService

router = APIRouter(prefix="/files", tags=["Files"])


@router.post(
    "/",
    response_model=FileInformationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and process a geospatial file",
    description="Accepts a `.kml` file or a `.zip` archive containing an ESRI Shapefile (.shp, .shx, .dbf). Extracts features and computes measurements.",
)
async def upload_geospatial_file(
    file: UploadFile = File(..., description="Geospatial file (.kml or .zip)"),
    db: Session = Depends(get_db),
) -> FileInformationResponse:
    # 1. Save uploaded file to secure storage
    file_id, file_path, file_type, file_size = await FileStorageService.save_upload_file(file)

    # 2. Ingest, process, reproject, calculate measurements, and persist
    file_record, _ = GeospatialProcessorService.process_and_persist_file(
        db=db,
        file_id=file_id,
        filename=file.filename,
        file_path=file_path,
        file_type=file_type,
        file_size=file_size,
    )

    return FileInformationResponse.model_validate(file_record)


@router.get(
    "/{file_id}/",
    response_model=FileInformationResponse,
    summary="Get file information",
    description="Returns metadata, feature count, detected CRS, and processing status for an uploaded file.",
)
def get_file_information(
    file_record: FileRecord = Depends(get_file_or_404),
) -> FileInformationResponse:
    return FileInformationResponse.model_validate(file_record)


@router.get(
    "/",
    response_model=FileListResponse,
    summary="List uploaded files",
    description="Retrieves a paginated list of uploaded files, optionally filtered by processing status.",
)
def list_files(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (COMPLETED, FAILED, etc.)"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: Session = Depends(get_db),
) -> FileListResponse:
    query = db.query(FileRecord)
    if status_filter:
        query = query.filter(FileRecord.status == status_filter.upper())

    total = query.count()
    items = query.order_by(FileRecord.created_at.desc()).offset(offset).limit(limit).all()

    return FileListResponse(
        items=[FileInformationResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{file_id}/features/",
    summary="Get raw feature geometries and attributes",
    description="Returns detailed features with parsed GeoJSON geometry representations.",
)
def get_file_features(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    file_record: FileRecord = Depends(get_file_or_404),
    db: Session = Depends(get_db),
):
    query = (
        db.query(FeatureRecord)
        .filter(FeatureRecord.file_id == file_record.id)
        .order_by(FeatureRecord.feature_index)
    )
    total = query.count()
    features = query.offset(offset).limit(limit).all()

    result = []
    for f in features:
        geom = json.loads(f.geometry_geojson) if f.geometry_geojson else None
        result.append(
            {
                "feature_index": f.feature_index,
                "feature_identifier": f.feature_identifier,
                "geometry_type": f.geometry_type,
                "geometry": geom,
                "properties": f.properties,
                "measurement_type": f.measurement_type,
                "measurement_value": f.measurement_value,
                "measurement_units": f.measurement_units,
                "additional_metrics": f.additional_metrics,
                "projected_crs": f.projected_crs,
                "notes": f.notes,
            }
        )

    return {
        "file_id": file_record.id,
        "filename": file_record.filename,
        "total": total,
        "limit": limit,
        "offset": offset,
        "features": result,
    }


@router.delete(
    "/{file_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a file",
    description="Deletes file records from database and cleans up file storage.",
)
def delete_file(
    file_record: FileRecord = Depends(get_file_or_404),
    db: Session = Depends(get_db),
) -> None:
    storage_path = file_record.storage_path
    db.delete(file_record)
    db.commit()
    FileStorageService.delete_stored_file(storage_path)
    return None
