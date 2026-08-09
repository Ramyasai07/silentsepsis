import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    staff_id: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        server_default="true",
        nullable=False,
    )
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    role: Mapped["Role"] = relationship(back_populates="users")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")
    feedback: Mapped[list["Feedback"]] = relationship(back_populates="clinician")
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    acknowledged_alerts: Mapped[list["Alert"]] = relationship(
        back_populates="acknowledged_by_user",
        foreign_keys="Alert.acknowledged_by",
    )
    confirmed_alerts: Mapped[list["Alert"]] = relationship(
        back_populates="confirmed_by_user",
        foreign_keys="Alert.confirmed_by",
    )
    dismissed_alerts: Mapped[list["Alert"]] = relationship(
        back_populates="dismissed_by_user",
        foreign_keys="Alert.dismissed_by",
    )
    resolved_alerts: Mapped[list["Alert"]] = relationship(
        back_populates="resolved_by_user",
        foreign_keys="Alert.resolved_by",
    )
