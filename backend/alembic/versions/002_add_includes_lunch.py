"""Add includes_lunch to job_requests."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_add_includes_lunch"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "job_requests",
        sa.Column("includes_lunch", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("job_requests", "includes_lunch")
