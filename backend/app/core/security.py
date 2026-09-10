from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from typing import Any, Dict, Optional
import bcrypt
import jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedError


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt with automatic salt generation."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its bcrypt hash in constant time."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


def hash_token(token: str) -> str:
    """Hash a sensitive token (such as a refresh token) using SHA-256 before database storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_secure_random_token(nbytes: int = 48) -> str:
    """Generate a cryptographically strong URL-safe random string for refresh tokens."""
    return secrets.token_urlsafe(nbytes)


def create_access_token(
    subject: str,
    extra_claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create an OAuth2/RFC 7519 compliant JWT access token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: Dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    secret_key = settings.JWT_SECRET_KEY or settings.SECRET_KEY
    encoded_jwt = jwt.encode(
        payload,
        secret_key,
        algorithm=settings.JWT_ALGORITHM,
    )
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and strictly validate a JWT access token.
    Checks signature, expiration, and token type.
    """
    secret_key = settings.JWT_SECRET_KEY or settings.SECRET_KEY
    try:
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=[settings.JWT_ALGORITHM],
        )
        # Validate required claims
        if payload.get("type") != "access":
            raise UnauthorizedError(detail="Invalid token type: access token required.")
        if "sub" not in payload:
            raise UnauthorizedError(detail="Invalid token: missing subject claim.")
        return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError(detail="Token has expired. Please authenticate again.")
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError(detail=f"Invalid authentication token: {str(exc)}")
