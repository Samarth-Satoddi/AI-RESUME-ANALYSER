import uuid
from typing import List
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.logging import logger
from app.db.models import Analysis, InterviewQuestion, User
from app.services.ai_provider import get_ai_provider


class InterviewService:
    """Service managing generation and retrieval of targeted interview preparation questions."""

    @classmethod
    def generate_interview_questions(cls, db: Session, user: User, analysis_id: uuid.UUID) -> List[InterviewQuestion]:
        """Generate targeted interview questions based on candidate resume and target job."""
        analysis = (
            db.query(Analysis)
            .filter(Analysis.id == analysis_id, Analysis.user_id == user.id)
            .first()
        )
        if not analysis:
            raise NotFoundError("Analysis not found or permission denied.")

        # Clean previous questions
        db.query(InterviewQuestion).filter(InterviewQuestion.analysis_id == analysis.id).delete()

        # Gather skills from resume version
        skills = [s.skill_name for s in analysis.resume_version.skills] if analysis.resume_version else []
        job_title = analysis.job_description.title if analysis.job_description else "Software Engineer"

        ai = get_ai_provider()
        generated = ai.generate_interview_questions(skills, job_title)

        created: List[InterviewQuestion] = []
        for q in generated:
            item = InterviewQuestion(
                analysis_id=analysis.id,
                category=q.category,
                question=q.question,
                difficulty=q.difficulty,
                why_it_matters=q.why_it_matters,
                answer_guidance=q.answer_guidance,
            )
            db.add(item)
            created.append(item)

        db.commit()
        logger.info(f"Generated {len(created)} interview questions for analysis_id={analysis.id}")
        return created

    @classmethod
    def get_interview_questions(cls, db: Session, user: User, analysis_id: uuid.UUID) -> List[InterviewQuestion]:
        """Fetch questions, generating them on demand if not present."""
        analysis = (
            db.query(Analysis)
            .filter(Analysis.id == analysis_id, Analysis.user_id == user.id)
            .first()
        )
        if not analysis:
            raise NotFoundError("Analysis not found.")

        questions = (
            db.query(InterviewQuestion)
            .filter(InterviewQuestion.analysis_id == analysis.id)
            .all()
        )

        if not questions:
            return cls.generate_interview_questions(db, user, analysis_id)

        return questions
