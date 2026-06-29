"""Add workers.show_all_vacancies (default true)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008_worker_show_all_vacancies"
down_revision: Union[str, None] = "007_dev2_phase10_sync"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_columns(table: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(table)}


def upgrade() -> None:
    if "show_all_vacancies" not in _table_columns("workers"):
        op.add_column(
            "workers",
            sa.Column("show_all_vacancies", sa.Boolean(), nullable=False, server_default=sa.true()),
        )


def downgrade() -> None:
    if "show_all_vacancies" in _table_columns("workers"):
        op.drop_column("workers", "show_all_vacancies")
