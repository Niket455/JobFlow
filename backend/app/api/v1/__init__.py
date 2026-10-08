from fastapi import APIRouter

from app.api.v1 import auth, career_goals, deal_breakers, profile

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(career_goals.router)
api_router.include_router(deal_breakers.router)
