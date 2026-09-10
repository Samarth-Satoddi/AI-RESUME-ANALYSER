import re
import uuid
from typing import List, Optional
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.logging import logger
from app.db.models import JobDescription, JobRequirement, User
from app.services.skill_extractor import SkillExtractor


class JobCreateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    company: Optional[str] = Field(None, max_length=255)
    description: str = Field(..., min_length=10)
    source_url: Optional[str] = Field(None, max_length=500)


class JobRequirementResponse(BaseModel):
    id: uuid.UUID
    requirement_type: str
    requirement_text: str
    normalized_skill_name: str
    category: Optional[str] = None
    is_required: bool


class JobResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    company: Optional[str]
    description: str
    source_url: Optional[str]
    requirements: List[JobRequirementResponse] = []
    created_at: str
    updated_at: str


class JobService:
    """Service handling job description CRUD operations and requirement parsing."""

    @classmethod
    def parse_job_requirements(cls, db: Session, job: JobDescription) -> List[JobRequirement]:
        """
        Analyze job description text and extract structured requirements:
        - Required vs preferred technical skills
        - Years of experience requirement
        - Education requirement
        """
        # 1. Clean previous requirements
        db.query(JobRequirement).filter(JobRequirement.job_description_id == job.id).delete()

        desc = job.description
        desc_lower = desc.lower()

        # Split description into sections if headers exist
        sections = re.split(r"(?:requirements|qualifications|responsibilities|what you['’]ll do|nice to have|preferred qualifications)[:\n]", desc, flags=re.IGNORECASE)

        # 2. Extract taxonomy skills from the text
        extractor = SkillExtractor.get_instance()
        extracted_skills = extractor.extract_skills(desc)

        created_reqs: List[JobRequirement] = []

        # Determine if skill is in 'preferred' or 'required' context
        preferred_zone_match = re.search(r"(?:preferred|nice to have|plus|bonus|optional)[\s\S]*", desc_lower)
        preferred_zone = preferred_zone_match.group(0) if preferred_zone_match else ""

        for s in extracted_skills:
            # Check if skill appeared in preferred zone
            is_req = not (s.normalized_skill_name in preferred_zone)

            req = JobRequirement(
                job_description_id=job.id,
                requirement_type="skill",
                requirement_text=f"{'Required' if is_req else 'Preferred'}: {s.skill_name}",
                normalized_skill_name=s.normalized_skill_name,
                category=s.category,
                is_required=is_req,
            )
            db.add(req)
            created_reqs.append(req)

        # 3. Detect experience requirement (e.g. '5+ years of software experience')
        exp_match = re.search(r"(\d+\+?\s*(?:to\s*\d+)?\s*(?:years?|yrs?)[^\.\n]*?(?:experience|background))", desc, re.IGNORECASE)
        if exp_match:
            exp_text = exp_match.group(1).strip()
            exp_req = JobRequirement(
                job_description_id=job.id,
                requirement_type="experience",
                requirement_text=exp_text,
                normalized_skill_name="years_experience",
                category="experience",
                is_required=True,
            )
            db.add(exp_req)
            created_reqs.append(exp_req)

        # 4. Detect degree requirement
        edu_match = re.search(r"((?:bachelor|master|phd|b\.s\.|m\.s\.)[^\.\n]*?(?:degree|in computer science|engineering)?)", desc, re.IGNORECASE)
        if edu_match:
            edu_text = edu_match.group(1).strip()
            edu_req = JobRequirement(
                job_description_id=job.id,
                requirement_type="education",
                requirement_text=edu_text,
                normalized_skill_name="degree_level",
                category="education",
                is_required=True,
            )
            db.add(edu_req)
            created_reqs.append(edu_req)

        db.commit()
        logger.info(f"Parsed {len(created_reqs)} requirements for job_id={job.id}")
        return created_reqs

    @classmethod
    def create_job(cls, db: Session, user: User, data: JobCreateRequest) -> JobDescription:
        """Create a new job posting record and automatically parse requirements."""
        job = JobDescription(
            user_id=user.id,
            title=data.title.strip(),
            company=data.company.strip() if data.company else None,
            description=data.description.strip(),
            source_url=data.source_url.strip() if data.source_url else None,
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        cls.parse_job_requirements(db, job)
        db.refresh(job)
        return job

    @classmethod
    def get_user_jobs(cls, db: Session, user: User) -> List[JobDescription]:
        """Fetch all jobs saved by the authenticated user."""
        return (
            db.query(JobDescription)
            .filter(JobDescription.user_id == user.id)
            .order_by(JobDescription.created_at.desc())
            .all()
        )

    @classmethod
    def get_job_by_id(cls, db: Session, user: User, job_id: uuid.UUID) -> JobDescription:
        """Fetch single job with ownership verification."""
        job = (
            db.query(JobDescription)
            .filter(JobDescription.id == job_id, JobDescription.user_id == user.id)
            .first()
        )
        if not job:
            raise NotFoundError("Job description not found or access denied.")
        return job

    @classmethod
    def delete_job(cls, db: Session, user: User, job_id: uuid.UUID) -> None:
        """Delete job description and cascade delete all associated requirements."""
        job = cls.get_job_by_id(db, user, job_id)
        db.delete(job)
        db.commit()
        logger.info(f"Deleted job_id={job_id} for user={user.id}")
