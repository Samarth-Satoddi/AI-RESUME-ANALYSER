from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, EmailStr
from app.schemas.profile import ProfileResponse


class UserResponse(BaseModel):
    """Safe user account representation (no passwords or sensitive security fields)."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    is_active: bool
    is_verified: bool
    created_at: datetime
    profile: Optional[ProfileResponse] = None


class UserUpdateRequest(BaseModel):
    """User-editable fields (strictly constrained)."""
    email: Optional[EmailStr] = None
