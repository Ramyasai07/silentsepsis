"""initial database architecture

Revision ID: 20260805_0001
Revises:
Create Date: 2026-08-05 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260805_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    alert_severity = postgresql.ENUM(
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
        name="alert_severity",
        create_type=False,
    )
    alert_status = postgresql.ENUM(
        "NEW",
        "ACKNOWLEDGED",
        "RESOLVED",
        "DISMISSED",
        name="alert_status",
        create_type=False,
    )
    feedback_type = postgresql.ENUM(
        "CONFIRMED",
        "FALSE_POSITIVE",
        "MISSED_CASE",
        "OTHER",
        name="feedback_type",
        create_type=False,
    )
    patient_gender = postgresql.ENUM(
        "MALE",
        "FEMALE",
        "OTHER",
        "UNKNOWN",
        name="patient_gender",
        create_type=False,
    )
    patient_status = postgresql.ENUM(
        "ADMITTED",
        "TRANSFERRED",
        "DISCHARGED",
        "DECEASED",
        name="patient_status",
        create_type=False,
    )
    risk_level = postgresql.ENUM(
        "LOW",
        "MODERATE",
        "HIGH",
        "CRITICAL",
        name="risk_level",
        create_type=False,
    )

    bind = op.get_bind()
    alert_severity.create(bind, checkfirst=True)
    alert_status.create(bind, checkfirst=True)
    feedback_type.create(bind, checkfirst=True)
    patient_gender.create(bind, checkfirst=True)
    patient_status.create(bind, checkfirst=True)
    risk_level.create(bind, checkfirst=True)

    op.create_table(
        "roles",
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_roles")),
    )
    op.create_index(op.f("ix_roles_name"), "roles", ["name"], unique=True)

    op.create_table(
        "wards",
        sa.Column("ward_name", sa.String(length=120), nullable=False),
        sa.Column("department", sa.String(length=120), nullable=False),
        sa.Column("floor", sa.Integer(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_wards")),
    )
    op.create_index(op.f("ix_wards_department"), "wards", ["department"], unique=False)
    op.create_index(op.f("ix_wards_ward_name"), "wards", ["ward_name"], unique=True)

    op.create_table(
        "users",
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            ["roles.id"],
            name=op.f("fk_users_role_id_roles"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_role_id"), "users", ["role_id"], unique=False)

    op.create_table(
        "patients",
        sa.Column("hospital_patient_id", sa.String(length=80), nullable=False),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("gender", patient_gender, nullable=False),
        sa.Column("admission_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("discharge_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("diagnosis", sa.Text(), nullable=True),
        sa.Column("ward_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_status", patient_status, nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["ward_id"],
            ["wards.id"],
            name=op.f("fk_patients_ward_id_wards"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_patients")),
    )
    op.create_index(
        op.f("ix_patients_admission_date"),
        "patients",
        ["admission_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_patients_current_status"),
        "patients",
        ["current_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_patients_full_name"), "patients", ["full_name"], unique=False
    )
    op.create_index(
        op.f("ix_patients_hospital_patient_id"),
        "patients",
        ["hospital_patient_id"],
        unique=True,
    )
    op.create_index(op.f("ix_patients_ward_id"), "patients", ["ward_id"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("entity", sa.String(length=120), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ip_address", postgresql.INET(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_audit_logs_user_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_logs")),
    )
    op.create_index(
        op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False
    )
    op.create_index(
        op.f("ix_audit_logs_entity"), "audit_logs", ["entity"], unique=False
    )
    op.create_index(
        op.f("ix_audit_logs_entity_id"),
        "audit_logs",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_audit_logs_user_id"), "audit_logs", ["user_id"], unique=False
    )

    op.create_table(
        "notifications",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "is_read", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_notifications_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notifications")),
    )
    op.create_index(
        op.f("ix_notifications_is_read"),
        "notifications",
        ["is_read"],
        unique=False,
    )
    op.create_index(
        op.f("ix_notifications_user_id"),
        "notifications",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "patient_baselines",
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("baseline_hr", sa.Float(), nullable=True),
        sa.Column("baseline_spo2", sa.Float(), nullable=True),
        sa.Column("baseline_temperature", sa.Float(), nullable=True),
        sa.Column("baseline_rr", sa.Float(), nullable=True),
        sa.Column("baseline_systolic_bp", sa.Float(), nullable=True),
        sa.Column("baseline_diastolic_bp", sa.Float(), nullable=True),
        sa.Column("calculated_from_hours", sa.Integer(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name=op.f("fk_patient_baselines_patient_id_patients"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_patient_baselines")),
    )
    op.create_index(
        op.f("ix_patient_baselines_patient_id"),
        "patient_baselines",
        ["patient_id"],
        unique=True,
    )

    op.create_table(
        "predictions",
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_version", sa.String(length=80), nullable=False),
        sa.Column("risk_probability", sa.Float(), nullable=False),
        sa.Column("risk_level", risk_level, nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name=op.f("fk_predictions_patient_id_patients"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_predictions")),
    )
    op.create_index(
        op.f("ix_predictions_generated_at"),
        "predictions",
        ["generated_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_predictions_model_version"),
        "predictions",
        ["model_version"],
        unique=False,
    )
    op.create_index(
        op.f("ix_predictions_patient_generated_at"),
        "predictions",
        ["patient_id", "generated_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_predictions_patient_id"),
        "predictions",
        ["patient_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_predictions_risk_level"),
        "predictions",
        ["risk_level"],
        unique=False,
    )

    op.create_table(
        "vital_readings",
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("heart_rate", sa.Float(), nullable=True),
        sa.Column("systolic_bp", sa.Float(), nullable=True),
        sa.Column("diastolic_bp", sa.Float(), nullable=True),
        sa.Column("respiratory_rate", sa.Float(), nullable=True),
        sa.Column("spo2", sa.Float(), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name=op.f("fk_vital_readings_patient_id_patients"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vital_readings")),
    )
    op.create_index(
        op.f("ix_vital_readings_patient_id"),
        "vital_readings",
        ["patient_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_vital_readings_patient_recorded_at"),
        "vital_readings",
        ["patient_id", "recorded_at"],
        unique=False,
    )

    op.create_table(
        "alerts",
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prediction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("severity", alert_severity, nullable=False),
        sa.Column("status", alert_status, nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["acknowledged_by"],
            ["users.id"],
            name=op.f("fk_alerts_acknowledged_by_users"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patients.id"],
            name=op.f("fk_alerts_patient_id_patients"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["prediction_id"],
            ["predictions.id"],
            name=op.f("fk_alerts_prediction_id_predictions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alerts")),
    )
    op.create_index(
        op.f("ix_alerts_acknowledged_by"),
        "alerts",
        ["acknowledged_by"],
        unique=False,
    )
    op.create_index(
        op.f("ix_alerts_patient_id"), "alerts", ["patient_id"], unique=False
    )
    op.create_index(
        op.f("ix_alerts_patient_status_created_at"),
        "alerts",
        ["patient_id", "status", "created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_alerts_prediction_id"),
        "alerts",
        ["prediction_id"],
        unique=False,
    )
    op.create_index(op.f("ix_alerts_severity"), "alerts", ["severity"], unique=False)
    op.create_index(op.f("ix_alerts_status"), "alerts", ["status"], unique=False)

    op.create_table(
        "prediction_features",
        sa.Column("prediction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("feature_name", sa.String(length=120), nullable=False),
        sa.Column("feature_value", sa.Float(), nullable=True),
        sa.Column("contribution", sa.Float(), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["prediction_id"],
            ["predictions.id"],
            name=op.f("fk_prediction_features_prediction_id_predictions"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prediction_features")),
    )
    op.create_index(
        op.f("ix_prediction_features_prediction_feature"),
        "prediction_features",
        ["prediction_id", "feature_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_prediction_features_prediction_id"),
        "prediction_features",
        ["prediction_id"],
        unique=False,
    )

    op.create_table(
        "feedback",
        sa.Column("alert_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinician_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("feedback_type", feedback_type, nullable=False),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["alert_id"],
            ["alerts.id"],
            name=op.f("fk_feedback_alert_id_alerts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["clinician_id"],
            ["users.id"],
            name=op.f("fk_feedback_clinician_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_feedback")),
    )
    op.create_index(
        op.f("ix_feedback_alert_id"), "feedback", ["alert_id"], unique=False
    )
    op.create_index(
        op.f("ix_feedback_clinician_id"),
        "feedback",
        ["clinician_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_feedback_feedback_type"),
        "feedback",
        ["feedback_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_feedback_feedback_type"), table_name="feedback")
    op.drop_index(op.f("ix_feedback_clinician_id"), table_name="feedback")
    op.drop_index(op.f("ix_feedback_alert_id"), table_name="feedback")
    op.drop_table("feedback")
    op.drop_index(
        op.f("ix_prediction_features_prediction_id"),
        table_name="prediction_features",
    )
    op.drop_index(
        op.f("ix_prediction_features_prediction_feature"),
        table_name="prediction_features",
    )
    op.drop_table("prediction_features")
    op.drop_index(op.f("ix_alerts_status"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_severity"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_prediction_id"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_patient_status_created_at"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_patient_id"), table_name="alerts")
    op.drop_index(op.f("ix_alerts_acknowledged_by"), table_name="alerts")
    op.drop_table("alerts")
    op.drop_index(
        op.f("ix_vital_readings_patient_recorded_at"),
        table_name="vital_readings",
    )
    op.drop_index(op.f("ix_vital_readings_patient_id"), table_name="vital_readings")
    op.drop_table("vital_readings")
    op.drop_index(op.f("ix_predictions_risk_level"), table_name="predictions")
    op.drop_index(op.f("ix_predictions_patient_id"), table_name="predictions")
    op.drop_index(
        op.f("ix_predictions_patient_generated_at"),
        table_name="predictions",
    )
    op.drop_index(op.f("ix_predictions_model_version"), table_name="predictions")
    op.drop_index(op.f("ix_predictions_generated_at"), table_name="predictions")
    op.drop_table("predictions")
    op.drop_index(
        op.f("ix_patient_baselines_patient_id"),
        table_name="patient_baselines",
    )
    op.drop_table("patient_baselines")
    op.drop_index(op.f("ix_notifications_user_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_is_read"), table_name="notifications")
    op.drop_table("notifications")
    op.drop_index(op.f("ix_audit_logs_user_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_entity_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_entity"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_action"), table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index(op.f("ix_patients_ward_id"), table_name="patients")
    op.drop_index(op.f("ix_patients_hospital_patient_id"), table_name="patients")
    op.drop_index(op.f("ix_patients_full_name"), table_name="patients")
    op.drop_index(op.f("ix_patients_current_status"), table_name="patients")
    op.drop_index(op.f("ix_patients_admission_date"), table_name="patients")
    op.drop_table("patients")
    op.drop_index(op.f("ix_users_role_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_wards_ward_name"), table_name="wards")
    op.drop_index(op.f("ix_wards_department"), table_name="wards")
    op.drop_table("wards")
    op.drop_index(op.f("ix_roles_name"), table_name="roles")
    op.drop_table("roles")

    bind = op.get_bind()
    postgresql.ENUM(name="risk_level").drop(bind, checkfirst=True)
    postgresql.ENUM(name="patient_status").drop(bind, checkfirst=True)
    postgresql.ENUM(name="patient_gender").drop(bind, checkfirst=True)
    postgresql.ENUM(name="feedback_type").drop(bind, checkfirst=True)
    postgresql.ENUM(name="alert_status").drop(bind, checkfirst=True)
    postgresql.ENUM(name="alert_severity").drop(bind, checkfirst=True)
