import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.services.job_service import JobCreateRequest, JobResponse, JobRequirementResponse, JobService

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def _to_job_response(job) -> JobResponse:
    return JobResponse(
        id=job.id,
        user_id=job.user_id,
        title=job.title,
        company=job.company,
        description=job.description,
        source_url=job.source_url,
        requirements=[
            JobRequirementResponse(
                id=r.id,
                requirement_type=r.requirement_type,
                requirement_text=r.requirement_text,
                normalized_skill_name=r.normalized_skill_name,
                category=r.category,
                is_required=r.is_required,
            )
            for r in job.requirements
        ],
        created_at=job.created_at.isoformat() if hasattr(job.created_at, "isoformat") else str(job.created_at),
        updated_at=job.updated_at.isoformat() if hasattr(job.updated_at, "isoformat") else str(job.updated_at),
    )


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED, summary="Create and parse a job posting")
def create_job(
    data: JobCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new job opportunity and automatically deconstruct requirements."""
    job = JobService.create_job(db=db, user=current_user, data=data)
    return _to_job_response(job)


@router.get("", response_model=List[JobResponse], status_code=status.HTTP_200_OK, summary="List candidate's saved jobs")
def list_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve all jobs created by the authenticated candidate."""
    jobs = JobService.get_user_jobs(db=db, user=current_user)
    return [_to_job_response(j) for j in jobs]


@router.get("/{job_id}", response_model=JobResponse, status_code=status.HTTP_200_OK, summary="Get job details and requirements")
def get_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve specific job with verified ownership."""
    job = JobService.get_job_by_id(db=db, user=current_user, job_id=job_id)
    return _to_job_response(job)


@router.delete("/{job_id}", status_code=status.HTTP_200_OK, summary="Delete a job posting")
def delete_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Permanently delete a saved job."""
    JobService.delete_job(db=db, user=current_user, job_id=job_id)
    return {"status": "success", "message": "Job description deleted successfully."}
