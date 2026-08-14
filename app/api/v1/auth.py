from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import AdminCreateUser, Token, UserOut
from app.services.audit_service import safe_record_audit_event
from app.services import auth_service
from app.services.auth_service import (
    BootstrapCompletedError,
    DuplicateEmailError,
    DuplicateStaffIdError,
    InvalidCredentialsError,
    InvalidRoleError,
)


router = APIRouter(prefix="/auth", tags=["auth"])


def _map_create_error(error: Exception) -> HTTPException:
    if isinstance(error, DuplicateEmailError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error.message)
    if isinstance(error, DuplicateStaffIdError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error.message)
    if isinstance(error, InvalidRoleError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error.message)
    if isinstance(error, BootstrapCompletedError):
        return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=error.message)
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unexpected authentication error",
    )


@router.post(
    "/bootstrap",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    openapi_extra={
        "parameters": [
            {
                "name": "X-Bootstrap-Secret",
                "in": "header",
                "required": True,
                "schema": {"type": "string"},
            }
        ]
    },
)
def bootstrap_admin(
    payload: AdminCreateUser,
    x_bootstrap_secret: str | None = Header(default=None, include_in_schema=False),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    if x_bootstrap_secret != settings.bootstrap_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid bootstrap secret",
        )

    try:
        user = auth_service.bootstrap_admin(db, payload)
    except (
        BootstrapCompletedError,
        DuplicateEmailError,
        DuplicateStaffIdError,
        InvalidRoleError,
    ) as exc:
        raise _map_create_error(exc) from exc
    return auth_service.to_user_out(user)


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    try:
        user = auth_service.authenticate_user(
            db,
            email=form_data.username,
            password=form_data.password,
        )
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.message,
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    safe_record_audit_event(db, user, action="login", entity="user", entity_id=user.id)
    return Token(access_token=auth_service.create_access_token_for_user(user))


@router.post(
    "/users",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    payload: AdminCreateUser,
    current_user: User = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        user = auth_service.create_user(db, payload)
    except (DuplicateEmailError, DuplicateStaffIdError, InvalidRoleError) as exc:
        raise _map_create_error(exc) from exc
    safe_record_audit_event(
        db,
        current_user,
        action="user_created",
        entity="user",
        entity_id=user.id,
    )
    return auth_service.to_user_out(user)


@router.get("/me", response_model=UserOut)
def read_me(current_user: User = Depends(get_current_user)) -> dict[str, object]:
    return auth_service.to_user_out(current_user)
