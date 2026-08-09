from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.patients import router as patients_router
from app.api.v1.predictions import router as predictions_router
from app.api.v1.vitals import router as vitals_router
from app.api.v1.wards import router as wards_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(wards_router)
api_router.include_router(patients_router)
api_router.include_router(vitals_router)
api_router.include_router(predictions_router)
