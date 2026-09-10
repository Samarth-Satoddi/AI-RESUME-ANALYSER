from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProfileResponse(BaseModel):
    """Candidate career profile representation."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    full_name: str
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    target_role: Optional[str] = None
    years_of_experience: float = 0.0
    updated_at: datetime


class ProfileUpdateRequest(BaseModel):
    """Editable profile attributes."""
    full_name: Optional[str] = Field(None, min_length=2, max_length=150)
    phone: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=255)
    linkedin_url: Optional[str] = Field(None, max_length=500)
    github_url: Optional[str] = Field(None, max_length=500)
    portfolio_url: Optional[str] = Field(None, max_length=500)
    target_role: Optional[str] = Field(None, max_length=255)
    years_of_experience: Optional[float] = Field(None, ge=0.0, le=70.0)

    @field_validator("linkedin_url", "github_url", "portfolio_url")
    @classmethod
    def validate_urls(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip() != "":
            v = v.strip()
            if not (v.startswith("http://") or v.startswith("https://")):
                raise ValueError("URL must begin with http:// or https://")
        return v
