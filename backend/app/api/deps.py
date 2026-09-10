from typing import Generator
import uuid
from fastapi import Depends, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppException, ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.models import User
from app.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=True,
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Dependency that verifies Bearer JWT token and retrieves the authenticated User."""
    credentials_exception = AppException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        code="INVALID_CREDENTIALS",
    )

    try:
        payload = decode_access_token(token)
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise credentials_exception
        user_id = uuid.UUID(user_id_str)
    except Exception:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token or token expired.",
            code="UNAUTHORIZED",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
            code="USER_NOT_FOUND",
        )

    if not user.is_active:
        raise AppException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive.",
            code="INACTIVE_USER",
        )

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency verifying the user is fully active."""
    if not current_user.is_active:
        raise ForbiddenError(detail="Inactive candidate account.")
    return current_user


def verify_resource_ownership(resource_owner_id: uuid.UUID, current_user: User) -> None:
    """Reusable authorization guard ensuring users can never access resources of other users."""
    if str(resource_owner_id) != str(current_user.id):
        raise ForbiddenError(
            detail="Access denied: you do not have permission to access or modify this resource."
        )
