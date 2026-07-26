"""add operational research source report

Revision ID: c6a5e2f84b17
Revises: b4f1a8c2d903
Create Date: 2026-07-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c6a5e2f84b17"
down_revision: str | None = "b4f1a8c2d903"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("enrichment_jobs", sa.Column("source_report", sa.JSON(), nullable=True))
    op.add_column(
        "enrichment_jobs", sa.Column("ai_model", sa.String(length=120), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("enrichment_jobs", "ai_model")
    op.drop_column("enrichment_jobs", "source_report")
