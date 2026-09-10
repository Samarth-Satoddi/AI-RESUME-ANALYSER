from typing import TYPE_CHECKING, List, Optional
import uuid
from sqlalchemy import Boolean, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, GUID, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.user import User
    from app.db.models.analysis import Analysis


class JobDescription(Base, TimestampMixin):
    """Job listing and requirement specification."""
    __tablename__ = "job_descriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    company: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    source_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="job_descriptions",
    )
    requirements: Mapped[List["JobRequirement"]] = relationship(
        "JobRequirement",
        back_populates="job_description",
        cascade="all, delete-orphan",
    )
    analyses: Mapped[List["Analysis"]] = relationship(
        "Analysis",
        back_populates="job_description",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<JobDescription id={self.id} title={self.title} company={self.company}>"


class JobRequirement(Base):
    """Deconstructed qualification or skill requirement for a job posting."""
    __tablename__ = "job_requirements"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    job_description_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("job_descriptions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    requirement_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    requirement_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    normalized_skill_name: Mapped[str] = mapped_column(
        String(150),
        index=True,
        nullable=False,
    )
    category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    is_required: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    years_required: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    # Relationships
    job_description: Mapped["JobDescription"] = relationship(
        "JobDescription",
        back_populates="requirements",
    )

    def __repr__(self) -> str:
        return f"<JobRequirement id={self.id} skill={self.normalized_skill_name} required={self.is_required}>"
