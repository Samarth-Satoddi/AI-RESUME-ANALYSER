import uuid
from typing import List, Optional
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.logging import logger
from app.db.models import Analysis, LearningRoadmap, LearningRoadmapItem, User
from app.services.ai_provider import get_ai_provider


class RoadmapService:
    """Service managing personalized learning curriculum to bridge candidate skill gaps."""

    @classmethod
    def generate_roadmap_for_analysis(cls, db: Session, user: User, analysis_id: uuid.UUID) -> LearningRoadmap:
        """Create or replace learning roadmap for an analysis."""
        analysis = (
            db.query(Analysis)
            .filter(Analysis.id == analysis_id, Analysis.user_id == user.id)
            .first()
        )
        if not analysis:
            raise NotFoundError("Analysis not found or permission denied.")

        # Clean existing roadmap if any
        if analysis.learning_roadmap:
            db.delete(analysis.learning_roadmap)
            db.flush()

        # Extract missing skills from analysis
        missing_skills = [ms.skill_name for ms in analysis.missing_skills]
        job_title = analysis.job_description.title if analysis.job_description else "Software Engineer"

        # Generate stages via AI provider
        ai = get_ai_provider()
        stages = ai.generate_roadmap(missing_skills, job_title)

        roadmap = LearningRoadmap(
            analysis_id=analysis.id,
            title=f"Personalized Career Roadmap: {job_title}",
            description=f"Curriculum designed to close {len(missing_skills)} skill gaps identified for {job_title}.",
            estimated_days=sum(s.estimated_days for s in stages),
        )
        db.add(roadmap)
        db.flush()

        for idx, s in enumerate(stages):
            item = LearningRoadmapItem(
                learning_roadmap_id=roadmap.id,
                skill_name=s.skill_name,
                topic=s.topic,
                priority=s.priority,
                estimated_days=s.estimated_days,
                prerequisites=s.prerequisites,
                order_index=idx,
            )
            db.add(item)

        db.commit()
        db.refresh(roadmap)
        logger.info(f"Generated roadmap id={roadmap.id} with {len(stages)} stages for analysis_id={analysis.id}")
        return roadmap

    @classmethod
    def get_roadmap(cls, db: Session, user: User, analysis_id: uuid.UUID) -> LearningRoadmap:
        """Fetch roadmap for analysis."""
        analysis = (
            db.query(Analysis)
            .filter(Analysis.id == analysis_id, Analysis.user_id == user.id)
            .first()
        )
        if not analysis:
            raise NotFoundError("Analysis not found.")

        if not analysis.learning_roadmap:
            return cls.generate_roadmap_for_analysis(db, user, analysis_id)

        return analysis.learning_roadmap
