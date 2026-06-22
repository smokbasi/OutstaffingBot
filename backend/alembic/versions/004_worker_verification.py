"""Add verification_status to workers."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_worker_verification"
down_revision: Union[str, None] = "003_phase_9_10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

verification_status = postgresql.ENUM(
    "pending", "verified", "rejected", name="verification_status", create_type=False
)


def upgrade() -> None:
    op.add_column(
        "workers",
        sa.Column(
            "verification_status",
            verification_status,
            nullable=False,
            server_default="pending",
        ),
    )
    op.execute(sa.text("UPDATE workers SET verification_status = 'verified'"))


def downgrade() -> None:
    op.drop_column("workers", "verification_status")
