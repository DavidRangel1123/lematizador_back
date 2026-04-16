from fastapi import APIRouter
from app.api.v1.router import api_router as v1_router

router = APIRouter()

# Router general de la api
router.include_router(v1_router, prefix="/api/v1")
