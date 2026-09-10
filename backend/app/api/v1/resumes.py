from typing import Optional
import uuid
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.resume import (
    ResumeListResponse,
    ResumeResponse,
    ResumeSectionsListResponse,
    ResumeTextResponse,
    ResumeUpdateNameRequest,
)
from app.services.file_validator import MIME_TYPE_MAP
from app.services.resume_service import ResumeService
from app.services.storage_service import StorageService

router = APIRouter(prefix="/resumes", tags=["Resumes"])


@router.post(
    "/upload",
    response_model=ResumeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new candidate resume",
)
async def upload_resume(
    file: UploadFile = File(..., description="PDF, DOCX, or TXT resume document"),
    name: Optional[str] = Form(None, description="Optional custom display name"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Securely upload, validate magic signatures, store, and record a resume document."""
    return await ResumeService.upload_resume(
        db=db,
        user=current_user,
        file=file,
        custom_name=name,
    )


@router.get(
    "",
    response_model=ResumeListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all resumes for the authenticated candidate",
)
def list_resumes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve all resume documents owned by the active candidate."""
    items = ResumeService.list_resumes(db=db, user=current_user)
    return ResumeListResponse(items=items, total=len(items))


@router.get(
    "/{resume_id}",
    response_model=ResumeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get resume metadata by ID",
)
def get_resume(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve metadata for a specific owned resume."""
    resume = ResumeService.get_resume(db=db, user=current_user, resume_id=resume_id)
    return ResumeService.to_response_dto(resume)


@router.patch(
    "/{resume_id}",
    response_model=ResumeResponse,
    status_code=status.HTTP_200_OK,
    summary="Rename an uploaded resume",
)
def update_resume_name(
    resume_id: uuid.UUID,
    data: ResumeUpdateNameRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change the display name of an owned resume."""
    return ResumeService.update_resume_name(
        db=db,
        user=current_user,
        resume_id=resume_id,
        new_name=data.name,
    )


@router.patch(
    "/{resume_id}/primary",
    response_model=ResumeResponse,
    status_code=status.HTTP_200_OK,
    summary="Set a resume as the candidate's primary document",
)
def set_primary_resume(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Atomically set this resume as primary and unset all others."""
    return ResumeService.set_primary_resume(db=db, user=current_user, resume_id=resume_id)


@router.get(
    "/{resume_id}/download",
    status_code=status.HTTP_200_OK,
    summary="Download original resume file",
)
def download_resume(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download the stored resume file with verified ownership."""
    resume = ResumeService.get_resume(db=db, user=current_user, resume_id=resume_id)
    abs_path = StorageService.get_absolute_path(resume.storage_path)

    media_type = MIME_TYPE_MAP.get(f".{resume.file_type}", "application/octet-stream")
    return FileResponse(
        path=abs_path,
        filename=resume.original_filename,
        media_type=media_type,
    )


@router.post(
    "/{resume_id}/parse",
    response_model=ResumeSectionsListResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract text and detect sections for resume",
)
def parse_resume(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger text extraction and heuristic section detection for a candidate resume."""
    return ResumeService.parse_resume(db=db, user=current_user, resume_id=resume_id)


@router.get(
    "/{resume_id}/sections",
    response_model=ResumeSectionsListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get detected sections for resume",
)
def get_resume_sections(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve structured sections (e.g. experience, skills, education) for a candidate resume."""
    return ResumeService.get_resume_sections(db=db, user=current_user, resume_id=resume_id)


@router.get(
    "/{resume_id}/text",
    response_model=ResumeTextResponse,
    status_code=status.HTTP_200_OK,
    summary="Get extracted and normalized resume text",
)
def get_resume_text(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve the normalized text extracted from the candidate's resume."""
    return ResumeService.get_resume_text(db=db, user=current_user, resume_id=resume_id)


@router.get(
    "/{resume_id}/skills",
    status_code=status.HTTP_200_OK,
    summary="Get extracted skills for resume",
)
def get_resume_skills(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve taxonomy-categorized skills identified in candidate's resume."""
    resume = ResumeService.get_resume(db=db, user=current_user, resume_id=resume_id)
    active_version = resume.versions[-1] if resume.versions else None
    if not active_version:
        return []

    # If no skills yet, extract them
    if not active_version.skills:
        from app.services.skill_extractor import SkillExtractor
        extractor = SkillExtractor.get_instance()
        skills = extractor.extract_skills(active_version.extracted_text or "")
        extractor.save_resume_skills(db, active_version, skills)
        db.refresh(active_version)

    return [
        {
            "id": s.id,
            "skill_name": s.skill_name,
            "normalized_skill_name": s.normalized_skill_name,
            "category": s.category,
            "proficiency": s.proficiency,
            "years_used": s.years_used,
        }
        for s in active_version.skills
    ]


@router.get(
    "/{resume_id}/entities",
    status_code=status.HTTP_200_OK,
    summary="Get structured entities for resume",
)
def get_resume_entities(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve parsed experiences, education, projects, certifications, and contact info."""
    resume = ResumeService.get_resume(db=db, user=current_user, resume_id=resume_id)
    active_version = resume.versions[-1] if resume.versions else None
    if not active_version:
        return {"experiences": [], "education": [], "projects": [], "certifications": [], "contact": {}}

    # If not yet extracted, extract entities
    if not active_version.experiences and not active_version.education:
        from app.services.entity_extractor import EntityExtractor
        ee = EntityExtractor()
        ee.process_and_save_entities(
            db=db,
            resume_version=active_version,
            sections=active_version.sections,
            full_text=active_version.extracted_text or "",
        )
        db.refresh(active_version)

    from app.services.entity_extractor import EntityExtractor
    contact = EntityExtractor().extract_contact_info(active_version.extracted_text or "")

    return {
        "contact": contact.model_dump(),
        "experiences": [
            {
                "id": e.id,
                "company": e.company,
                "job_title": e.job_title,
                "location": e.location,
                "start_date": e.start_date,
                "end_date": e.end_date,
                "is_current": e.is_current,
                "description": e.description,
            }
            for e in active_version.experiences
        ],
        "education": [
            {
                "id": ed.id,
                "institution": ed.institution,
                "degree": ed.degree,
                "field_of_study": ed.field_of_study,
                "start_date": ed.start_date,
                "end_date": ed.end_date,
                "grade": ed.grade,
            }
            for ed in active_version.education
        ],
        "projects": [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "github_url": p.github_url,
            }
            for p in active_version.projects
        ],
        "certifications": [
            {
                "id": c.id,
                "name": c.name,
                "issuing_organization": c.issuing_organization,
                "issue_date": c.issue_date,
            }
            for c in active_version.certifications
        ],
    }


@router.get(
    "/{resume_id}/score",
    status_code=status.HTTP_200_OK,
    summary="Get comprehensive resume quality & ATS evaluation",
)
def get_resume_score(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run deterministic multi-component score and ATS report for a resume."""
    from app.services.analysis_orchestrator import AnalysisOrchestrator
    return AnalysisOrchestrator.run_full_pipeline(
        db=db,
        user=current_user,
        resume_id=resume_id,
        job_id=None,
    )


@router.delete(
    "/{resume_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a resume and its stored file",
)
def delete_resume(
    resume_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Permanently delete a resume, all child versions, and its physical file."""
    ResumeService.delete_resume(db=db, user=current_user, resume_id=resume_id)
    return {"status": "success", "message": "Resume deleted successfully."}


