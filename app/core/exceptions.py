from typing import Any, Dict, Optional


class GeospatialAPIException(Exception):
    """Base exception for all domain-specific errors in the Geospatial API."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class UnsupportedFileTypeError(GeospatialAPIException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="UNSUPPORTED_FILE_TYPE",
            status_code=400,
            details=details,
        )


class CorruptedFileError(GeospatialAPIException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="CORRUPTED_FILE",
            status_code=400,
            details=details,
        )


class MissingShapefileComponentsError(GeospatialAPIException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="MISSING_SHAPEFILE_COMPONENTS",
            status_code=400,
            details=details,
        )


class ZipSlipSecurityError(GeospatialAPIException):
    def __init__(
        self,
        message: str = "Zip archive contains forbidden path traversal entries",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="ZIP_SLIP_ATTEMPT",
            status_code=400,
            details=details,
        )


class EmptyDatasetError(GeospatialAPIException):
    def __init__(
        self,
        message: str = "Uploaded file does not contain any geospatial features",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="EMPTY_DATASET",
            status_code=400,
            details=details,
        )


class FileNotFoundInStorageError(GeospatialAPIException):
    def __init__(
        self,
        message: str = "File record not found",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code="FILE_NOT_FOUND",
            status_code=404,
            details=details,
        )


class FileSizeLimitExceededError(GeospatialAPIException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="FILE_SIZE_LIMIT_EXCEEDED",
            status_code=413,
            details=details,
        )


class CRSTransformationError(GeospatialAPIException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="CRS_TRANSFORMATION_ERROR",
            status_code=422,
            details=details,
        )


class InvalidGeometryError(GeospatialAPIException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="INVALID_GEOMETRY",
            status_code=422,
            details=details,
        )


class GeospatialProcessingError(GeospatialAPIException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="PROCESSING_ERROR",
            status_code=500,
            details=details,
        )
