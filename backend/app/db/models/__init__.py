"""Model exports for SQLAlchemy declarative Base."""
from app.db.models.user import User
from app.db.models.profile import Profile
from app.db.models.resume import (
    Resume,
    ResumeVersion,
    ResumeSection,
    ResumeSkill,
    Experience,
    Education,
    Project,
    Certification,
)
from app.db.models.job import (
    JobDescription,
    JobRequirement,
)
from app.db.models.analysis import (
    Analysis,
    SkillMatch,
    MissingSkill,
    Recommendation,
    LearningRoadmap,
    LearningRoadmapItem,
    InterviewQuestion,
)
from app.db.models.session import RefreshToken
from app.db.models.job_search import (
    JobSearch,
    JobListing,
    JobSearchResult,
    SavedJob,
)

__all__ = [
    "User",
    "Profile",
    "Resume",
    "ResumeVersion",
    "ResumeSection",
    "ResumeSkill",
    "Experience",
    "Education",
    "Project",
    "Certification",
    "JobDescription",
    "JobRequirement",
    "Analysis",
    "SkillMatch",
    "MissingSkill",
    "Recommendation",
    "LearningRoadmap",
    "LearningRoadmapItem",
    "InterviewQuestion",
    "RefreshToken",
    "JobSearch",
    "JobListing",
    "JobSearchResult",
    "SavedJob",
]
