"""Add moderation_violations log and user moderation_flagged_at."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003_moderation_violations"
down_revision: Union[str, None] = "002_add_includes_lunch"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

moderation_violation_source = postgresql.ENUM(
    "bot",
    "mini_app",
    "api",
    name="moderation_violation_source",
    create_type=False,
)


def upgrade() -> None:
    moderation_violation_source.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "users",
        sa.Column("moderation_flagged_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "moderation_violations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("field", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=True),
        sa.Column("matched_term", sa.String(length=200), nullable=False),
        sa.Column("raw_snippet", sa.Text(), nullable=False),
        sa.Column("normalized_snippet", sa.Text(), nullable=False),
        sa.Column("source", moderation_violation_source, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_moderation_violations_user_id", "moderation_violations", ["user_id"])
    op.create_index("ix_moderation_violations_telegram_id", "moderation_violations", ["telegram_id"])


def downgrade() -> None:
    op.drop_index("ix_moderation_violations_telegram_id", table_name="moderation_violations")
    op.drop_index("ix_moderation_violations_user_id", table_name="moderation_violations")
    op.drop_table("moderation_violations")
    op.drop_column("users", "moderation_flagged_at")
    moderation_violation_source.drop(op.get_bind(), checkfirst=True)
