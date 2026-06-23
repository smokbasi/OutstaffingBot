"""Add is_banned to workers and employers."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_user_ban"
down_revision: Union[str, None] = "005_worker_phone"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workers",
        sa.Column("is_banned", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "employers",
        sa.Column("is_banned", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("employers", "is_banned")
    op.drop_column("workers", "is_banned")
