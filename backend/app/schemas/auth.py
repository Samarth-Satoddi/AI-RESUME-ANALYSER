import re
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.core.config import settings


class RegisterRequest(BaseModel):
    """User registration payload."""
    email: EmailStr = Field(..., description="Valid candidate email address")
    password: str = Field(..., description="Plaintext user password")
    full_name: str = Field(..., min_length=2, max_length=150, description="Full candidate name")

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("Password cannot be empty or whitespace only.")
        if len(v) < settings.PASSWORD_MIN_LENGTH:
            raise ValueError(f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters long.")
        # Reject trivial passwords
        if v.lower() in {"password", "12345678", "qwerty1234", "admin123"}:
            raise ValueError("Password is too weak. Please choose a more complex password.")
        return v


class LoginRequest(BaseModel):
    """User login payload."""
    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., description="User password")


class TokenResponse(BaseModel):
    """OAuth2 / JWT token response payload."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None


class RefreshTokenRequest(BaseModel):
    """Token rotation payload."""
    refresh_token: str = Field(..., description="Active session refresh token")


class ChangePasswordRequest(BaseModel):
    """Password rotation payload."""
    current_password: str = Field(..., description="Current plaintext password")
    new_password: str = Field(..., description="New plaintext password")

    @field_validator("new_password")
    @classmethod
    def validate_new_password_strength(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("New password cannot be empty.")
        if len(v) < settings.PASSWORD_MIN_LENGTH:
            raise ValueError(f"New password must be at least {settings.PASSWORD_MIN_LENGTH} characters long.")
        return v
