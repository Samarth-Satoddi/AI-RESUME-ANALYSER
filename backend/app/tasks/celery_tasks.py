import os
import uuid
from typing import Optional
from celery import Celery

from app.core.config import settings
from app.core.logging import logger
from app.db.session import SessionLocal
from app.db.models import User
from app.services.analysis_orchestrator import AnalysisOrchestrator

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "resume_analyzer_tasks",
    broker=redis_url,
    backend=redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)


@celery_app.task(name="tasks.run_full_analysis", bind=True, max_retries=2)
def run_full_analysis_task(self, user_id_str: str, resume_id_str: str, job_id_str: Optional[str] = None):
    """Background asynchronous Celery task for running compute-heavy resume analysis."""
    logger.info(f"[Celery] Task started: task_id={self.request.id} resume_id={resume_id_str}")
    db = SessionLocal()
    try:
        user_id = uuid.UUID(user_id_str)
        resume_id = uuid.UUID(resume_id_str)
        job_id = uuid.UUID(job_id_str) if job_id_str else None

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.error(f"[Celery] User not found: {user_id}")
            return {"status": "failed", "error": "User not found"}

        result = AnalysisOrchestrator.run_full_pipeline(
            db=db,
            user=user,
            resume_id=resume_id,
            job_id=job_id,
        )
        return {"status": "completed", "data": result.model_dump(mode="json")}
    except Exception as exc:
        logger.error(f"[Celery] Analysis failed: {exc}")
        db.rollback()
        raise self.retry(exc=exc, countdown=5)
    finally:
        db.close()
