"""add enrichment review pipeline

Revision ID: 91c3d5a7e204
Revises: 5072395c6e0d
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "91c3d5a7e204"
down_revision: str | None = "5072395c6e0d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "enrichment_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("coaster_id", sa.Uuid(), nullable=False),
        sa.Column("requested_by_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("wikidata_id", sa.String(length=32), nullable=True),
        sa.Column("wikipedia_title", sa.String(length=300), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["coaster_id"], ["coasters.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_enrichment_jobs_coaster_id", "enrichment_jobs", ["coaster_id"])
    op.create_index(
        "ix_enrichment_jobs_requested_by_id", "enrichment_jobs", ["requested_by_id"]
    )
    op.create_index("ix_enrichment_jobs_status", "enrichment_jobs", ["status"])
    op.create_index("ix_enrichment_jobs_wikidata_id", "enrichment_jobs", ["wikidata_id"])

    op.create_table(
        "field_proposals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("field_name", sa.String(length=80), nullable=False),
        sa.Column("proposed_value", sa.JSON(), nullable=True),
        sa.Column("current_value", sa.JSON(), nullable=True),
        sa.Column("evidence_status", sa.String(length=24), nullable=False),
        sa.Column("proposal_status", sa.String(length=16), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("reviewed_by_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["job_id"], ["enrichment_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "field_name", name="uq_field_proposals_job_field"),
    )
    op.create_index("ix_field_proposals_job_id", "field_proposals", ["job_id"])
    op.create_index("ix_field_proposals_field_name", "field_proposals", ["field_name"])
    op.create_index(
        "ix_field_proposals_evidence_status", "field_proposals", ["evidence_status"]
    )
    op.create_index(
        "ix_field_proposals_proposal_status", "field_proposals", ["proposal_status"]
    )
    op.create_index(
        "ix_field_proposals_reviewed_by_id", "field_proposals", ["reviewed_by_id"]
    )

    op.create_table(
        "source_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("proposal_id", sa.Uuid(), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=False),
        sa.Column("source_label", sa.String(length=300), nullable=True),
        sa.Column(
            "retrieved_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("raw_value", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["proposal_id"], ["field_proposals.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_source_evidence_proposal_id", "source_evidence", ["proposal_id"])
    op.create_index("ix_source_evidence_source_type", "source_evidence", ["source_type"])


def downgrade() -> None:
    op.drop_index("ix_source_evidence_source_type", table_name="source_evidence")
    op.drop_index("ix_source_evidence_proposal_id", table_name="source_evidence")
    op.drop_table("source_evidence")
    op.drop_index("ix_field_proposals_reviewed_by_id", table_name="field_proposals")
    op.drop_index("ix_field_proposals_proposal_status", table_name="field_proposals")
    op.drop_index("ix_field_proposals_evidence_status", table_name="field_proposals")
    op.drop_index("ix_field_proposals_field_name", table_name="field_proposals")
    op.drop_index("ix_field_proposals_job_id", table_name="field_proposals")
    op.drop_table("field_proposals")
    op.drop_index("ix_enrichment_jobs_wikidata_id", table_name="enrichment_jobs")
    op.drop_index("ix_enrichment_jobs_status", table_name="enrichment_jobs")
    op.drop_index("ix_enrichment_jobs_requested_by_id", table_name="enrichment_jobs")
    op.drop_index("ix_enrichment_jobs_coaster_id", table_name="enrichment_jobs")
    op.drop_table("enrichment_jobs")
