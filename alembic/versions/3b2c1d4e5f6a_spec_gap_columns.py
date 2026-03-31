"""Add customer.segment and outcome purchase_count_after_event, days_since_last_purchase."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "3b2c1d4e5f6a"
down_revision = "2590870933fe"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column("segment", sa.String(length=32), nullable=False, server_default="casual"),
    )
    op.alter_column("customers", "segment", server_default=None)

    op.add_column(
        "daily_customer_outcomes",
        sa.Column("purchase_count_after_event", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "daily_customer_outcomes",
        sa.Column("days_since_last_purchase", sa.Integer(), nullable=True),
    )
    op.alter_column(
        "daily_customer_outcomes",
        "purchase_count_after_event",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("daily_customer_outcomes", "days_since_last_purchase")
    op.drop_column("daily_customer_outcomes", "purchase_count_after_event")
    op.drop_column("customers", "segment")
