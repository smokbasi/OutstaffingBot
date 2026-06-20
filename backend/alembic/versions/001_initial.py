"""Initial schema — all core tables."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

user_role = postgresql.ENUM("worker", "employer", "both", "admin", name="user_role", create_type=False)
gender = postgresql.ENUM("male", "female", "other", "prefer_not_say", name="gender", create_type=False)
required_gender = postgresql.ENUM("any", "male", "female", name="required_gender", create_type=False)
job_request_status = postgresql.ENUM(
    "draft", "active", "filled", "cancelled", "expired", name="job_request_status", create_type=False
)
application_status = postgresql.ENUM(
    "pending",
    "accepted",
    "rejected",
    "cancelled_by_worker",
    "cancelled_by_employer",
    name="application_status",
    create_type=False,
)
notification_type = postgresql.ENUM(
    "new_vacancy", "application_status", "shift_reminder", name="notification_type", create_type=False
)


def upgrade() -> None:
    user_role.create(op.get_bind(), checkfirst=True)
    gender.create(op.get_bind(), checkfirst=True)
    required_gender.create(op.get_bind(), checkfirst=True)
    job_request_status.create(op.get_bind(), checkfirst=True)
    application_status.create(op.get_bind(), checkfirst=True)
    notification_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "job_categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("name_ru", sa.String(length=100), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["parent_id"], ["job_categories.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "metro_stations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("line_name", sa.String(length=100), nullable=False),
        sa.Column("lat", sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column("lon", sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "telegram_groups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("chat_id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("category_ids", postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chat_id"),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=255), nullable=True),
        sa.Column("role", user_role, nullable=False, server_default="worker"),
        sa.Column("language_code", sa.String(length=5), nullable=True),
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_id"),
    )

    op.create_table(
        "employers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_name", sa.String(length=200), nullable=False),
        sa.Column("contact_phone", sa.String(length=20), nullable=True),
        sa.Column("contact_person", sa.String(length=200), nullable=True),
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "workers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("age", sa.SmallInteger(), nullable=False),
        sa.Column("gender", gender, nullable=True),
        sa.Column("metro_station_id", sa.Integer(), nullable=True),
        sa.Column("metro_radius_km", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("min_hourly_rate", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("resume_completed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["metro_station_id"], ["metro_stations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "worker_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_ids", postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column("metro_station_ids", postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column("min_hourly_rate", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("max_distance_km", sa.SmallInteger(), nullable=True),
        sa.Column("push_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("quiet_hours_start", sa.Time(), nullable=True),
        sa.Column("quiet_hours_end", sa.Time(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", notification_type, nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "job_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("metro_station_id", sa.Integer(), nullable=False),
        sa.Column("address", sa.String(length=300), nullable=True),
        sa.Column("hourly_rate", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("workers_needed", sa.SmallInteger(), nullable=False),
        sa.Column("min_experience_months", sa.SmallInteger(), nullable=True),
        sa.Column("required_gender", required_gender, nullable=True),
        sa.Column("min_age", sa.SmallInteger(), nullable=True),
        sa.Column("max_age", sa.SmallInteger(), nullable=True),
        sa.Column("dress_code", sa.String(length=200), nullable=True),
        sa.Column("contact_info", sa.Text(), nullable=True),
        sa.Column("status", job_request_status, nullable=False, server_default="draft"),
        sa.Column("post_to_groups", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("notify_matching_workers", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["category_id"], ["job_categories.id"]),
        sa.ForeignKeyConstraint(["employer_id"], ["employers.id"]),
        sa.ForeignKeyConstraint(["metro_station_id"], ["metro_stations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_job_requests_matching",
        "job_requests",
        ["status", "category_id", "metro_station_id", "hourly_rate"],
    )

    op.create_table(
        "worker_experiences",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("worker_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("role_title", sa.String(length=200), nullable=False),
        sa.Column("duration_months", sa.SmallInteger(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["job_categories.id"]),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "shift_slots",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shift_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("slots_total", sa.SmallInteger(), nullable=False),
        sa.Column("slots_filled", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["job_request_id"], ["job_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_shift_slots_schedule", "shift_slots", ["shift_date", "start_time", "end_time"])

    op.create_table(
        "group_posts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["group_id"], ["telegram_groups.id"]),
        sa.ForeignKeyConstraint(["job_request_id"], ["job_requests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("worker_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shift_slot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", application_status, nullable=False, server_default="pending"),
        sa.Column("applied_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["job_request_id"], ["job_requests.id"]),
        sa.ForeignKeyConstraint(["shift_slot_id"], ["shift_slots.id"]),
        sa.ForeignKeyConstraint(["worker_id"], ["workers.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("worker_id", "shift_slot_id", name="uq_worker_shift_slot"),
    )
    op.create_index("ix_applications_worker_status", "applications", ["worker_id", "status"])
    op.create_index(
        "ix_applications_accepted",
        "applications",
        ["worker_id"],
        unique=False,
        postgresql_where=sa.text("status = 'accepted'"),
    )


def downgrade() -> None:
    op.drop_index("ix_applications_accepted", table_name="applications")
    op.drop_index("ix_applications_worker_status", table_name="applications")
    op.drop_table("applications")
    op.drop_table("group_posts")
    op.drop_index("ix_shift_slots_schedule", table_name="shift_slots")
    op.drop_table("shift_slots")
    op.drop_table("worker_experiences")
    op.drop_index("ix_job_requests_matching", table_name="job_requests")
    op.drop_table("job_requests")
    op.drop_table("notifications")
    op.drop_table("worker_preferences")
    op.drop_table("workers")
    op.drop_table("employers")
    op.drop_table("users")
    op.drop_table("telegram_groups")
    op.drop_table("metro_stations")
    op.drop_table("job_categories")

    notification_type.drop(op.get_bind(), checkfirst=True)
    application_status.drop(op.get_bind(), checkfirst=True)
    job_request_status.drop(op.get_bind(), checkfirst=True)
    required_gender.drop(op.get_bind(), checkfirst=True)
    gender.drop(op.get_bind(), checkfirst=True)
    user_role.drop(op.get_bind(), checkfirst=True)
