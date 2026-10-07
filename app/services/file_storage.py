import os
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Tuple
from fastapi import UploadFile

from app.config import settings
from app.core.exceptions import (
    CorruptedFileError,
    FileSizeLimitExceededError,
    UnsupportedFileTypeError,
    ZipSlipSecurityError,
)
from app.core.logging import logger
from app.models.file_record import FileType


class FileStorageService:
    @staticmethod
    def validate_file_type(filename: str) -> Tuple[str, str]:
        """Validates extension and returns (extension, FileType)."""
        suffix = Path(filename).suffix.lower()
        if suffix == ".zip":
            return suffix, FileType.SHAPEFILE
        elif suffix == ".kml":
            return suffix, FileType.KML
        else:
            raise UnsupportedFileTypeError(
                message=f"Unsupported file type '{suffix}'. Supported formats are: .zip (Shapefile) and .kml",
                details={"filename": filename, "extension": suffix, "allowed": settings.ALLOWED_EXTENSIONS},
            )

    @classmethod
    async def save_upload_file(cls, file: UploadFile) -> Tuple[str, Path, str, int]:
        """
        Streams and saves uploaded file to storage.
        Enforces maximum upload size and returns (file_id, saved_path, file_type, size_bytes).
        """
        if not file.filename:
            raise UnsupportedFileTypeError("Missing filename in uploaded file.")

        extension, file_type = cls.validate_file_type(file.filename)
        file_id = str(uuid.uuid4())
        safe_filename = f"{file_id}{extension}"
        target_path = settings.UPLOAD_DIR / safe_filename

        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        total_bytes = 0

        try:
            with open(target_path, "wb") as buffer:
                while chunk := await file.read(1024 * 1024):  # 1MB chunks
                    total_bytes += len(chunk)
                    if total_bytes > max_bytes:
                        # Clean up partial file
                        buffer.close()
                        if target_path.exists():
                            target_path.unlink()
                        raise FileSizeLimitExceededError(
                            message=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB.",
                            details={"max_mb": settings.MAX_UPLOAD_SIZE_MB, "uploaded_bytes": total_bytes},
                        )
                    buffer.write(chunk)
        except (FileSizeLimitExceededError, UnsupportedFileTypeError):
            raise
        except Exception as e:
            if target_path.exists():
                target_path.unlink()
            logger.error("Failed to save uploaded file %s: %s", file.filename, e)
            raise CorruptedFileError(
                message=f"Could not save uploaded file: {str(e)}",
                details={"filename": file.filename},
            )

        # Post-save validation for zip files
        if file_type == FileType.SHAPEFILE:
            cls.validate_zip_archive(target_path)

        return file_id, target_path, file_type, total_bytes

    @staticmethod
    def validate_zip_archive(zip_path: Path) -> None:
        """Validates that zip is not corrupted and prevents ZipSlip path traversal attacks."""
        if not zipfile.is_zipfile(zip_path):
            if zip_path.exists():
                zip_path.unlink()
            raise CorruptedFileError(
                message="Uploaded .zip file is not a valid or readable ZIP archive.",
                details={"path": str(zip_path)},
            )

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                # Test zip integrity
                bad_file = zf.testzip()
                if bad_file:
                    raise CorruptedFileError(
                        message=f"Corrupted file entry detected inside ZIP archive: '{bad_file}'",
                        details={"corrupted_entry": bad_file},
                    )

                # ZipSlip check
                for member in zf.namelist():
                    norm_path = os.path.normpath(member)
                    if norm_path.startswith("..") or os.path.isabs(norm_path) or "/../" in member:
                        raise ZipSlipSecurityError(
                            message=f"Security violation: Zip archive contains illegal relative path: '{member}'"
                        )
        except (CorruptedFileError, ZipSlipSecurityError):
            if zip_path.exists():
                zip_path.unlink()
            raise
        except Exception as e:
            if zip_path.exists():
                zip_path.unlink()
            raise CorruptedFileError(
                message=f"Failed to inspect zip archive: {str(e)}",
                details={"error": str(e)},
            )

    @staticmethod
    def delete_stored_file(file_path: str) -> None:
        """Deletes file from storage if it exists."""
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                logger.info("Deleted stored file at %s", file_path)
        except Exception as e:
            logger.warning("Could not delete stored file at %s: %s", file_path, e)
