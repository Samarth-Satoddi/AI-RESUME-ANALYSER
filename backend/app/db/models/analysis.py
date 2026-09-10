from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
import uuid
from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, GUID

if TYPE_CHECKING:
    from app.db.models.user import User
    from app.db.models.resume import ResumeVersion
    from app.db.models.job import JobDescription


class Analysis(Base):
    """Evaluation record comparing a resume version against a job description."""
    __tablename__ = "analyses"

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
    resume_version_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("resume_versions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    job_description_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("job_descriptions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
    )
    overall_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    resume_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    ats_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    skill_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    semantic_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    experience_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    keyword_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    education_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="analyses",
    )
    resume_version: Mapped["ResumeVersion"] = relationship(
        "ResumeVersion",
        back_populates="analyses",
    )
    job_description: Mapped["JobDescription"] = relationship(
        "JobDescription",
        back_populates="analyses",
    )
    skill_matches: Mapped[List["SkillMatch"]] = relationship(
        "SkillMatch",
        back_populates="analysis",
        cascade="all, delete-orphan",
    )
    missing_skills: Mapped[List["MissingSkill"]] = relationship(
        "MissingSkill",
        back_populates="analysis",
        cascade="all, delete-orphan",
    )
    recommendations: Mapped[List["Recommendation"]] = relationship(
        "Recommendation",
        back_populates="analysis",
        cascade="all, delete-orphan",
    )
    learning_roadmap: Mapped[Optional["LearningRoadmap"]] = relationship(
        "LearningRoadmap",
        back_populates="analysis",
        uselist=False,
        cascade="all, delete-orphan",
    )
    interview_questions: Mapped[List["InterviewQuestion"]] = relationship(
        "InterviewQuestion",
        back_populates="analysis",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Analysis id={self.id} status={self.status} overall_score={self.overall_score}>"


class SkillMatch(Base):
    """Detailed match evaluation for an identified skill."""
    __tablename__ = "skill_matches"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("analyses.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    skill_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    resume_skill: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
    )
    job_skill: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
    )
    match_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    similarity_score: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    importance: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    analysis: Mapped["Analysis"] = relationship(
        "Analysis",
        back_populates="skill_matches",
    )


class MissingSkill(Base):
    """Identified requirement absent from candidate's resume."""
    __tablename__ = "missing_skills"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("analyses.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    skill_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    category: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
    )
    priority: Mapped[str] = mapped_column(
        String(50),
        default="medium",
        nullable=False,
    )
    reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    analysis: Mapped["Analysis"] = relationship(
        "Analysis",
        back_populates="missing_skills",
    )


class Recommendation(Base):
    """Tailored feedback and improvement suggestions."""
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("analyses.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    recommendation_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    priority: Mapped[str] = mapped_column(
        String(50),
        default="medium",
        nullable=False,
    )

    analysis: Mapped["Analysis"] = relationship(
        "Analysis",
        back_populates="recommendations",
    )


class LearningRoadmap(Base):
    """Personalized curriculum designed to close skill gaps."""
    __tablename__ = "learning_roadmaps"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("analyses.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    estimated_days: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    analysis: Mapped["Analysis"] = relationship(
        "Analysis",
        back_populates="learning_roadmap",
    )
    items: Mapped[List["LearningRoadmapItem"]] = relationship(
        "LearningRoadmapItem",
        back_populates="learning_roadmap",
        cascade="all, delete-orphan",
        order_by="LearningRoadmapItem.order_index",
    )


class LearningRoadmapItem(Base):
    """Step-by-step topic module within a learning roadmap."""
    __tablename__ = "learning_roadmap_items"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    learning_roadmap_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("learning_roadmaps.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    skill_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    topic: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    priority: Mapped[str] = mapped_column(
        String(50),
        default="medium",
        nullable=False,
    )
    estimated_days: Mapped[int] = mapped_column(
        Integer,
        default=7,
        nullable=False,
    )
    prerequisites: Mapped[Optional[dict | list]] = mapped_column(
        JSON,
        nullable=True,
    )
    order_index: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    learning_roadmap: Mapped["LearningRoadmap"] = relationship(
        "LearningRoadmap",
        back_populates="items",
    )


class InterviewQuestion(Base):
    """Targeted interview question with evaluation guidance."""
    __tablename__ = "interview_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("analyses.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    question: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    difficulty: Mapped[str] = mapped_column(
        String(50),
        default="medium",
        nullable=False,
    )
    why_it_matters: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    answer_guidance: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    analysis: Mapped["Analysis"] = relationship(
        "Analysis",
        back_populates="interview_questions",
    )
