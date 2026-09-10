from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import BadRequestError
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import (
    ChangePasswordRequest,
    RefreshTokenRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
):
    """Create a new candidate account, hash credentials, and provision an initial profile."""
    new_user = AuthService.register_user(db=db, data=data)
    return new_user


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate and receive JWT access token",
)
async def login(
    request: Request,
    db: Session = Depends(get_db),
):
    """OAuth2-compatible and JSON-compatible authentication endpoint.
    Accepts application/json body or application/x-www-form-urlencoded (for Swagger UI).
    """
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
        except Exception:
            raise BadRequestError(detail="Invalid JSON payload.")
        email = body.get("email") or body.get("username")
        password = body.get("password")
    else:
        form = await request.form()
        email = form.get("username") or form.get("email")
        password = form.get("password")

    if not email or not password:
        raise BadRequestError(detail="Email and password are required.")

    user = AuthService.authenticate_user(db=db, email=str(email), password=str(password))
    return AuthService.create_tokens_for_user(db=db, user=user)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate refresh token and issue new access token",
)
def refresh(
    data: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    """Rotate an existing valid refresh token and obtain a fresh access token."""
    return AuthService.refresh_session(db=db, refresh_token=data.refresh_token)


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Revoke active refresh session",
)
def logout(
    data: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    """Invalidate a refresh session token on the server."""
    AuthService.revoke_session(db=db, refresh_token=data.refresh_token)
    return {"status": "success", "message": "Logged out successfully."}


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve current authenticated user",
)
def get_me(
    current_user: User = Depends(get_current_user),
):
    """Return profile and account information for the currently authenticated user."""
    return current_user


@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
    summary="Rotate user password",
)
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Verify existing password and securely apply new password hash."""
    AuthService.change_password(db=db, user=current_user, data=data)
    return {"status": "success", "message": "Password updated successfully."}
