from datetime import datetime
from typing import List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field


class ResumeResponse(BaseModel):
    """Safe metadata representation of an uploaded resume and active version."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    original_filename: str
    file_type: str
    file_size: int
    is_primary: bool
    version_number: int = 1
    parser_status: str = "pending"
    sections_count: int = 0
    skills_count: int = 0
    created_at: datetime
    updated_at: datetime


class ResumeListResponse(BaseModel):
    """Collection of user-owned resumes."""
    items: List[ResumeResponse]
    total: int


class ResumeUpdateNameRequest(BaseModel):
    """Resume rename payload."""
    name: str = Field(..., min_length=1, max_length=255, description="New display name for the resume")


class ResumeSectionResponse(BaseModel):
    """Detected resume section item."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    resume_version_id: uuid.UUID
    section_type: str
    content: str
    section_order: int


class ResumeSectionsListResponse(BaseModel):
    """Collection of detected sections for a resume version."""
    resume_id: uuid.UUID
    version_number: int
    parser_status: str
    total_sections: int
    sections: List[ResumeSectionResponse]


class ResumeTextResponse(BaseModel):
    """Extracted text contents of a resume version."""
    resume_id: uuid.UUID
    version_number: int
    parser_status: str
    extracted_text: Optional[str]

