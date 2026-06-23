"""Add application_complaints table for shift/application disputes."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005_application_complaints"
down_revision: Union[str, None] = "004_audit_log"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

complaint_violation_type = postgresql.ENUM(
    "late",
    "no_show",
    "no_payment",
    "no_work",
    name="complaint_violation_type",
    create_type=False,
)
complaint_reporter_role = postgresql.ENUM(
    "worker",
    "employer",
    name="complaint_reporter_role",
    create_type=False,
)
complaint_status = postgresql.ENUM(
    "open",
    "under_review",
    "resolved",
    "dismissed",
    name="complaint_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    complaint_violation_type.create(bind, checkfirst=True)
    complaint_reporter_role.create(bind, checkfirst=True)
    complaint_status.create(bind, checkfirst=True)

    op.create_table(
        "application_complaints",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shift_slot_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reporter_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reporter_role", complaint_reporter_role, nullable=False),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("violation_type", complaint_violation_type, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", complaint_status, nullable=False, server_default="open"),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_telegram_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
        sa.ForeignKeyConstraint(["job_request_id"], ["job_requests.id"]),
        sa.ForeignKeyConstraint(["shift_slot_id"], ["shift_slots.id"]),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_application_complaints_job_request_id",
        "application_complaints",
        ["job_request_id"],
    )
    op.create_index(
        "ix_application_complaints_violation_type_created_at",
        "application_complaints",
        ["violation_type", "created_at"],
    )
    op.create_index(
        "uq_application_complaints_open_dup",
        "application_complaints",
        ["application_id", "reporter_user_id", "violation_type"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_application_complaints_open_dup",
        table_name="application_complaints",
        postgresql_where=sa.text("status = 'open'"),
    )
    op.drop_index(
        "ix_application_complaints_violation_type_created_at",
        table_name="application_complaints",
    )
    op.drop_index(
        "ix_application_complaints_job_request_id",
        table_name="application_complaints",
    )
    op.drop_table("application_complaints")

    bind = op.get_bind()
    complaint_status.drop(bind, checkfirst=True)
    complaint_reporter_role.drop(bind, checkfirst=True)
    complaint_violation_type.drop(bind, checkfirst=True)
