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


def _table_columns(table: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table)}


def _table_exists(table: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return table in inspector.get_table_names()


def upgrade() -> None:
    reviewer_role.create(op.get_bind(), checkfirst=True)

    if "city" not in _table_columns("metro_stations"):
        op.add_column(
            "metro_stations",
            sa.Column("city", sa.String(length=50), nullable=False, server_default="spb"),
        )
    if "city" not in _table_columns("workers"):
        op.add_column(
            "workers",
            sa.Column("city", sa.String(length=50), nullable=False, server_default="spb"),
        )
    if "city" not in _table_columns("job_requests"):
        op.add_column(
            "job_requests",
            sa.Column("city", sa.String(length=50), nullable=False, server_default="spb"),
        )
    if "phone" not in _table_columns("workers"):
        op.add_column("workers", sa.Column("phone", sa.String(length=20), nullable=True))
    if "verified" not in _table_columns("workers"):
        op.add_column(
            "workers",
            sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        )

    if not _table_exists("reviews"):
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
    if _table_exists("reviews"):
        op.drop_table("reviews")
    workers_cols = _table_columns("workers")
    if "verified" in workers_cols:
        op.drop_column("workers", "verified")
    if "phone" in workers_cols:
        op.drop_column("workers", "phone")
    if "city" in _table_columns("job_requests"):
        op.drop_column("job_requests", "city")
    if "city" in workers_cols:
        op.drop_column("workers", "city")
    if "city" in _table_columns("metro_stations"):
        op.drop_column("metro_stations", "city")
    reviewer_role.drop(op.get_bind(), checkfirst=True)
