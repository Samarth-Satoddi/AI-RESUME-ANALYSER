from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import BadRequestError, UnauthorizedError
from app.core.security import (
    create_access_token,
    generate_secure_random_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.db.models import Profile, RefreshToken, User
from app.schemas.auth import ChangePasswordRequest, RegisterRequest, TokenResponse


class AuthService:
    """Business logic for registration, authentication, sessions, and credentials."""

    @staticmethod
    def register_user(db: Session, data: RegisterRequest) -> User:
        """Register a new candidate account and auto-provision their Profile."""
        normalized_email = data.email.strip().lower()

        # Duplicate check
        existing_user = db.query(User).filter(User.email == normalized_email).first()
        if existing_user:
            raise BadRequestError(detail="An account with this email address already exists.")

        hashed_pw = hash_password(data.password)
        new_user = User(
            email=normalized_email,
            hashed_password=hashed_pw,
            is_active=True,
            is_verified=False,
        )
        db.add(new_user)
        db.flush()  # Obtain new_user.id

        new_profile = Profile(
            user_id=new_user.id,
            full_name=data.full_name.strip(),
            years_of_experience=0.0,
        )
        db.add(new_profile)
        db.commit()
        db.refresh(new_user)
        return new_user

    @staticmethod
    def authenticate_user(db: Session, email: str, password: str) -> User:
        """Authenticate user credentials in constant-time with no enumeration leak."""
        normalized_email = email.strip().lower()
        user = db.query(User).filter(User.email == normalized_email).first()

        # Perform password check or dummy verify to prevent timing enumeration attacks
        dummy_hash = "$2b$12$e9g0/kC11R8s7Q3LqFvRSu2pL3/19L6w4t5Z5m3.7k9r1p8x9v.2i"
        hash_to_check = user.hashed_password if user else dummy_hash
        is_valid = verify_password(password, hash_to_check)

        if not user or not is_valid:
            raise UnauthorizedError(detail="Invalid email or password.")

        if not user.is_active:
            raise UnauthorizedError(detail="Account is currently inactive. Please contact support.")

        return user

    @staticmethod
    def create_tokens_for_user(db: Session, user: User) -> TokenResponse:
        """Generate a short-lived access token and a hashed refresh session token."""
        access_token = create_access_token(subject=str(user.id))

        raw_refresh_token = generate_secure_random_token()
        token_digest = hash_token(raw_refresh_token)
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        refresh_record = RefreshToken(
            user_id=user.id,
            token_hash=token_digest,
            expires_at=expires_at,
            created_at=now,
        )
        db.add(refresh_record)
        db.commit()

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token=raw_refresh_token,
        )

    @staticmethod
    def refresh_session(db: Session, refresh_token: str) -> TokenResponse:
        """Rotate an active refresh token session and produce a new access token."""
        token_digest = hash_token(refresh_token)
        record = (
            db.query(RefreshToken)
            .filter(RefreshToken.token_hash == token_digest)
            .first()
        )

        now = datetime.now(timezone.utc)
        if not record or record.revoked_at is not None:
            raise UnauthorizedError(detail="Invalid or revoked refresh token.")

        # Ensure timezone-awareness for comparison
        expires_at = record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < now:
            record.revoked_at = now
            db.commit()
            raise UnauthorizedError(detail="Refresh token has expired. Please log in again.")

        user = db.query(User).filter(User.id == record.user_id).first()
        if not user or not user.is_active:
            record.revoked_at = now
            db.commit()
            raise UnauthorizedError(detail="User account is inactive or not found.")

        # Revoke old refresh token (strict single-use rotation)
        record.revoked_at = now
        record.last_used_at = now
        db.flush()

        # Issue fresh token pair
        return AuthService.create_tokens_for_user(db, user)

    @staticmethod
    def revoke_session(db: Session, refresh_token: str) -> None:
        """Revoke a refresh token on logout."""
        token_digest = hash_token(refresh_token)
        record = (
            db.query(RefreshToken)
            .filter(RefreshToken.token_hash == token_digest)
            .first()
        )
        if record and record.revoked_at is None:
            record.revoked_at = datetime.now(timezone.utc)
            db.commit()

    @staticmethod
    def change_password(db: Session, user: User, data: ChangePasswordRequest) -> None:
        """Verify current password, hash new password, and invalidate existing refresh sessions."""
        if not verify_password(data.current_password, user.hashed_password):
            raise UnauthorizedError(detail="Current password is incorrect.")

        if verify_password(data.new_password, user.hashed_password):
            raise BadRequestError(detail="New password cannot be the same as the current password.")

        user.hashed_password = hash_password(data.new_password)

        # Invalidate all active sessions for this user on security credential change
        now = datetime.now(timezone.utc)
        active_sessions = (
            db.query(RefreshToken)
            .filter(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
            .all()
        )
        for s in active_sessions:
            s.revoked_at = now

        db.commit()
