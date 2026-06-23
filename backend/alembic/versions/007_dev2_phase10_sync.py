"""Dev2 sync: reviews, city columns, worker phone/verified, employer push."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007_dev2_phase10_sync"
down_revision: Union[str, None] = "006_employers_verified_column"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

reviewer_role = postgresql.ENUM("worker", "employer", name="reviewer_role", create_type=False)


def upgrade() -> None:
    reviewer_role.create(op.get_bind(), checkfirst=True)

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
    op.add_column("workers", sa.Column("phone", sa.String(length=20), nullable=True))
    op.add_column(
        "workers",
        sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

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
    op.drop_column("workers", "verified")
    op.drop_column("workers", "phone")
    op.drop_column("job_requests", "city")
    op.drop_column("workers", "city")
    op.drop_column("metro_stations", "city")
    reviewer_role.drop(op.get_bind(), checkfirst=True)
