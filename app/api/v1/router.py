from fastapi import APIRouter

from app.api.v1.alerts import router as alerts_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.audit_logs import router as audit_logs_router
from app.api.v1.auth import router as auth_router
from app.api.v1.patients import router as patients_router
from app.api.v1.predictions import router as predictions_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.vitals import router as vitals_router
from app.api.v1.wards import router as wards_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(wards_router)
api_router.include_router(patients_router)
api_router.include_router(vitals_router)
api_router.include_router(predictions_router)
api_router.include_router(alerts_router)
api_router.include_router(audit_logs_router)
api_router.include_router(tasks_router)
api_router.include_router(analytics_router)
