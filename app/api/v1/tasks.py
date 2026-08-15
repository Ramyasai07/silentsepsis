from fastapi import APIRouter, Depends, status
from app.api.deps import require_role
from app.db.session import get_db
from app.models.user import User
from app.services.audit_service import safe_record_audit_event
from app.tasks.risk_evaluation import evaluate_all_active_patients
from sqlalchemy.orm import Session

router = APIRouter(prefix="/admin/tasks", tags=["tasks/admin"])


@router.post("/evaluate-risk", status_code=status.HTTP_202_ACCEPTED)
def trigger_risk_evaluation(
    current_user: User = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    """Manually trigger the sepsis risk evaluation background task."""
    task = evaluate_all_active_patients.delay()
    safe_record_audit_event(
        db,
        current_user,
        action="risk_evaluation_triggered",
        entity="task",
        entity_id=None,
    )
    return {"task_id": str(task.id)}
