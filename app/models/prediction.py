import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Prediction(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "predictions"
    __table_args__ = (
        Index("ix_predictions_patient_generated_at", "patient_id", "generated_at"),
    )

    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    vital_reading_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vital_readings.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    model_version: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    risk_probability: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(
        Enum(RiskLevel, name="risk_level"),
        index=True,
        nullable=False,
    )

    @property
    def risk_score(self) -> float:
        return self.risk_probability

    @property
    def risk_tier(self) -> str:
        return self.risk_level.value

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        index=True,
        nullable=False,
    )

    patient: Mapped["Patient"] = relationship(back_populates="predictions")
    features: Mapped[list["PredictionFeature"]] = relationship(
        back_populates="prediction",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    alerts: Mapped[list["Alert"]] = relationship(back_populates="prediction")
