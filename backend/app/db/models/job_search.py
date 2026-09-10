from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
import uuid
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, GUID, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.user import User
    from app.db.models.resume import Resume
    from app.db.models.job import JobDescription
    from app.db.models.analysis import Analysis


class JobSearch(Base, TimestampMixin):
    """Represents a job search run initiated by a candidate."""
    __tablename__ = "job_searches"

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
    resume_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("resumes.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    # Search parameters
    query_role: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    remote: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True, default=False)
    experience_level: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    employment_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    salary_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    salary_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    skills_filter: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    posted_within_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=14)

    # Execution status: queued -> searching -> analyzing -> matching -> completed / failed
    status: Mapped[str] = mapped_column(String(50), default="queued", index=True, nullable=False)
    jobs_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_analyzed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_matched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User")
    resume: Mapped[Optional["Resume"]] = relationship("Resume")
    results: Mapped[List["JobSearchResult"]] = relationship(
        "JobSearchResult",
        back_populates="search",
        cascade="all, delete-orphan",
        order_by="JobSearchResult.rank",
    )

    def __repr__(self) -> str:
        return f"<JobSearch id={self.id} role={self.query_role} status={self.status}>"


class JobListing(Base, TimestampMixin):
    """Individual normalized job listing discovered from any external or internal source."""
    __tablename__ = "job_listings"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    external_id: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    source: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    company: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    remote_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # remote, hybrid, on-site, unknown
    employment_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # full-time, part-time, contract, internship
    salary_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    salary_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    dedup_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)

    # Optional foreign key linking to existing JobDescription entity to leverage existing matching engine
    job_description_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("job_descriptions.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    # Relationships
    job_description: Mapped[Optional["JobDescription"]] = relationship("JobDescription")
    search_results: Mapped[List["JobSearchResult"]] = relationship(
        "JobSearchResult",
        back_populates="listing",
        cascade="all, delete-orphan",
    )
    saved_by_users: Mapped[List["SavedJob"]] = relationship(
        "SavedJob",
        back_populates="listing",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<JobListing id={self.id} title={self.title} company={self.company} source={self.source}>"


class JobSearchResult(Base, TimestampMixin):
    """Ranked match result linking a JobSearch with a JobListing and Analysis."""
    __tablename__ = "job_search_results"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    search_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("job_searches.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    job_listing_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("job_listings.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    analysis_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID,
        ForeignKey("analyses.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    # Multi-signal deterministic scores
    overall_match_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    skill_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    keyword_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    semantic_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    experience_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    education_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Composite rank & position
    rank_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rank: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Qualitative explanation from AI provider
    ai_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    search: Mapped["JobSearch"] = relationship("JobSearch", back_populates="results")
    listing: Mapped["JobListing"] = relationship("JobListing", back_populates="search_results")
    analysis: Mapped[Optional["Analysis"]] = relationship("Analysis")

    def __repr__(self) -> str:
        return f"<JobSearchResult search={self.search_id} listing={self.job_listing_id} rank={self.rank} score={self.overall_match_score}>"


class SavedJob(Base, TimestampMixin):
    """User-saved job bookmark with application tracking pipeline."""
    __tablename__ = "saved_jobs"
    __table_args__ = (
        UniqueConstraint("user_id", "job_listing_id", name="uq_user_saved_job"),
    )

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
    job_listing_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("job_listings.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="saved",
        index=True,
        nullable=False,
    )  # "saved", "applied", "interview", "rejected", "offer"
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User")
    listing: Mapped["JobListing"] = relationship("JobListing", back_populates="saved_by_users")

    def __repr__(self) -> str:
        return f"<SavedJob user={self.user_id} listing={self.job_listing_id} status={self.status}>"
