import datetime
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import settings
from app.core.limiter import limiter
from app.db.session import SessionLocal
from app.main import app
from app.models.alert import Alert
from app.models.patient import Patient
from app.models.prediction import Prediction
from app.models.role import Role
from app.models.user import User
from app.models.vital_reading import VitalReading
from app.models.ward import Ward
from app.services.alert_service import get_alerts

client = TestClient(app)


def test_health_check_liveness_only() -> None:
    """
    GET /health returns 200 status 'ok' even if the database is down.
    This validates true liveness-only behavior.
    """
    # Mock database engine connect to fail completely
    with patch("app.db.session.engine.connect") as mock_connect:
        mock_connect.side_effect = Exception("Database is down")

        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_readiness_check_success() -> None:
    """
    GET /ready returns 200 status 'ready' when both database and Redis
    are reachable.
    """
    with (
        patch("sqlalchemy.engine.base.Engine.connect") as mock_db_connect,
        patch("redis.from_url") as mock_redis_from_url,
    ):
        # Setup mocks to succeed
        mock_db_conn = MagicMock()
        mock_db_connect.return_value.__enter__.return_value = mock_db_conn

        mock_redis = MagicMock()
        mock_redis_from_url.return_value = mock_redis
        mock_redis.ping.return_value = True

        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ready"}


def test_readiness_check_db_failure() -> None:
    """
    GET /ready returns 503 containing 'database' in failed
    dependencies when DB is unreachable.
    """
    with (
        patch("sqlalchemy.engine.base.Engine.connect") as mock_db_connect,
        patch("redis.from_url") as mock_redis_from_url,
    ):
        # DB connection fails
        mock_db_connect.side_effect = Exception("DB Connection Failed")

        mock_redis = MagicMock()
        mock_redis_from_url.return_value = mock_redis
        mock_redis.ping.return_value = True

        response = client.get("/ready")
        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "unavailable"
        assert "database" in body["failed"]
        assert "redis" not in body["failed"]


def test_readiness_check_redis_failure() -> None:
    """
    GET /ready returns 503 containing 'redis' in failed
    dependencies when Redis is unreachable.
    """
    with (
        patch("sqlalchemy.engine.base.Engine.connect") as mock_db_connect,
        patch("redis.from_url") as mock_redis_from_url,
    ):
        # DB succeeds
        mock_db_conn = MagicMock()
        mock_db_connect.return_value.__enter__.return_value = mock_db_conn

        # Redis ping fails
        mock_redis = MagicMock()
        mock_redis_from_url.return_value = mock_redis
        mock_redis.ping.side_effect = Exception("Redis Connection Failed")

        response = client.get("/ready")
        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "unavailable"
        assert "redis" in body["failed"]
        assert "database" not in body["failed"]


def test_metrics_endpoint_success() -> None:
    """
    GET /metrics returns 200 and contains typical Prometheus metrics
    output.
    """
    original_metrics_enabled = settings.enable_metrics
    settings.enable_metrics = True

    try:
        response = client.get("/metrics")
        assert response.status_code == 200
        text_content = response.text
        assert "http_requests_total" in text_content
        assert "http_request_duration_seconds" in text_content
        assert "celery_task_success_total" in text_content
    finally:
        settings.enable_metrics = original_metrics_enabled


def test_metrics_endpoint_disabled() -> None:
    """
    GET /metrics returns 404 when settings.enable_metrics is False.
    """
    original_metrics_enabled = settings.enable_metrics
    settings.enable_metrics = False

    try:
        response = client.get("/metrics")
        assert response.status_code == 404
        assert response.json() == {"detail": "Metrics disabled"}
    finally:
        settings.enable_metrics = original_metrics_enabled


def test_health_ready_rate_limit_exemption() -> None:
    """
    Liveness and readiness endpoints must be exempted from default rate
    limits. Even past the default limit, they should return 200.
    """
    # Enable rate limiter
    limiter.enabled = True
    original_default_limit = settings.default_rate_limit

    # Configure a tiny default rate limit of 2/minute
    settings.default_rate_limit = "2/minute"

    try:
        # Hit /health 10 times — it should remain 200
        for _ in range(10):
            response = client.get("/health")
            assert response.status_code == 200

        # Hit /ready 10 times — it should remain 200/503 (not 429)
        with (
            patch("sqlalchemy.engine.base.Engine.connect") as mock_db_connect,
            patch("redis.from_url") as mock_redis_from_url,
        ):
            mock_db_conn = MagicMock()
            mock_db_connect.return_value.__enter__.return_value = mock_db_conn
            mock_redis = MagicMock()
            mock_redis_from_url.return_value = mock_redis
            mock_redis.ping.return_value = True

            for _ in range(10):
                response = client.get("/ready")
                assert response.status_code == 200

    finally:
        settings.default_rate_limit = original_default_limit
        limiter.enabled = False


