from typing import TYPE_CHECKING, List, Optional
import uuid
from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, GUID, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.user import User
    from app.db.models.analysis import Analysis


class Resume(Base, TimestampMixin):
    """Resume parent entity representing a candidate resume document."""
    __tablename__ = "resumes"

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
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    file_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    file_size: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    storage_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )
    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="resumes",
    )
    versions: Mapped[List["ResumeVersion"]] = relationship(
        "ResumeVersion",
        back_populates="resume",
        cascade="all, delete-orphan",
        order_by="ResumeVersion.version_number",
    )

    def __repr__(self) -> str:
        return f"<Resume id={self.id} name={self.name} is_primary={self.is_primary}>"


class ResumeVersion(Base, TimestampMixin):
    """Specific revision of a resume with extracted contents and sections."""
    __tablename__ = "resume_versions"
    __table_args__ = (
        UniqueConstraint("resume_id", "version_number", name="uq_resume_version_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    resume_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("resumes.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    extracted_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    parser_status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
    )

    # Relationships
    resume: Mapped["Resume"] = relationship(
        "Resume",
        back_populates="versions",
    )
    sections: Mapped[List["ResumeSection"]] = relationship(
        "ResumeSection",
        back_populates="resume_version",
        cascade="all, delete-orphan",
        order_by="ResumeSection.section_order",
    )
    skills: Mapped[List["ResumeSkill"]] = relationship(
        "ResumeSkill",
        back_populates="resume_version",
        cascade="all, delete-orphan",
    )
    experiences: Mapped[List["Experience"]] = relationship(
        "Experience",
        back_populates="resume_version",
        cascade="all, delete-orphan",
    )
    education: Mapped[List["Education"]] = relationship(
        "Education",
        back_populates="resume_version",
        cascade="all, delete-orphan",
    )
    projects: Mapped[List["Project"]] = relationship(
        "Project",
        back_populates="resume_version",
        cascade="all, delete-orphan",
    )
    certifications: Mapped[List["Certification"]] = relationship(
        "Certification",
        back_populates="resume_version",
        cascade="all, delete-orphan",
    )
    analyses: Mapped[List["Analysis"]] = relationship(
        "Analysis",
        back_populates="resume_version",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ResumeVersion id={self.id} resume_id={self.resume_id} version={self.version_number}>"


class ResumeSection(Base):
    """Segmented resume section (e.g. Experience, Education, Skills)."""
    __tablename__ = "resume_sections"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    resume_version_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("resume_versions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    section_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    section_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    resume_version: Mapped["ResumeVersion"] = relationship(
        "ResumeVersion",
        back_populates="sections",
    )


class ResumeSkill(Base):
    """Extracted skill entity associated with a resume version."""
    __tablename__ = "resume_skills"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    resume_version_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("resume_versions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    skill_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    normalized_skill_name: Mapped[str] = mapped_column(
        String(150),
        index=True,
        nullable=False,
    )
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    proficiency: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    years_used: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    resume_version: Mapped["ResumeVersion"] = relationship(
        "ResumeVersion",
        back_populates="skills",
    )


class Experience(Base):
    """Work experience record extracted from resume."""
    __tablename__ = "experiences"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    resume_version_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("resume_versions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    company: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    job_title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    location: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    start_date: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    end_date: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    resume_version: Mapped["ResumeVersion"] = relationship(
        "ResumeVersion",
        back_populates="experiences",
    )


class Education(Base):
    """Educational qualification extracted from resume."""
    __tablename__ = "educations"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    resume_version_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("resume_versions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    institution: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    degree: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    field_of_study: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    start_date: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    end_date: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    grade: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    resume_version: Mapped["ResumeVersion"] = relationship(
        "ResumeVersion",
        back_populates="education",
    )


class Project(Base):
    """Portfolio or academic project extracted from resume."""
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    resume_version_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("resume_versions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    technologies: Mapped[Optional[dict | list]] = mapped_column(
        JSON,
        nullable=True,
    )
    project_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    github_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    start_date: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    end_date: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    resume_version: Mapped["ResumeVersion"] = relationship(
        "ResumeVersion",
        back_populates="projects",
    )


class Certification(Base):
    """Professional license or credential extracted from resume."""
    __tablename__ = "certifications"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    resume_version_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("resume_versions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    issuing_organization: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    issue_date: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    expiration_date: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    credential_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    credential_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )

    resume_version: Mapped["ResumeVersion"] = relationship(
        "ResumeVersion",
        back_populates="certifications",
    )
