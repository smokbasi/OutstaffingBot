"""Sync employers.verified for legacy staging DBs (verification_status enum)."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_employers_verified_column"
down_revision: Union[str, None] = "005_application_complaints"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _employers_columns() -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns("employers")}


def upgrade() -> None:
    columns = _employers_columns()

    if "verified" not in columns:
        op.add_column(
            "employers",
            sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )
        columns = _employers_columns()

    if "verification_status" in columns:
        op.execute(
            sa.text(
                "UPDATE employers SET verified = (verification_status::text = 'verified')"
            )
        )
        op.drop_column("employers", "verification_status")

    if "is_banned" in columns:
        op.drop_column("employers", "is_banned")


def downgrade() -> None:
    columns = _employers_columns()

    if "verification_status" not in columns:
        verification_status = sa.Enum(
            "pending",
            "verified",
            "rejected",
            name="verification_status",
        )
        verification_status.create(op.get_bind(), checkfirst=True)
        op.add_column(
            "employers",
            sa.Column(
                "verification_status",
                verification_status,
                nullable=False,
                server_default=sa.text("'pending'::verification_status"),
            ),
        )
        if "verified" in columns:
            op.execute(
                sa.text(
                    "UPDATE employers SET verification_status = CASE "
                    "WHEN verified THEN 'verified'::verification_status "
                    "ELSE 'pending'::verification_status END"
                )
            )

    if "is_banned" not in columns:
        op.add_column(
            "employers",
            sa.Column("is_banned", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )

    if "verified" in columns:
        op.drop_column("employers", "verified")