def test_sql_optimization_index_correctness() -> None:
    """
    Functional test to confirm get_alerts returns identical results
    (order and identity) with the index applied as it would with an
    in-memory python sort. Only performance should change, not
    correctness.
    """
    with SessionLocal() as db:
        # Create test records
        ward = Ward(ward_name="Test Ward Health", department="ICU", capacity=10)
        db.add(ward)
        db.flush()

        patient = Patient(
            hospital_patient_id="PT-HEALTH-TEST",
            full_name="Health Patient",
            age=45,
            gender="MALE",
            admission_date=datetime.datetime.now(datetime.timezone.utc),
            current_status="ADMITTED",
            ward_id=ward.id,
            diagnosis="Sepsis Risk Test",
            bed_number="B101",
        )
        db.add(patient)
        db.flush()

        role = db.scalar(text("SELECT id FROM roles WHERE name = 'Admin'"))
        if not role:
            role = Role(name="Admin", description="Admin role")
            db.add(role)
            db.flush()
            role_id = role.id
        else:
            role_id = role

        user = User(
            full_name="Admin User Health",
            email="admin-health@silentsepsis.test",
            hashed_password="x",
            role_id=role_id,
            staff_id="STF-HEALTH",
            is_active=True,
        )
        db.add(user)
        db.flush()

        # Create multiple alerts with varying timestamps to test sorting
        # order
        alerts = []
        base_time = datetime.datetime.now(datetime.timezone.utc)
        for i in range(5):
            # Create vital reading
            vr = VitalReading(
                patient_id=patient.id,
                heart_rate=72.0,
                recorded_at=base_time - datetime.timedelta(minutes=i * 10),
            )
            db.add(vr)
            db.flush()

            # Create prediction
            pred = Prediction(
                patient_id=patient.id,
                vital_reading_id=vr.id,
                model_version="rule-based-v1",
                risk_probability=0.85,
                risk_level="HIGH",
                generated_at=base_time - datetime.timedelta(minutes=i * 10),
            )
            db.add(pred)
            db.flush()

            # Create alert
            alert = Alert(
                patient_id=patient.id,
                prediction_id=pred.id,
                severity="HIGH",
                status="active",
                message=f"Test alert message {i}",
                created_at=base_time - datetime.timedelta(minutes=i * 10),
                updated_at=base_time - datetime.timedelta(minutes=i * 10),
            )
            db.add(alert)
            alerts.append(alert)
        db.commit()

        try:
            # Query get_alerts which sorts by created_at.desc() in DB
            db_alerts = get_alerts(db, limit=50)

            # Filter db_alerts to only those belonging to our test patient
            db_alerts_filtered = [a for a in db_alerts if a.patient_id == patient.id]

            # Assert count is correct
            assert len(db_alerts_filtered) == 5

            # Verify they are ordered DESC by created_at
            for idx in range(len(db_alerts_filtered) - 1):
                assert (
                    db_alerts_filtered[idx].created_at
                    >= db_alerts_filtered[idx + 1].created_at
                )

            # Verify they match the exact in-memory sorted order
            in_memory_sorted = sorted(alerts, key=lambda x: x.created_at, reverse=True)
            for db_alert, mem_alert in zip(db_alerts_filtered, in_memory_sorted):
                assert db_alert.id == mem_alert.id
                assert db_alert.message == mem_alert.message

        finally:
            # Cleanup test records
            db.execute(
                text(
                    "DELETE FROM feedback WHERE alert_id IN ("
                    "SELECT id FROM alerts WHERE patient_id = :p)"
                ),
                {"p": patient.id},
            )
            db.execute(
                text("DELETE FROM alerts WHERE patient_id = :p"), {"p": patient.id}
            )
            db.execute(
                text("DELETE FROM predictions WHERE patient_id = :p"),
                {"p": patient.id},
            )
            db.execute(
                text("DELETE FROM vital_readings WHERE patient_id = :p"),
                {"p": patient.id},
            )
            db.execute(text("DELETE FROM patients WHERE id = :p"), {"p": patient.id})
            db.execute(text("DELETE FROM users WHERE id = :u"), {"u": user.id})
            db.execute(text("DELETE FROM wards WHERE id = :w"), {"w": ward.id})
            db.commit()
