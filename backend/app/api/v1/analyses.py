import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.db.models import Analysis, User
from app.db.session import get_db
from app.services.analysis_orchestrator import AnalysisOrchestrator, FullAnalysisResponse
from app.services.interview_service import InterviewService
from app.services.roadmap_service import RoadmapService

router = APIRouter(prefix="/analyses", tags=["Analyses"])


class RunAnalysisRequest(BaseModel):
    resume_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None


class AnalysisListItem(BaseModel):
    id: uuid.UUID
    resume_id: uuid.UUID
    resume_name: str
    job_id: Optional[uuid.UUID] = None
    job_title: Optional[str] = None
    overall_score: Optional[float] = None
    ats_score: Optional[float] = None
    skill_score: Optional[float] = None
    status: str
    created_at: str


class SkillMatchItem(BaseModel):
    skill_name: str
    resume_skill: Optional[str] = None
    job_skill: Optional[str] = None
    match_type: str
    similarity_score: float
    importance: Optional[str] = None


class MissingSkillItem(BaseModel):
    skill_name: str
    category: Optional[str] = None
    priority: str
    reason: Optional[str] = None


class RecommendationItem(BaseModel):
    title: str
    description: str
    priority: str
    recommendation_type: str


class RoadmapItemDto(BaseModel):
    id: uuid.UUID
    skill_name: str
    topic: str
    priority: str
    estimated_days: int
    prerequisites: Optional[List[str]] = None
    order_index: int


class RoadmapResponseDto(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    estimated_days: Optional[int] = None
    items: List[RoadmapItemDto]


class InterviewQuestionDto(BaseModel):
    id: uuid.UUID
    category: str
    question: str
    difficulty: str
    why_it_matters: Optional[str] = None
    answer_guidance: Optional[str] = None


class AnalysisDetailResponse(BaseModel):
    id: uuid.UUID
    status: str
    overall_score: Optional[float] = None
    resume_score: Optional[float] = None
    ats_score: Optional[float] = None
    skill_score: Optional[float] = None
    keyword_score: Optional[float] = None
    semantic_score: Optional[float] = None
    experience_score: Optional[float] = None
    education_score: Optional[float] = None
    resume_id: uuid.UUID
    resume_name: str
    job_id: Optional[uuid.UUID] = None
    job_title: Optional[str] = None
    skill_matches: List[SkillMatchItem] = []
    missing_skills: List[MissingSkillItem] = []
    recommendations: List[RecommendationItem] = []
    created_at: str
    completed_at: Optional[str] = None


@router.post("", response_model=FullAnalysisResponse, status_code=status.HTTP_201_CREATED, summary="Trigger complete analysis or matching pipeline")
def run_analysis(
    data: RunAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run full deterministic evaluation, ATS audit, and optional job matching."""
    return AnalysisOrchestrator.run_full_pipeline(
        db=db,
        user=current_user,
        resume_id=data.resume_id,
        job_id=data.job_id,
    )


@router.get("", response_model=List[AnalysisListItem], status_code=status.HTTP_200_OK, summary="List candidate's analysis history")
def list_analyses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve all historical evaluations for authenticated candidate."""
    analyses = (
        db.query(Analysis)
        .filter(Analysis.user_id == current_user.id)
        .order_by(Analysis.created_at.desc())
        .all()
    )
    result = []
    for a in analyses:
        res_name = a.resume_version.resume.name if a.resume_version and a.resume_version.resume else "Resume"
        res_id = a.resume_version.resume_id if a.resume_version else uuid.uuid4()
        j_title = a.job_description.title if a.job_description else None
        result.append(
            AnalysisListItem(
                id=a.id,
                resume_id=res_id,
                resume_name=res_name,
                job_id=a.job_description_id,
                job_title=j_title,
                overall_score=a.overall_score,
                ats_score=a.ats_score,
                skill_score=a.skill_score,
                status=a.status,
                created_at=a.created_at.isoformat(),
            )
        )
    return result


@router.get("/{analysis_id}", response_model=AnalysisDetailResponse, status_code=status.HTTP_200_OK, summary="Get full analysis breakdown")
def get_analysis_detail(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch complete score breakdown, matched/missing skills, and recommendations."""
    a = (
        db.query(Analysis)
        .filter(Analysis.id == analysis_id, Analysis.user_id == current_user.id)
        .first()
    )
    if not a:
        raise NotFoundError("Analysis record not found.")

    res_name = a.resume_version.resume.name if a.resume_version and a.resume_version.resume else "Resume"
    res_id = a.resume_version.resume_id if a.resume_version else uuid.uuid4()

    return AnalysisDetailResponse(
        id=a.id,
        status=a.status,
        overall_score=a.overall_score,
        resume_score=a.resume_score,
        ats_score=a.ats_score,
        skill_score=a.skill_score,
        keyword_score=a.keyword_score,
        semantic_score=a.semantic_score,
        experience_score=a.experience_score,
        education_score=a.education_score,
        resume_id=res_id,
        resume_name=res_name,
        job_id=a.job_description_id,
        job_title=a.job_description.title if a.job_description else None,
        skill_matches=[
            SkillMatchItem(
                skill_name=sm.skill_name,
                resume_skill=sm.resume_skill,
                job_skill=sm.job_skill,
                match_type=sm.match_type,
                similarity_score=sm.similarity_score,
                importance=sm.importance,
            )
            for sm in a.skill_matches
        ],
        missing_skills=[
            MissingSkillItem(
                skill_name=ms.skill_name,
                category=ms.category,
                priority=ms.priority,
                reason=ms.reason,
            )
            for ms in a.missing_skills
        ],
        recommendations=[
            RecommendationItem(
                title=r.title,
                description=r.description,
                priority=r.priority,
                recommendation_type=r.recommendation_type,
            )
            for r in a.recommendations
        ],
        created_at=a.created_at.isoformat(),
        completed_at=a.completed_at.isoformat() if a.completed_at else None,
    )


@router.get("/{analysis_id}/roadmap", response_model=RoadmapResponseDto, status_code=status.HTTP_200_OK, summary="Get personalized learning roadmap")
def get_roadmap(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve structured learning stages to bridge identified skill gaps."""
    roadmap = RoadmapService.get_roadmap(db=db, user=current_user, analysis_id=analysis_id)
    return RoadmapResponseDto(
        id=roadmap.id,
        title=roadmap.title,
        description=roadmap.description,
        estimated_days=roadmap.estimated_days,
        items=[
            RoadmapItemDto(
                id=i.id,
                skill_name=i.skill_name,
                topic=i.topic,
                priority=i.priority,
                estimated_days=i.estimated_days,
                prerequisites=i.prerequisites if isinstance(i.prerequisites, list) else [],
                order_index=i.order_index,
            )
            for i in roadmap.items
        ],
    )


@router.get("/{analysis_id}/interview", response_model=List[InterviewQuestionDto], status_code=status.HTTP_200_OK, summary="Get tailored interview prep questions")
def get_interview_questions(
    analysis_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve tailored interview preparation questions with answer guidance."""
    questions = InterviewService.get_interview_questions(db=db, user=current_user, analysis_id=analysis_id)
    return [
        InterviewQuestionDto(
            id=q.id,
            category=q.category,
            question=q.question,
            difficulty=q.difficulty,
            why_it_matters=q.why_it_matters,
            answer_guidance=q.answer_guidance,
        )
        for q in questions
    ]
