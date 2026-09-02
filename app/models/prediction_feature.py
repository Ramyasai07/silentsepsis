import uuid

from sqlalchemy import Float, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PredictionFeature(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "prediction_features"
    __table_args__ = (
        Index(
            "ix_prediction_features_prediction_feature", "prediction_id", "feature_name"
        ),
    )

    prediction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("predictions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    feature_name: Mapped[str] = mapped_column(String(120), nullable=False)
    feature_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    contribution: Mapped[float] = mapped_column(Float, nullable=False)

    prediction: Mapped["Prediction"] = relationship(back_populates="features")
