import asyncio
import json
from typing import Any, Dict, List, Optional
import uuid

from fastapi import BackgroundTasks
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.logging import logger
from app.db.models import (
    Analysis,
    JobListing,
    JobSearch,
    JobSearchResult,
    Profile,
    Resume,
    ResumeSkill,
    ResumeVersion,
    SavedJob,
    User,
)
from app.job_search.agent import JobSearchAgent
from app.job_search.schemas import (
    JobSearchQuery,
    MissingSkillDetail,
    RankedJobOpportunity,
    SavedJobResponse,
    SearchDefaultsResponse,
)


class JobSearchService:
    """Service layer managing search execution, filtering, saved bookmarks, and preferences."""

    @classmethod
    def get_search_defaults(cls, db: Session, user: User) -> SearchDefaultsResponse:
        """Infer intelligent search defaults from candidate profile and active resume."""
        profile = db.query(Profile).filter(Profile.user_id == user.id).first()
        resumes = db.query(Resume).filter(Resume.user_id == user.id).order_by(Resume.created_at.desc()).all()

        target_role = None
        location = None
        experience_level = None
        skills: List[str] = []
        rec_resume_id = None
        rec_resume_name = None

        if profile:
            target_role = profile.target_role
            location = profile.location
            if profile.years_of_experience > 0:
                y = profile.years_of_experience
                experience_level = "0-2 years" if y <= 2 else "3-5 years" if y <= 5 else "5+ years"

        if resumes:
            primary_resume = resumes[0]
            rec_resume_id = primary_resume.id
            rec_resume_name = primary_resume.name

            # Check if skills exist in active version
            if primary_resume.versions:
                v = primary_resume.versions[-1]
                if v.skills:
                    skills = [s.skill_name for s in v.skills[:8]]

        return SearchDefaultsResponse(
            target_role=target_role or "Software Engineer",
            location=location,
            remote=False,
            experience_level=experience_level or "0-2 years",
            skills=skills,
            recommended_resume_id=rec_resume_id,
            recommended_resume_name=rec_resume_name,
        )

    @classmethod
    def create_search(
        cls,
        db: Session,
        user: User,
        query: JobSearchQuery,
        background_tasks: Optional[BackgroundTasks] = None,
        sync: bool = False,
    ) -> JobSearch:
        """
        Create JobSearch record and initiate agent workflow.
        If sync=True, executes search immediately within current session (ideal for tests & sync requests).
        Otherwise dispatches to Celery worker or background task.
        """
        # Verify resume ownership if specified
        if query.resume_id:
            resume = db.query(Resume).filter(Resume.id == query.resume_id, Resume.user_id == user.id).first()
            if not resume:
                raise NotFoundError("Specified resume not found or access denied.")

        search = JobSearch(
            user_id=user.id,
            resume_id=query.resume_id,
            query_role=query.role.strip(),
            location=query.location.strip() if query.location else None,
            remote=query.remote,
            experience_level=query.experience,
            employment_type=query.employment_type,
            salary_min=query.salary_min,
            salary_max=query.salary_max,
            skills_filter=json.dumps(query.skills) if query.skills else None,
            posted_within_days=query.posted_within_days or 14,
            status="queued",
        )
        db.add(search)
        db.commit()
        db.refresh(search)

        if sync:
            import asyncio
            asyncio.run(JobSearchAgent.execute_search(db=db, search_record=search, user=user))
            db.refresh(search)
            return search

        # Dispatch execution
        dispatched_via_celery = False
        try:
            from app.tasks.job_search_tasks import execute_job_search_task
            # Enqueue Celery task
            execute_job_search_task.delay(str(search.id), str(user.id))
            dispatched_via_celery = True
            logger.info(f"Dispatched JobSearch id={search.id} to Celery worker.")
        except Exception as e:
            logger.info(f"Celery unavailable ({e}); utilizing background task fallback.")

        if not dispatched_via_celery:
            # Fallback: run directly via background task or dedicated thread
            def _execute_sync(search_id_val: uuid.UUID, user_id_val: uuid.UUID):
                import asyncio
                from app.db.session import SessionLocal
                bg_db = SessionLocal()
                try:
                    s = bg_db.query(JobSearch).filter(JobSearch.id == search_id_val).first()
                    u = bg_db.query(User).filter(User.id == user_id_val).first()
                    if s and u:
                        asyncio.run(JobSearchAgent.execute_search(bg_db, s, u))
                except Exception as ex:
                    logger.error(f"Background job search error: {ex}")
                finally:
                    bg_db.close()

            if background_tasks:
                background_tasks.add_task(_execute_sync, search.id, user.id)
            else:
                import threading
                threading.Thread(target=_execute_sync, args=(search.id, user.id), daemon=True).start()

        return search

    @classmethod
    def get_search_by_id(cls, db: Session, user: User, search_id: uuid.UUID) -> JobSearch:
        """Fetch JobSearch record with strict tenant isolation."""
        search = db.query(JobSearch).filter(JobSearch.id == search_id, JobSearch.user_id == user.id).first()
        if not search:
            raise NotFoundError("Job search not found or access denied.")
        return search

    @classmethod
    def list_user_searches(cls, db: Session, user: User, limit: int = 20) -> List[JobSearch]:
        """Fetch user's historical searches."""
        return (
            db.query(JobSearch)
            .filter(JobSearch.user_id == user.id)
            .order_by(JobSearch.created_at.desc())
            .limit(limit)
            .all()
        )

    @classmethod
    def get_search_results(
        cls,
        db: Session,
        user: User,
        search_id: uuid.UUID,
        min_score: Optional[float] = None,
        remote_only: Optional[bool] = None,
        location: Optional[str] = None,
        sort_by: Optional[str] = "best_match",
    ) -> List[RankedJobOpportunity]:
        """Fetch, filter, and sort ranked job results for a specific search."""
        search = cls.get_search_by_id(db, user, search_id)

        query = (
            db.query(JobSearchResult, JobListing, Analysis)
            .join(JobListing, JobSearchResult.job_listing_id == JobListing.id)
            .outerjoin(Analysis, JobSearchResult.analysis_id == Analysis.id)
            .filter(JobSearchResult.search_id == search.id)
        )

        if min_score is not None:
            query = query.filter(JobSearchResult.overall_match_score >= min_score)
        if remote_only:
            query = query.filter(JobListing.remote_type == "remote")
        if location:
            query = query.filter(JobListing.location.ilike(f"%{location.strip()}%"))

        # Sorting
        if sort_by == "highest_skill":
            query = query.order_by(JobSearchResult.skill_score.desc())
        elif sort_by == "newest":
            query = query.order_by(JobListing.posted_at.desc().nullslast())
        elif sort_by == "experience":
            query = query.order_by(JobSearchResult.experience_score.desc())
        else:
            # Default best match: order by rank ascending
            query = query.order_by(JobSearchResult.rank.asc())

        records = query.all()

        # Query user saved jobs for fast bookmark status lookup
        saved_listing_ids = {
            s.job_listing_id: s.status
            for s in db.query(SavedJob).filter(SavedJob.user_id == user.id).all()
        }

        results: List[RankedJobOpportunity] = []
        for res, listing, analysis in records:
            matched_skills: List[str] = []
            missing_skills: List[MissingSkillDetail] = []
            partial_matches: List[str] = []

            if analysis:
                for sm in analysis.skill_matches:
                    if sm.match_type == "matched":
                        matched_skills.append(sm.job_skill.split(":")[-1].strip())
                    elif sm.match_type == "partial":
                        partial_matches.append(sm.job_skill.split(":")[-1].strip())

                for ms in analysis.missing_skills:
                    missing_skills.append(
                        MissingSkillDetail(
                            skill_name=ms.skill_name,
                            category=ms.category or "General",
                            priority=ms.priority,
                        )
                    )

            # Determine job description ID
            job_desc_id = listing.job_description_id or res.id

            is_saved = listing.id in saved_listing_ids
            app_status = saved_listing_ids.get(listing.id, "discovered")

            results.append(
                RankedJobOpportunity(
                    job_id=job_desc_id,
                    listing_id=listing.id,
                    title=listing.title,
                    company=listing.company,
                    location=listing.location,
                    remote_type=listing.remote_type,
                    employment_type=listing.employment_type,
                    salary_min=listing.salary_min,
                    salary_max=listing.salary_max,
                    currency=listing.currency,
                    source=listing.source,
                    url=listing.url,
                    posted_at=listing.posted_at.isoformat() if listing.posted_at else None,
                    description_snippet=listing.description[:250] + "..." if len(listing.description) > 250 else listing.description,
                    overall_match_score=round(res.overall_match_score, 1),
                    skill_score=round(res.skill_score, 1),
                    keyword_score=round(res.keyword_score, 1),
                    semantic_score=round(res.semantic_score, 1),
                    experience_score=round(res.experience_score, 1),
                    education_score=round(res.education_score, 1),
                    rank_score=round(res.rank_score, 1),
                    rank=res.rank,
                    matched_skills=matched_skills,
                    missing_skills=missing_skills,
                    partial_matches=partial_matches,
                    ai_explanation=res.ai_explanation,
                    is_saved=is_saved,
                    application_status=app_status,
                )
            )

        return results

    @classmethod
    def save_job(
        cls,
        db: Session,
        user: User,
        listing_id: uuid.UUID,
        status: str = "saved",
        notes: Optional[str] = None,
    ) -> SavedJob:
        """Save/bookmark a job opportunity with initial application status."""
        listing = db.query(JobListing).filter(JobListing.id == listing_id).first()
        if not listing:
            raise NotFoundError("Job listing not found.")

        saved = (
            db.query(SavedJob)
            .filter(SavedJob.user_id == user.id, SavedJob.job_listing_id == listing_id)
            .first()
        )
        if saved:
            saved.status = status
            if notes is not None:
                saved.notes = notes
        else:
            saved = SavedJob(
                user_id=user.id,
                job_listing_id=listing_id,
                status=status,
                notes=notes,
            )
            db.add(saved)

        db.commit()
        db.refresh(saved)
        return saved

    @classmethod
    def unsave_job(cls, db: Session, user: User, listing_id: uuid.UUID) -> None:
        """Remove saved job bookmark."""
        saved = (
            db.query(SavedJob)
            .filter(SavedJob.user_id == user.id, SavedJob.job_listing_id == listing_id)
            .first()
        )
        if saved:
            db.delete(saved)
            db.commit()

    @classmethod
    def update_application_status(
        cls,
        db: Session,
        user: User,
        listing_id: uuid.UUID,
        new_status: str,
        notes: Optional[str] = None,
    ) -> SavedJob:
        """Update job application status in the pipeline (applied, interview, rejected, offer)."""
        valid_statuses = {"discovered", "saved", "applied", "interview", "rejected", "offer"}
        if new_status not in valid_statuses:
            new_status = "saved"
        return cls.save_job(db, user, listing_id, status=new_status, notes=notes)

    @classmethod
    def list_saved_jobs(cls, db: Session, user: User) -> List[SavedJobResponse]:
        """Fetch all jobs saved by the user."""
        saved_records = (
            db.query(SavedJob, JobListing)
            .join(JobListing, SavedJob.job_listing_id == JobListing.id)
            .filter(SavedJob.user_id == user.id)
            .order_by(SavedJob.created_at.desc())
            .all()
        )

        return [
            SavedJobResponse(
                id=s.id,
                job_listing_id=listing.id,
                title=listing.title,
                company=listing.company,
                location=listing.location,
                remote_type=listing.remote_type,
                source=listing.source,
                url=listing.url,
                status=s.status,
                notes=s.notes,
                created_at=s.created_at.isoformat() if hasattr(s.created_at, "isoformat") else str(s.created_at),
                updated_at=s.updated_at.isoformat() if hasattr(s.updated_at, "isoformat") else str(s.updated_at),
            )
            for s, listing in saved_records
        ]

    @classmethod
    def get_top_recommendations(cls, db: Session, user: User, limit: int = 6) -> List[RankedJobOpportunity]:
        """Retrieve highest-scoring opportunities across all user searches."""
        latest_search = (
            db.query(JobSearch)
            .filter(JobSearch.user_id == user.id, JobSearch.status == "completed")
            .order_by(JobSearch.created_at.desc())
            .first()
        )
        recs = cls.get_search_results(db, user, latest_search.id, min_score=60.0)[:limit]
        if not recs:
            recs = cls.get_search_results(db, user, latest_search.id)[:limit]
        return recs
