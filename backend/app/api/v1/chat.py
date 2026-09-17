import uuid
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.db.models import User
from app.ai.intent.classifier import IntentClassifier, AssistantIntent
from app.ai.resume_context.builder import ResumeContextBuilder
from app.ai.llm.inference import AssistantInferenceService
from app.core.logging import logger

router = APIRouter(prefix="/chat", tags=["AI Chat Assistant"])

inference_service = AssistantInferenceService()


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    resume_id: uuid.UUID = Field(..., description="ID of the selected resume to query against")
    message: str = Field(..., min_length=1, max_length=2000, description="User's query or bullet point")
    job_id: Optional[uuid.UUID] = Field(None, description="Optional job description context")
    conversation_history: Optional[List[ChatMessage]] = Field(default=None, description="Prior conversation turns for follow-ups")


class SourcesInfo(BaseModel):
    resume: bool
    analysis: bool
    job: bool


class BulletImprovementInfo(BaseModel):
    original: str
    improved: str
    rationale: str


class ChatResponse(BaseModel):
    intent: str
    answer: str
    resume_id: str
    sources: SourcesInfo
    bullet_improvement: Optional[BulletImprovementInfo] = None


@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK, summary="Ask questions about a resume or refactor bullet points")
def chat_with_assistant(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Handles user inquiries regarding an authenticated user's selected resume, ATS score,
    skills, job match, or bullet point refactorings using the local Hugging Face model.
    """
    # 1. Intent Detection
    intent, intent_meta = IntentClassifier.classify(request.message)
    logger.info(f"Chat request | User: {current_user.id} | Intent: {intent.value} | Reason: {intent_meta.get('reason')}")

    # 2. Selected Resume Verification & Context Building
    context_builder = ResumeContextBuilder(db=db, user_id=current_user.id)
    try:
        resume_context = context_builder.build_context(
            resume_id=request.resume_id,
            intent=intent,
            job_id=request.job_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc)
        )
    except Exception as exc:
        logger.error(f"Error building resume context: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve resume context for assistant."
        )

    # 3. Format conversation history
    history_dicts = None
    if request.conversation_history:
        history_dicts = [{"role": m.role, "content": m.content} for m in request.conversation_history]

    # 4. LLM Generation
    extracted_bullet = intent_meta.get("extracted_bullet")
    try:
        result = inference_service.run_inference(
            intent=intent,
            user_message=request.message,
            resume_context=resume_context,
            conversation_history=history_dicts,
            extracted_bullet=extracted_bullet,
        )
    except RuntimeError as exc:
        logger.error(f"LLM inference failure: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI Resume Assistant is currently unavailable because the local language model could not be loaded."
        )
    except Exception as exc:
        logger.error(f"Unexpected error during assistant generation: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating the assistant response."
        )

    bullet_improvement = None
    if result.get("bullet_improvement"):
        bullet_improvement = BulletImprovementInfo(**result["bullet_improvement"])

    return ChatResponse(
        intent=result["intent"],
        answer=result["answer"],
        resume_id=str(request.resume_id),
        sources=SourcesInfo(**result["sources"]),
        bullet_improvement=bullet_improvement,
    )
