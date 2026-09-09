"""Make metrics columns nullable and add supporting resource columns.

Revision ID: 0002_nullable_metrics
Revises: 0001_initial
Create Date: 2026-09-09
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002_nullable_metrics"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Make core metrics nullable in metrics table
    for col in ["cpu_usage", "memory_usage", "disk_usage", "load_1m", "load_5m", "load_15m"]:
        op.alter_column("metrics", col, existing_type=sa.Float(), nullable=True)

    op.alter_column("metrics", "cpu_count", existing_type=sa.Integer(), nullable=True, server_default=None)

    # 2. Add extra memory and disk breakdown columns if not present
    op.add_column("metrics", sa.Column("memory_total_mb", sa.Float(), nullable=True))
    op.add_column("metrics", sa.Column("memory_used_mb", sa.Float(), nullable=True))
    op.add_column("metrics", sa.Column("disk_total_gb", sa.Float(), nullable=True))
    op.add_column("metrics", sa.Column("disk_used_gb", sa.Float(), nullable=True))

    # 3. Add last_seen_at to incidents
    op.add_column("incidents", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("incidents", "last_seen_at")
    op.drop_column("metrics", "disk_used_gb")
    op.drop_column("metrics", "disk_total_gb")
    op.drop_column("metrics", "memory_used_mb")
    op.drop_column("metrics", "memory_total_mb")
    for col in ["cpu_usage", "memory_usage", "disk_usage", "load_1m", "load_5m", "load_15m"]:
        op.alter_column("metrics", col, existing_type=sa.Float(), nullable=False)
