import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AlertSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(str, enum.Enum):
    ACTIVE = "active"
    WATCHING = "watching"
    CONFIRMED = "confirmed"
    DISMISSED = "dismissed"
    RESOLVED = "resolved"


class Alert(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "alerts"

    __table_args__ = (
        Index(
            "ix_alerts_patient_status_created_at",
            "patient_id",
            "status",
            "created_at",
        ),
        Index("ix_alerts_created_at", "created_at"),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    prediction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("predictions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    severity: Mapped[AlertSeverity] = mapped_column(
        Enum(AlertSeverity, name="alert_severity"),
        index=True,
        nullable=False,
    )

    status: Mapped[AlertStatus] = mapped_column(
        Enum(
            AlertStatus,
            name="alert_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        index=True,
        nullable=False,
    )

    # Backward-compatible alias.
    # Existing tests and analytics code use Alert._status.
    _status = synonym("status")

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # Acknowledgement (acknowledge -> active -> watching)
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    # Confirmation
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    # Dismissal
    dismissed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    dismissed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    dismissed_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Resolution
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    resolved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    patient: Mapped["Patient"] = relationship(
        back_populates="alerts",
    )

    prediction: Mapped["Prediction"] = relationship(
        back_populates="alerts",
    )

    acknowledged_by_user: Mapped["User | None"] = relationship(
        back_populates="acknowledged_alerts",
        foreign_keys=[acknowledged_by],
    )

    confirmed_by_user: Mapped["User | None"] = relationship(
        back_populates="confirmed_alerts",
        foreign_keys=[confirmed_by],
    )

    dismissed_by_user: Mapped["User | None"] = relationship(
        back_populates="dismissed_alerts",
        foreign_keys=[dismissed_by],
    )

    resolved_by_user: Mapped["User | None"] = relationship(
        back_populates="resolved_alerts",
        foreign_keys=[resolved_by],
    )

    feedback: Mapped[list["Feedback"]] = relationship(
        back_populates="alert",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
