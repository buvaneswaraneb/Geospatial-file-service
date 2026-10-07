from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


class FileInformationResponse(BaseModel):
    id: str = Field(..., description="Unique file UUID")
    filename: str = Field(..., description="Original uploaded filename")
    feature_count: int = Field(..., description="Number of geospatial features extracted")
    crs: Optional[str] = Field(None, description="Coordinate Reference System of the file")
    status: str = Field(..., description="Processing status (PENDING, PROCESSING, COMPLETED, FAILED)")
    file_type: Optional[str] = Field(None, description="SHAPEFILE or KML")
    file_size_bytes: Optional[int] = Field(None, description="Size in bytes")
    created_at: Optional[datetime] = Field(None, description="Upload timestamp")
    error_message: Optional[str] = Field(None, description="Error reason if processing failed")

    @model_validator(mode="before")
    @classmethod
    def populate_crs_from_source(cls, data: any) -> any:
        if hasattr(data, "source_crs") and not getattr(data, "crs", None):
            # Object like SQLAlchemy model
            return {
                "id": data.id,
                "filename": data.filename,
                "feature_count": data.feature_count,
                "crs": data.source_crs,
                "status": data.status,
                "file_type": data.file_type,
                "file_size_bytes": data.file_size_bytes,
                "created_at": data.created_at,
                "error_message": data.error_message,
            }
        elif isinstance(data, dict):
            if "crs" not in data and "source_crs" in data:
                data["crs"] = data["source_crs"]
            return data
        return data

    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }


class FileListResponse(BaseModel):
    items: List[FileInformationResponse]
    total: int
    limit: int
    offset: int
