"""Phase 9-10: verification_status, audit_logs, reviews, city, geo-ready columns."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002_phase_9_10"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

verification_status = postgresql.ENUM(
    "pending", "verified", "rejected", name="verification_status", create_type=False
)
reviewer_role = postgresql.ENUM("worker", "employer", name="reviewer_role", create_type=False)


def upgrade() -> None:
    verification_status.create(op.get_bind(), checkfirst=True)
    reviewer_role.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "employers",
        sa.Column(
            "verification_status",
            verification_status,
            nullable=False,
            server_default="pending",
        ),
    )
    op.execute(
        sa.text(
            "UPDATE employers SET verification_status = 'verified' WHERE verified = true"
        )
    )
    op.drop_column("employers", "verified")

    op.add_column(
        "metro_stations",
        sa.Column("city", sa.String(length=50), nullable=False, server_default="spb"),
    )
    op.add_column(
        "workers",
        sa.Column("city", sa.String(length=50), nullable=False, server_default="spb"),
    )
    op.add_column(
        "job_requests",
        sa.Column("city", sa.String(length=50), nullable=False, server_default="spb"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.String(length=100), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    op.create_table(
        "reviews",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("application_id", sa.UUID(), nullable=False),
        sa.Column("reviewer_user_id", sa.UUID(), nullable=False),
        sa.Column("reviewed_user_id", sa.UUID(), nullable=False),
        sa.Column("reviewer_role", reviewer_role, nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"]),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reviewed_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "application_id", "reviewer_user_id", name="uq_review_application_reviewer"
        ),
    )

    op.execute(
        sa.text(
            "ALTER TYPE notification_type ADD VALUE IF NOT EXISTS 'new_matching_worker'"
        )
    )


def downgrade() -> None:
    op.drop_table("reviews")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_column("job_requests", "city")
    op.drop_column("workers", "city")
    op.drop_column("metro_stations", "city")

    op.add_column(
        "employers",
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.execute(
        sa.text(
            "UPDATE employers SET verified = true WHERE verification_status = 'verified'"
        )
    )
    op.drop_column("employers", "verification_status")

    reviewer_role.drop(op.get_bind(), checkfirst=True)
    verification_status.drop(op.get_bind(), checkfirst=True)
