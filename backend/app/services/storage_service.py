import os
import uuid
from typing import Tuple
from fastapi import UploadFile

from app.core.config import settings
from app.core.exceptions import FileValidationError, NotFoundError
from app.core.logging import logger
from app.services.file_validator import FileValidator


class StorageService:
    """Secure local storage management for uploaded candidate documents."""

    @staticmethod
    def get_upload_dir() -> str:
        """Ensure and return the configured upload directory."""
        upload_path = os.path.abspath(settings.UPLOAD_DIR)
        os.makedirs(upload_path, exist_ok=True)
        return upload_path

    @classmethod
    async def save_upload_file(cls, file: UploadFile) -> Tuple[str, int, str, str]:
        """Stream an uploaded file to secure storage with on-the-fly validation.
        
        Returns:
            Tuple of (stored_filename, file_size_bytes, sanitized_original_name, file_type)
        """
        original_name = file.filename or "resume"
        sanitized_name = FileValidator.sanitize_filename(original_name)
        ext = FileValidator.validate_extension(sanitized_name)
        FileValidator.validate_mime_type(file.content_type or "", ext)

        upload_dir = cls.get_upload_dir()
        # Generate safe server-side storage filename: <uuid>.<ext>
        stored_filename = f"{uuid.uuid4()}{ext}"
        destination_path = os.path.join(upload_dir, stored_filename)

        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        total_bytes = 0
        chunk_size = 64 * 1024  # 64 KB chunks
        first_chunk = True

        try:
            with open(destination_path, "wb") as buffer:
                while True:
                    chunk = await file.read(chunk_size)
                    if not chunk:
                        break

                    if first_chunk:
                        FileValidator.validate_magic_bytes(chunk, ext)
                        first_chunk = False

                    total_bytes += len(chunk)
                    if total_bytes > max_bytes:
                        raise FileValidationError(
                            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB.",
                            extra={"max_size_mb": settings.MAX_UPLOAD_SIZE_MB},
                        )
                    buffer.write(chunk)

            if total_bytes == 0:
                raise FileValidationError(detail="Uploaded file is empty (0 bytes).")

            # Perform lightweight integrity check
            FileValidator.validate_integrity(destination_path, ext)

            file_type = ext.lstrip(".").lower()
            logger.info(f"Successfully stored file: {stored_filename} ({total_bytes} bytes)")
            return stored_filename, total_bytes, sanitized_name, file_type

        except Exception as exc:
            # Clean up partial/corrupt file on failure
            if os.path.exists(destination_path):
                try:
                    os.remove(destination_path)
                except OSError:
                    pass
            logger.warning(f"File upload failed for '{original_name}': {str(exc)}")
            raise

    @classmethod
    def delete_file(cls, stored_filename: str) -> bool:
        """Safely delete an uploaded file from disk, preventing directory traversal."""
        if not stored_filename or "/" in stored_filename or "\\" in stored_filename or ".." in stored_filename:
            return False

        upload_dir = cls.get_upload_dir()
        target_path = os.path.join(upload_dir, stored_filename)

        if os.path.exists(target_path):
            try:
                os.remove(target_path)
                logger.info(f"Removed file from storage: {stored_filename}")
                return True
            except OSError as e:
                logger.error(f"Failed to delete stored file '{stored_filename}': {str(e)}")
                return False
        return False

    @classmethod
    def get_absolute_path(cls, stored_filename: str) -> str:
        """Resolve and verify existence of a stored file."""
        if not stored_filename or "/" in stored_filename or "\\" in stored_filename or ".." in stored_filename:
            raise NotFoundError(detail="Invalid file identifier.")

        upload_dir = cls.get_upload_dir()
        target_path = os.path.join(upload_dir, stored_filename)

        if not os.path.isfile(target_path):
            raise NotFoundError(detail="Requested resume file not found on disk.")

        return target_path

    @classmethod
    def get_file_path(cls, stored_filename: str) -> str:
        """Alias for get_absolute_path to resolve physical storage path."""
        return cls.get_absolute_path(stored_filename)

