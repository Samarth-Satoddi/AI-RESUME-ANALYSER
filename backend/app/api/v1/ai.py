from typing import Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.db.models import User
from app.services.ai_provider import BulletImprovement, get_ai_provider

router = APIRouter(prefix="/ai", tags=["AI"])


class ImproveBulletRequest(BaseModel):
    bullet: str = Field(..., min_length=5, max_length=1000, description="Raw resume bullet point")
    target_role: Optional[str] = Field(None, description="Optional target job title")


@router.post("/improve-bullet", response_model=BulletImprovement, status_code=status.HTTP_200_OK, summary="Enhance a resume bullet using STAR methodology")
def improve_bullet(
    data: ImproveBulletRequest,
    current_user: User = Depends(get_current_user),
):
    """Refactor a passive resume bullet into an action-oriented, high-impact accomplishment."""
    ai = get_ai_provider()
    return ai.improve_bullet(bullet=data.bullet, target_role=data.target_role)
