"""generalise enrichment and add confidence governance

Revision ID: b4f1a8c2d903
Revises: 91c3d5a7e204
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b4f1a8c2d903"
down_revision: str | None = "91c3d5a7e204"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("enrichment_jobs", "coaster_id", existing_type=sa.Uuid(), nullable=True)
    op.add_column("enrichment_jobs", sa.Column("park_id", sa.Uuid(), nullable=True))
    op.add_column("enrichment_jobs", sa.Column("manufacturer_id", sa.Uuid(), nullable=True))
    op.add_column(
        "enrichment_jobs",
        sa.Column("entity_type", sa.String(length=24), server_default="coaster", nullable=False),
    )
    op.add_column("enrichment_jobs", sa.Column("entity_id", sa.Uuid(), nullable=True))
    op.add_column(
        "enrichment_jobs", sa.Column("entity_match_confidence", sa.Float(), nullable=True)
    )
    op.execute("UPDATE enrichment_jobs SET entity_id = coaster_id WHERE entity_id IS NULL")
    op.alter_column("enrichment_jobs", "entity_id", existing_type=sa.Uuid(), nullable=False)
    op.create_foreign_key(
        "fk_enrichment_jobs_park", "enrichment_jobs", "parks", ["park_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        "fk_enrichment_jobs_manufacturer",
        "enrichment_jobs",
        "manufacturers",
        ["manufacturer_id"],
        ["id"],
        ondelete="CASCADE",
    )
    for column in ("park_id", "manufacturer_id", "entity_type", "entity_id"):
        op.create_index(f"ix_enrichment_jobs_{column}", "enrichment_jobs", [column])

    op.add_column("field_proposals", sa.Column("reviewed_value", sa.JSON(), nullable=True))
    op.add_column(
        "field_proposals",
        sa.Column(
            "confidence_class",
            sa.String(length=32),
            server_default="needs_review",
            nullable=False,
        ),
    )
    op.add_column(
        "field_proposals",
        sa.Column("automation_class", sa.String(length=1), server_default="B", nullable=False),
    )
    op.add_column("field_proposals", sa.Column("score_breakdown", sa.JSON(), nullable=True))
    op.add_column(
        "field_proposals",
        sa.Column("has_conflict", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "field_proposals",
        sa.Column(
            "auto_approval_eligible", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
    )
    op.add_column(
        "field_proposals",
        sa.Column("is_manual_override", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    for column in (
        "confidence_class",
        "has_conflict",
        "auto_approval_eligible",
        "is_manual_override",
    ):
        op.create_index(f"ix_field_proposals_{column}", "field_proposals", [column])

    op.add_column("source_evidence", sa.Column("asserted_value", sa.JSON(), nullable=True))
    op.add_column("source_evidence", sa.Column("source_confidence", sa.Float(), nullable=True))
    op.add_column(
        "source_evidence",
        sa.Column("is_primary", sa.Boolean(), server_default=sa.false(), nullable=False),
    )

    op.create_table(
        "external_identifiers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=24), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("scheme", sa.String(length=50), nullable=False),
        sa.Column("value", sa.String(length=500), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "entity_type", "entity_id", "scheme", name="uq_external_identifier_entity_scheme"
        ),
    )
    for column in ("entity_type", "entity_id", "scheme", "value"):
        op.create_index(f"ix_external_identifiers_{column}", "external_identifiers", [column])

    op.create_table(
        "canonical_overrides",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=24), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("field_name", sa.String(length=80), nullable=False),
        sa.Column("value", sa.JSON(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "entity_type", "entity_id", "field_name", name="uq_canonical_override_entity_field"
        ),
    )
    for column in ("entity_type", "entity_id", "field_name", "created_by_id", "is_active"):
        op.create_index(f"ix_canonical_overrides_{column}", "canonical_overrides", [column])


def downgrade() -> None:
    op.drop_table("canonical_overrides")
    op.drop_table("external_identifiers")
    for column in (
        "is_manual_override",
        "auto_approval_eligible",
        "has_conflict",
        "confidence_class",
    ):
        op.drop_index(f"ix_field_proposals_{column}", table_name="field_proposals")
    for column in (
        "is_manual_override",
        "auto_approval_eligible",
        "has_conflict",
        "score_breakdown",
        "automation_class",
        "confidence_class",
        "reviewed_value",
    ):
        op.drop_column("field_proposals", column)
    for column in ("is_primary", "source_confidence", "asserted_value"):
        op.drop_column("source_evidence", column)
    for column in ("entity_id", "entity_type", "manufacturer_id", "park_id"):
        op.drop_index(f"ix_enrichment_jobs_{column}", table_name="enrichment_jobs")
    op.drop_constraint("fk_enrichment_jobs_manufacturer", "enrichment_jobs", type_="foreignkey")
    op.drop_constraint("fk_enrichment_jobs_park", "enrichment_jobs", type_="foreignkey")
    for column in (
        "entity_match_confidence",
        "entity_id",
        "entity_type",
        "manufacturer_id",
        "park_id",
    ):
        op.drop_column("enrichment_jobs", column)
    op.alter_column("enrichment_jobs", "coaster_id", existing_type=sa.Uuid(), nullable=False)
