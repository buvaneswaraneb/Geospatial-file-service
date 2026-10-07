from typing import Generator
from fastapi import Depends, Path
from sqlalchemy.orm import Session

from app.core.exceptions import FileNotFoundInStorageError
from app.db.session import get_db
from app.models.file_record import FileRecord


def get_file_or_404(
    file_id: str = Path(..., description="Unique file UUID"),
    db: Session = Depends(get_db),
) -> FileRecord:
    """Dependency to retrieve a FileRecord by ID or raise FileNotFoundInStorageError (404)."""
    file_record = db.query(FileRecord).filter(FileRecord.id == file_id).first()
    if not file_record:
        raise FileNotFoundInStorageError(
            message=f"File with ID '{file_id}' was not found.",
            details={"file_id": file_id},
        )
    return file_record
