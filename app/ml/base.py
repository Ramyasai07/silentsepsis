from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

RISK_SCORE_LOW_MAX = 0.3
RISK_SCORE_MODERATE_MAX = 0.5
RISK_SCORE_HIGH_MAX = 0.7

RISK_TIER_LOW = "LOW"
RISK_TIER_MODERATE = "MODERATE"
RISK_TIER_HIGH = "HIGH"
RISK_TIER_CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class FeatureContribution:
    feature_name: str
    contribution: float
    feature_value: float | None = None


@dataclass(frozen=True)
class PredictionResult:
    risk_score: float
    risk_tier: str
    feature_contributions: list[FeatureContribution]


class RiskPredictor(ABC):
    @abstractmethod
    def predict(self, vitals, baseline) -> PredictionResult:
        """Return a deterministic risk prediction for the provided vitals
        and optional baseline."""
        raise NotImplementedError
