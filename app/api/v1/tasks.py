from fastapi import APIRouter, Depends, status
from app.api.deps import require_role
from app.tasks.risk_evaluation import evaluate_all_active_patients

router = APIRouter(prefix="/admin/tasks", tags=["tasks"])


@router.post("/evaluate-risk", status_code=status.HTTP_202_ACCEPTED)
def trigger_risk_evaluation(current_user=Depends(require_role("Admin"))):
    task = evaluate_all_active_patients.delay()
    return {"task_id": str(task.id)}
