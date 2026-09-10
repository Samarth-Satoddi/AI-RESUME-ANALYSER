import uuid
from typing import Dict, List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.logging import logger
from app.db.models import Analysis, JobDescription, Resume, ResumeVersion, User
from app.services.entity_extractor import EntityExtractor
from app.services.interview_service import InterviewService
from app.services.job_service import JobService
from app.services.matching_engine import MatchingEngine
from app.services.roadmap_service import RoadmapService
from app.services.scoring_engine import ScoreBreakdown, ScoringEngine
from app.services.skill_extractor import SkillExtractor


class FullAnalysisResponse(BaseModel):
    analysis_id: Optional[uuid.UUID] = None
    resume_id: uuid.UUID
    resume_name: str
    job_id: Optional[uuid.UUID] = None
    job_title: Optional[str] = None
    overall_score: float
    ats_score: float
    skill_score: float
    experience_score: float
    education_score: float
    keyword_score: float
    semantic_score: float
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    skills_detected_count: int
    matched_skills: List[str] = []
    missing_skills: List[dict] = []
    roadmap_item_count: int = 0
    interview_question_count: int = 0


class AnalysisOrchestrator:
    """
    Unified analysis pipeline orchestrator.
    Executes text extraction, section detection, skill & entity extraction,
    deterministic ATS scoring, job matching, AI feedback, roadmap generation,
    and interview prep in a transactional, dependency-ordered sequence.
    """

    @classmethod
    def run_full_pipeline(
        cls,
        db: Session,
        user: User,
        resume_id: uuid.UUID,
        job_id: Optional[uuid.UUID] = None,
    ) -> FullAnalysisResponse:
        """Run the end-to-end resume evaluation and optional job-matching pipeline."""
        logger.info(f"Starting full pipeline: resume_id={resume_id} job_id={job_id} user={user.id}")

        # 1. Fetch and verify resume ownership
        resume = (
            db.query(Resume)
            .filter(Resume.id == resume_id, Resume.user_id == user.id)
            .first()
        )
        if not resume:
            raise NotFoundError("Resume not found or permission denied.")

        active_version = resume.versions[-1] if resume.versions else None
        if not active_version:
            raise NotFoundError("Active resume version not found.")

        # 2. Extract Skills (Phase 7)
        skill_extractor = SkillExtractor.get_instance()
        skills = skill_extractor.extract_skills(active_version.extracted_text or "")
        saved_skills = skill_extractor.save_resume_skills(db, active_version, skills)

        # 3. Extract Entities (Phase 8)
        entity_extractor = EntityExtractor()
        contact_info = entity_extractor.extract_contact_info(active_version.extracted_text or "")
        entity_extractor.process_and_save_entities(
            db=db,
            resume_version=active_version,
            sections=active_version.sections,
            full_text=active_version.extracted_text or "",
        )

        # 4. Deterministic Scoring & ATS Analysis (Phases 9 & 10)
        score_breakdown: ScoreBreakdown = ScoringEngine.evaluate_resume(
            skills=saved_skills,
            experiences=active_version.experiences,
            educations=active_version.education,
            projects=active_version.projects,
            sections=active_version.sections,
            contact_info=contact_info.model_dump(),
            full_text=active_version.extracted_text or "",
        )

        analysis_record: Optional[Analysis] = None
        matched_skills: List[str] = []
        missing_skills: List[dict] = []
        roadmap_count = 0
        interview_count = 0

        # 5. Job Matching Pipeline (Phases 11-17) if job specified
        if job_id:
            job = (
                db.query(JobDescription)
                .filter(JobDescription.id == job_id, JobDescription.user_id == user.id)
                .first()
            )
            if not job:
                raise NotFoundError("Target job not found or permission denied.")

            # Run matching engine
            analysis_record = MatchingEngine.match_resume_to_job(db, active_version, job)

            # Generate roadmap
            roadmap = RoadmapService.generate_roadmap_for_analysis(db, user, analysis_record.id)
            roadmap_count = len(roadmap.items) if roadmap else 0

            # Generate interview questions
            questions = InterviewService.generate_interview_questions(db, user, analysis_record.id)
            interview_count = len(questions)

            matched_skills = [
                sm.job_skill.split(":")[-1].strip()
                for sm in analysis_record.skill_matches
                if sm.match_type == "matched"
            ]
            missing_skills = [
                {"name": ms.skill_name, "priority": ms.priority, "category": ms.category}
                for ms in analysis_record.missing_skills
            ]

        overall_score = analysis_record.overall_score if analysis_record else score_breakdown.overall_score
        ats_score = score_breakdown.ats_score
        skill_score = score_breakdown.skill_score

        logger.info(f"Pipeline completed: overall_score={overall_score}, ats_score={ats_score}")

        return FullAnalysisResponse(
            analysis_id=analysis_record.id if analysis_record else None,
            resume_id=resume.id,
            resume_name=resume.name,
            job_id=job_id,
            job_title=job.title if job_id and 'job' in locals() and job else None,
            overall_score=overall_score,
            ats_score=ats_score,
            skill_score=skill_score,
            experience_score=score_breakdown.experience_score,
            education_score=score_breakdown.education_score,
            keyword_score=analysis_record.keyword_score if analysis_record else score_breakdown.ats_score,
            semantic_score=analysis_record.semantic_score if analysis_record else 75.0,
            strengths=score_breakdown.strengths,
            weaknesses=score_breakdown.weaknesses,
            recommendations=score_breakdown.recommendations,
            skills_detected_count=len(saved_skills),
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            roadmap_item_count=roadmap_count,
            interview_question_count=interview_count,
        )
