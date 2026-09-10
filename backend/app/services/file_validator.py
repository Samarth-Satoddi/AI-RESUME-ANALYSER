import os
import re
import zipfile
from typing import Tuple
import fitz  # PyMuPDF
import docx

from app.core.config import settings
from app.core.exceptions import BadRequestError, FileValidationError

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}

MIME_TYPE_MAP = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
}


class FileValidator:
    """Modular file security and integrity validation for resume uploads."""

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Strip directory traversal elements and extract a safe basename."""
        if not filename:
            return "resume"
        # Strip path separators
        clean_name = os.path.basename(filename.replace("\\", "/"))
        # Remove dangerous shell and control characters
        clean_name = re.sub(r"[^\w\s\.-]", "", clean_name).strip()
        return clean_name or "resume"

    @staticmethod
    def generate_display_name(original_filename: str) -> str:
        """Convert a filename into a human-readable title (e.g. John_Doe_Resume.pdf -> John Doe Resume)."""
        base_name, _ = os.path.splitext(original_filename)
        # Replace underscores and hyphens with spaces
        readable = re.sub(r"[_-]+", " ", base_name).strip()
        # Clean up excessive whitespace
        readable = re.sub(r"\s+", " ", readable)
        return readable.title() if readable else "Resume"

    @staticmethod
    def validate_extension(filename: str) -> str:
        """Validate that the file extension is one of .pdf, .docx, .txt."""
        _, ext = os.path.splitext(filename.lower())
        if not ext or ext not in ALLOWED_EXTENSIONS:
            raise FileValidationError(
                detail=f"Unsupported file format '{ext or 'unknown'}'. Only PDF, DOCX, and TXT are accepted.",
                extra={"allowed_extensions": list(ALLOWED_EXTENSIONS)},
            )
        return ext

    @staticmethod
    def validate_mime_type(content_type: str, ext: str) -> None:
        """Validate declared MIME type against expected extension."""
        expected_mime = MIME_TYPE_MAP.get(ext)
        # Be lenient with generic octet-stream from some browsers if magic bytes match, but reject blatant mismatches
        if content_type and content_type not in (
            expected_mime,
            "application/octet-stream",
            "application/x-zip-compressed",
            "text/plain",
        ):
            raise FileValidationError(
                detail=f"Invalid MIME type '{content_type}' for {ext.upper()} file.",
                extra={"expected_mime": expected_mime, "received_mime": content_type},
            )

    @staticmethod
    def validate_magic_bytes(header_bytes: bytes, ext: str) -> None:
        """Inspect the initial file header bytes against known magic signatures."""
        if not header_bytes:
            raise FileValidationError(detail="Uploaded file is empty (0 bytes).")

        if ext == ".pdf":
            # PDF must begin with %PDF-
            if not header_bytes.startswith(b"%PDF-"):
                raise FileValidationError(
                    detail="Invalid PDF file signature. The file is corrupted or not a valid PDF document."
                )

        elif ext == ".docx":
            # DOCX is a ZIP-based OOXML archive starting with PK\x03\x04
            if not header_bytes.startswith(b"PK\x03\x04"):
                raise FileValidationError(
                    detail="Invalid DOCX file signature. The file is corrupted or not a valid Word document."
                )

        elif ext == ".txt":
            # Reject binary files masquerading as .txt (e.g. executables starting with MZ, ELF, or binary null bytes)
            if header_bytes.startswith(b"MZ") or header_bytes.startswith(b"\x7fELF"):
                raise FileValidationError(detail="Binary executable detected. Upload rejected.")
            if b"\x00" in header_bytes[:1024]:
                raise FileValidationError(
                    detail="Binary data detected in text file. Upload a plain UTF-8 or ASCII text document."
                )

    @staticmethod
    def validate_integrity(file_path: str, ext: str) -> None:
        """Perform lightweight structural verification without extracting resume contents."""
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            raise FileValidationError(detail="Uploaded file is empty.")

        if ext == ".pdf":
            try:
                doc = fitz.open(file_path)
                page_count = doc.page_count
                doc.close()
                if page_count < 1:
                    raise FileValidationError(detail="PDF contains no readable pages.")
            except Exception as e:
                raise FileValidationError(detail=f"Malformed or corrupted PDF file: {str(e)}")

        elif ext == ".docx":
            try:
                # 1. Verify it is a valid zip package with document.xml
                if not zipfile.is_zipfile(file_path):
                    raise FileValidationError(detail="Corrupted DOCX archive.")
                with zipfile.ZipFile(file_path, "r") as z:
                    namelist = z.namelist()
                    if not any("word/document.xml" in name for name in namelist):
                        raise FileValidationError(
                            detail="Invalid Word document structure: missing word/document.xml."
                        )
                # 2. Verify docx library can initialize the package
                docx.Document(file_path)
            except Exception as e:
                raise FileValidationError(detail=f"Malformed or corrupted DOCX document: {str(e)}")

        elif ext == ".txt":
            try:
                # Verify decodability in common text encodings
                with open(file_path, "rb") as f:
                    content = f.read()
                # Check for null bytes
                if b"\x00" in content:
                    raise FileValidationError(detail="Text file contains prohibited binary characters.")
                # Verify decodable
                try:
                    content.decode("utf-8")
                except UnicodeDecodeError:
                    try:
                        content.decode("latin-1")
                    except UnicodeDecodeError:
                        raise FileValidationError(detail="Text file cannot be decoded using UTF-8 or Latin-1.")
            except FileValidationError:
                raise
            except Exception as e:
                raise FileValidationError(detail=f"Failed to read text file: {str(e)}")
