import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    String,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Enum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class FileStatus(str):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class FileType(str):
    SHAPEFILE = "SHAPEFILE"
    KML = "KML"


class MeasurementType(str):
    AREA = "AREA"
    LENGTH = "LENGTH"
    NONE = "NONE"
    UNSUPPORTED = "UNSUPPORTED"


class FileRecord(Base):
    __tablename__ = "files"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    feature_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_crs: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=FileStatus.PENDING)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    features: Mapped[List["FeatureRecord"]] = relationship(
        "FeatureRecord",
        back_populates="file",
        cascade="all, delete-orphan",
        order_by="FeatureRecord.feature_index",
    )


class FeatureRecord(Base):
    __tablename__ = "features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    feature_index: Mapped[int] = mapped_column(Integer, nullable=False)
    feature_identifier: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    geometry_type: Mapped[str] = mapped_column(String(50), nullable=False)
    geometry_geojson: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    properties: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    measurement_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=MeasurementType.NONE,
    )
    measurement_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    measurement_units: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    additional_metrics: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    projected_crs: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    file: Mapped["FileRecord"] = relationship("FileRecord", back_populates="features")
