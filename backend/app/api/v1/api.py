from fastapi import APIRouter
from app.api.v1.auth import router as auth_router
from app.api.v1.profile import router as profile_router
from app.api.v1.users import router as users_router
from app.api.v1.resumes import router as resumes_router
from app.api.v1.jobs import router as jobs_router
from app.api.v1.analyses import router as analyses_router
from app.api.v1.ai import router as ai_router
from app.api.v1.job_search import router as job_search_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(profile_router)
api_router.include_router(users_router)
api_router.include_router(resumes_router)
api_router.include_router(jobs_router)
api_router.include_router(analyses_router)
api_router.include_router(ai_router)
api_router.include_router(job_search_router)

