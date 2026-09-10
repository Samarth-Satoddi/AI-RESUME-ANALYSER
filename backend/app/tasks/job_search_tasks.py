import asyncio
import os
import uuid
from typing import Optional

from app.core.logging import logger
from app.db.models import JobSearch, User
from app.db.session import SessionLocal
from app.job_search.agent import JobSearchAgent
from app.tasks.celery_tasks import celery_app


@celery_app.task(name="tasks.execute_job_search", bind=True, max_retries=1)
def execute_job_search_task(self, search_id_str: str, user_id_str: str):
    """
    Celery background worker task for executing end-to-end Job Search Agent discovery,
    normalization, deduplication, requirement parsing, and ranking.
    """
    logger.info(f"[Celery] Commencing job search task: search_id={search_id_str} user_id={user_id_str}")
    db = SessionLocal()
    try:
        search_id = uuid.UUID(search_id_str)
        user_id = uuid.UUID(user_id_str)

        search = db.query(JobSearch).filter(JobSearch.id == search_id).first()
        user = db.query(User).filter(User.id == user_id).first()

        if not search or not user:
            logger.error(f"[Celery] Entity missing: search={search is not None} user={user is not None}")
            return {"status": "failed", "error": "Search or user not found."}

        # Run asynchronous agent execution within sync Celery worker process
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            completed_search = loop.run_until_complete(
                JobSearchAgent.execute_search(db=db, search_record=search, user=user)
            )
            return {
                "status": completed_search.status,
                "jobs_found": completed_search.jobs_found,
                "jobs_matched": completed_search.jobs_matched,
            }
        finally:
            loop.close()

    except Exception as exc:
        logger.error(f"[Celery] Job search task error: {exc}")
        db.rollback()
        raise self.retry(exc=exc, countdown=5)
    finally:
        db.close()
