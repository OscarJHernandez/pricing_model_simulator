"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-03-28

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "simulation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("baseline_end_day", sa.Integer(), nullable=False),
        sa.Column("experiment_start_day", sa.Integer(), nullable=False),
        sa.Column("customer_count", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_simulation_runs_status"), "simulation_runs", ["status"], unique=False
    )

    op.create_table(
        "run_parameters",
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "config", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.ForeignKeyConstraint(["run_id"], ["simulation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("run_id"),
    )

    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_index", sa.Integer(), nullable=False),
        sa.Column("budget", sa.Float(), nullable=False),
        sa.Column("buy_propensity", sa.Float(), nullable=False),
        sa.Column("price_threshold", sa.Float(), nullable=False),
        sa.Column("repeat_boost", sa.Float(), nullable=False),
        sa.Column("basket_mean", sa.Float(), nullable=False),
        sa.Column("location_zone", sa.String(length=64), nullable=False),
        sa.Column("acquisition_channel", sa.String(length=64), nullable=True),
        sa.Column("retention_sensitivity", sa.Float(), nullable=True),
        sa.Column("promo_sensitivity", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["simulation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "customer_index", name="uq_customers_run_index"),
    )
    op.create_index(op.f("ix_customers_run_id"), "customers", ["run_id"], unique=False)

    op.create_table(
        "experiment_assignments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("treatment", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(
            ["customer_id"], ["customers.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["run_id"], ["simulation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("customer_id"),
    )
    op.create_index(
        op.f("ix_experiment_assignments_run_id"),
        "experiment_assignments",
        ["run_id"],
        unique=False,
    )

    op.create_table(
        "daily_customer_outcomes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("phase", sa.String(length=16), nullable=False),
        sa.Column("treatment", sa.String(length=32), nullable=True),
        sa.Column("offered_total_price", sa.Float(), nullable=False),
        sa.Column("purchase_probability", sa.Float(), nullable=False),
        sa.Column("purchased", sa.Boolean(), nullable=False),
        sa.Column("order_value", sa.Float(), nullable=False),
        sa.Column("gross_revenue", sa.Float(), nullable=False),
        sa.Column("discount_amount", sa.Float(), nullable=False),
        sa.Column("net_revenue", sa.Float(), nullable=False),
        sa.Column("variable_cost", sa.Float(), nullable=False),
        sa.Column("contribution_margin", sa.Float(), nullable=False),
        sa.Column("incremental_order", sa.Boolean(), nullable=False),
        sa.Column("counterfactual_would_buy", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(
            ["customer_id"], ["customers.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["run_id"], ["simulation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_id", "day", "customer_id", name="uq_outcome_run_day_customer"
        ),
    )
    op.create_index(
        op.f("ix_daily_customer_outcomes_customer_id"),
        "daily_customer_outcomes",
        ["customer_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_daily_customer_outcomes_day"),
        "daily_customer_outcomes",
        ["day"],
        unique=False,
    )
    op.create_index(
        op.f("ix_daily_customer_outcomes_run_id"),
        "daily_customer_outcomes",
        ["run_id"],
        unique=False,
    )

    op.create_table(
        "daily_aggregates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day", sa.Integer(), nullable=False),
        sa.Column("phase", sa.String(length=16), nullable=False),
        sa.Column("treatment", sa.String(length=32), nullable=True),
        sa.Column("location_zone", sa.String(length=64), nullable=True),
        sa.Column(
            "metrics", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.ForeignKeyConstraint(["run_id"], ["simulation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "run_id",
            "day",
            "phase",
            "treatment",
            "location_zone",
            name="uq_agg_run_day_phase_treat_zone",
        ),
    )
    op.create_index(
        op.f("ix_daily_aggregates_day"), "daily_aggregates", ["day"], unique=False
    )
    op.create_index(
        op.f("ix_daily_aggregates_run_id"), "daily_aggregates", ["run_id"], unique=False
    )

    op.create_table(
        "promo_budget_tracking",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day", sa.Integer(), nullable=False),
        sa.Column("discount_spend_day", sa.Float(), nullable=False),
        sa.Column("cumulative_discount_spend", sa.Float(), nullable=False),
        sa.Column("remaining_budget", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["simulation_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("run_id", "day", name="uq_promo_budget_run_day"),
    )
    op.create_index(
        op.f("ix_promo_budget_tracking_day"),
        "promo_budget_tracking",
        ["day"],
        unique=False,
    )
    op.create_index(
        op.f("ix_promo_budget_tracking_run_id"),
        "promo_budget_tracking",
        ["run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_promo_budget_tracking_run_id"), table_name="promo_budget_tracking")
    op.drop_index(op.f("ix_promo_budget_tracking_day"), table_name="promo_budget_tracking")
    op.drop_table("promo_budget_tracking")
    op.drop_index(op.f("ix_daily_aggregates_run_id"), table_name="daily_aggregates")
    op.drop_index(op.f("ix_daily_aggregates_day"), table_name="daily_aggregates")
    op.drop_table("daily_aggregates")
    op.drop_index(op.f("ix_daily_customer_outcomes_run_id"), table_name="daily_customer_outcomes")
    op.drop_index(op.f("ix_daily_customer_outcomes_day"), table_name="daily_customer_outcomes")
    op.drop_index(op.f("ix_daily_customer_outcomes_customer_id"), table_name="daily_customer_outcomes")
    op.drop_table("daily_customer_outcomes")
    op.drop_index(op.f("ix_experiment_assignments_run_id"), table_name="experiment_assignments")
    op.drop_table("experiment_assignments")
    op.drop_index(op.f("ix_customers_run_id"), table_name="customers")
    op.drop_table("customers")
    op.drop_table("run_parameters")
    op.drop_index(op.f("ix_simulation_runs_status"), table_name="simulation_runs")
    op.drop_table("simulation_runs")
