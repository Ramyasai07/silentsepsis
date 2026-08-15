from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.analytics_service import get_precision_recall_history, get_staff_response_by_ward


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/precision-recall-history", response_model=list[dict[str, str | int | None]])
def read_precision_recall_history(
    days: Optional[int] = Query(30, gt=0, description="Number of days of history to retrieve"),
    bucket_size_days: Optional[int] = Query(5, gt=0, description="Size of each time bucket in days"),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> list[dict[str, str | int | None]]:
    try:
        return get_precision_recall_history(db, days=days, bucket_size_days=bucket_size_days)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        ) from e


@router.get("/staff-response-by-ward", response_model=list[dict[str, str | int]])
def read_staff_response_by_ward(
    days: Optional[int] = Query(30, gt=0, description="Number of days of history to retrieve"),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> list[dict[str, str | int]]:
    try:
        return get_staff_response_by_ward(db, days=days)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        ) from e