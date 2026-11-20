"""Run-scoped authorization; no second model-usage ledger."""

from alembic import op
import sqlalchemy as sa

revision = "0002_gateway_grants"
down_revision = "0001_platform"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "rp_gateway_grants",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("run_id", sa.String(32), sa.ForeignKey("rp_runs.id"), nullable=False),
        sa.Column("token_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("allowed_models", sa.JSON(), nullable=False),
        sa.Column("max_output_tokens", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.Float(), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
    )
    op.create_index("ix_rp_gateway_grants_run_id", "rp_gateway_grants", ["run_id"])


def downgrade():
    op.drop_index("ix_rp_gateway_grants_run_id", table_name="rp_gateway_grants")
    op.drop_table("rp_gateway_grants")
