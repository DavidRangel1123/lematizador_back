from fastapi import APIRouter
from app.api.v1.routes import data

api_router = APIRouter()

api_router.include_router(data.router)
