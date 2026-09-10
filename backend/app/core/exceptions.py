from typing import Any, Dict, Optional
from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base application exception with structured error detail."""
    def __init__(
        self,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: str = "An unexpected error occurred.",
        code: str = "INTERNAL_ERROR",
        extra: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.code = code
        self.extra = extra or {}


class NotFoundError(AppException):
    def __init__(self, detail: str = "Requested resource not found.", extra: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            code="RESOURCE_NOT_FOUND",
            extra=extra,
        )


class BadRequestError(AppException):
    def __init__(self, detail: str = "Invalid request.", extra: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            code="BAD_REQUEST",
            extra=extra,
        )


class UnauthorizedError(AppException):
    def __init__(self, detail: str = "Authentication required or credentials invalid."):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            code="UNAUTHORIZED",
        )


class ForbiddenError(AppException):
    def __init__(self, detail: str = "Permission denied to perform this action."):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            code="FORBIDDEN",
        )


class FileValidationError(AppException):
    def __init__(self, detail: str = "Uploaded file failed validation requirements.", extra: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            code="FILE_VALIDATION_ERROR",
            extra=extra,
        )


class ValidationException(BadRequestError):
    def __init__(self, detail: str = "Validation failed.", extra: Optional[Dict[str, Any]] = None):
        super().__init__(detail=detail, extra=extra)

