"""Add phone to workers."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_worker_phone"
down_revision: Union[str, None] = "004_worker_verification"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("workers", sa.Column("phone", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("workers", "phone")
