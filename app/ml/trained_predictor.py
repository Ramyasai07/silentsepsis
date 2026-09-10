from app.ml.online_logistic_predictor import OnlineLogisticPredictor


class TrainedRiskPredictor(OnlineLogisticPredictor):
    """Production predictor backed by the committed calibrated model artifacts.

    The artifacts are the small joblib files under
    ``ai/artifacts/online-logistic-v1-calibrated``. The inherited implementation
    preserves the existing RiskPredictor and PredictionResult contracts.
    """

    pass
