import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
            "ix_alerts_patient_status_created_at", "patient_id", "status", "created_at"
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
    # Use native_enum=False to ensure SQLAlchemy binds plain strings (enum values)
    # when writing to the DB. The DB still has a PostgreSQL enum type; sending
    # plain text values avoids SQLAlchemy mapping enum members to their names
    # which previously produced 'ACTIVE' instead of the DB label 'active'.
    # Store status as a string column to avoid SQLAlchemy enum binding quirks.
    # The DB still uses the PostgreSQL enum type; passing plain strings works because
    # Postgres will cast string literals to the enum when they match labels.
    from sqlalchemy.ext.hybrid import hybrid_property

    # store actual DB column as a plain string but expose a hybrid property that
    # returns an AlertStatus enum for attribute access while still allowing
    # SQL expressions to target the underlying column.
    _status: Mapped[str] = mapped_column(
        "status", String(32), index=True, nullable=False
    )

    @hybrid_property
    def status(self) -> AlertStatus:
        return AlertStatus(self._status)

    @status.setter
    def status(self, value: str | AlertStatus) -> None:
        # Accept either an enum or raw string
        self._status = value.value if hasattr(value, "value") else value

    @status.expression
    def status(cls):
        return cls._status

    message: Mapped[str] = mapped_column(Text, nullable=False)

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
    dismissed_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

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

    patient: Mapped["Patient"] = relationship(back_populates="alerts")
    prediction: Mapped["Prediction"] = relationship(back_populates="alerts")
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
