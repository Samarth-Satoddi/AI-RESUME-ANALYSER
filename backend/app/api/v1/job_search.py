from typing import List, Optional
import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.job_search.schemas import (
    JobSearchQuery,
    RankedJobOpportunity,
    SavedJobResponse,
    SearchDefaultsResponse,
    SearchListItem,
    SearchResultsResponse,
    SearchStatusResponse,
)
from app.services.job_search_service import JobSearchService

router = APIRouter(prefix="/job-search", tags=["Job Search Agent"])


class UpdateStatusRequest(BaseModel):
    status: str  # discovered, saved, applied, interview, rejected, offer
    notes: Optional[str] = None


@router.get(
    "/defaults",
    response_model=SearchDefaultsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get smart search defaults inferred from candidate profile and active resume",
)
def get_search_defaults(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return JobSearchService.get_search_defaults(db=db, user=current_user)


@router.post(
    "/search",
    response_model=SearchStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Initiate autonomous multi-source job search and matching workflow",
)
def start_job_search(
    query: JobSearchQuery,
    background_tasks: BackgroundTasks,
    sync: bool = Query(False, description="Run search synchronously"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    search = JobSearchService.create_search(
        db=db,
        user=current_user,
        query=query,
        background_tasks=background_tasks,
        sync=sync,
    )
    return SearchStatusResponse(
        search_id=search.id,
        status=search.status,
        jobs_found=search.jobs_found,
        jobs_analyzed=search.jobs_analyzed,
        jobs_matched=search.jobs_matched,
        error_message=search.error_message,
        created_at=search.created_at.isoformat() if hasattr(search.created_at, "isoformat") else str(search.created_at),
        updated_at=search.updated_at.isoformat() if hasattr(search.updated_at, "isoformat") else str(search.updated_at),
    )


@router.get(
    "/searches",
    response_model=List[SearchListItem],
    status_code=status.HTTP_200_OK,
    summary="List candidate's past job searches",
)
def list_searches(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    searches = JobSearchService.list_user_searches(db=db, user=current_user)
    return [
        SearchListItem(
            id=s.id,
            query_role=s.query_role,
            location=s.location,
            remote=s.remote,
            status=s.status,
            jobs_found=s.jobs_found,
            jobs_matched=s.jobs_matched,
            created_at=s.created_at.isoformat() if hasattr(s.created_at, "isoformat") else str(s.created_at),
        )
        for s in searches
    ]


@router.get(
    "/searches/{search_id}",
    response_model=SearchStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Poll job search progress and execution status",
)
def get_search_status(
    search_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = JobSearchService.get_search_by_id(db=db, user=current_user, search_id=search_id)
    return SearchStatusResponse(
        search_id=s.id,
        status=s.status,
        jobs_found=s.jobs_found,
        jobs_analyzed=s.jobs_analyzed,
        jobs_matched=s.jobs_matched,
        error_message=s.error_message,
        created_at=s.created_at.isoformat() if hasattr(s.created_at, "isoformat") else str(s.created_at),
        updated_at=s.updated_at.isoformat() if hasattr(s.updated_at, "isoformat") else str(s.updated_at),
    )


@router.get(
    "/searches/{search_id}/results",
    response_model=SearchResultsResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve ranked job opportunities with filtering and sorting",
)
def get_search_results(
    search_id: uuid.UUID,
    min_score: Optional[float] = Query(None, ge=0, le=100),
    remote_only: Optional[bool] = Query(None),
    location: Optional[str] = Query(None),
    sort_by: Optional[str] = Query("best_match", pattern="^(best_match|highest_skill|newest|experience)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = JobSearchService.get_search_by_id(db=db, user=current_user, search_id=search_id)
    results = JobSearchService.get_search_results(
        db=db,
        user=current_user,
        search_id=search_id,
        min_score=min_score,
        remote_only=remote_only,
        location=location,
        sort_by=sort_by,
    )
    return SearchResultsResponse(
        search_id=s.id,
        query={
            "role": s.query_role,
            "location": s.location,
            "remote": s.remote,
            "experience": s.experience_level,
        },
        status=s.status,
        total_results=len(results),
        results=results,
    )


@router.post(
    "/jobs/{listing_id}/save",
    response_model=SavedJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save a job opportunity to saved bookmarks",
)
def save_job(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    saved = JobSearchService.save_job(db=db, user=current_user, listing_id=listing_id)
    return SavedJobResponse(
        id=saved.id,
        job_listing_id=saved.listing.id,
        title=saved.listing.title,
        company=saved.listing.company,
        location=saved.listing.location,
        remote_type=saved.listing.remote_type,
        source=saved.listing.source,
        url=saved.listing.url,
        status=saved.status,
        notes=saved.notes,
        created_at=saved.created_at.isoformat() if hasattr(saved.created_at, "isoformat") else str(saved.created_at),
        updated_at=saved.updated_at.isoformat() if hasattr(saved.updated_at, "isoformat") else str(saved.updated_at),
    )


@router.delete(
    "/jobs/{listing_id}/save",
    status_code=status.HTTP_200_OK,
    summary="Remove a job bookmark",
)
def unsave_job(
    listing_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    JobSearchService.unsave_job(db=db, user=current_user, listing_id=listing_id)
    return {"status": "success", "message": "Job unsaved successfully."}


@router.patch(
    "/jobs/{listing_id}/status",
    response_model=SavedJobResponse,
    status_code=status.HTTP_200_OK,
    summary="Update application tracking status (saved, applied, interview, rejected, offer)",
)
def update_application_status(
    listing_id: uuid.UUID,
    data: UpdateStatusRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    saved = JobSearchService.update_application_status(
        db=db,
        user=current_user,
        listing_id=listing_id,
        new_status=data.status,
        notes=data.notes,
    )
    return SavedJobResponse(
        id=saved.id,
        job_listing_id=saved.listing.id,
        title=saved.listing.title,
        company=saved.listing.company,
        location=saved.listing.location,
        remote_type=saved.listing.remote_type,
        source=saved.listing.source,
        url=saved.listing.url,
        status=saved.status,
        notes=saved.notes,
        created_at=saved.created_at.isoformat() if hasattr(saved.created_at, "isoformat") else str(saved.created_at),
        updated_at=saved.updated_at.isoformat() if hasattr(saved.updated_at, "isoformat") else str(saved.updated_at),
    )


@router.get(
    "/saved",
    response_model=List[SavedJobResponse],
    status_code=status.HTTP_200_OK,
    summary="List candidate's saved job bookmarks and tracked applications",
)
def list_saved_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return JobSearchService.list_saved_jobs(db=db, user=current_user)


@router.get(
    "/top-recommendations",
    response_model=List[RankedJobOpportunity],
    status_code=status.HTTP_200_OK,
    summary="Retrieve candidate's top ranked job opportunities based on resume alignment",
)
def get_top_recommendations(
    limit: int = Query(6, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return JobSearchService.get_top_recommendations(db=db, user=current_user, limit=limit)
