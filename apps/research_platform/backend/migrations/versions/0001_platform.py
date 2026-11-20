"""Initial project, workflow, event, artifact, usage and durable job schema."""

from alembic import op
import sqlalchemy as sa

revision = "0001_platform"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "rp_projects",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("domain", sa.String(120), nullable=False),
        sa.Column("objectives", sa.JSON(), nullable=False),
        sa.Column("references", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
    )
    op.create_table(
        "rp_runs",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("project_id", sa.String(32), sa.ForeignKey("rp_projects.id"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("current_stage", sa.String(60)),
        sa.Column("profile", sa.String(30), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("model", sa.String(180), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column("usage", sa.JSON(), nullable=False),
        sa.Column("approval", sa.JSON()),
        sa.Column("error", sa.Text()),
        sa.Column("control", sa.String(20)),
        sa.Column("started_at", sa.String(40)),
        sa.Column("created_at", sa.String(40), nullable=False),
        sa.Column("updated_at", sa.String(40), nullable=False),
    )
    op.create_table(
        "rp_jobs",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column(
            "run_id", sa.String(32), sa.ForeignKey("rp_runs.id"), unique=True, nullable=False
        ),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("owner", sa.String(100)),
        sa.Column("lease_until", sa.Float(), nullable=False),
        sa.Column("heartbeat_at", sa.String(40)),
        sa.Column("resume_payload", sa.JSON()),
        sa.Column("attempts", sa.Integer(), nullable=False),
    )
    op.create_table(
        "rp_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.String(32), sa.ForeignKey("rp_runs.id"), nullable=False),
        sa.Column("stage", sa.String(60), nullable=False),
        sa.Column("kind", sa.String(60), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
    )
    op.create_table(
        "rp_decisions",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("run_id", sa.String(32), sa.ForeignKey("rp_runs.id"), nullable=False),
        sa.Column("stage", sa.String(60), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
    )
    op.create_table(
        "rp_experiments",
        sa.Column("id", sa.String(80), primary_key=True),
        sa.Column("run_id", sa.String(32), sa.ForeignKey("rp_runs.id"), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("hypothesis", sa.Text(), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("logs", sa.Text(), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("artifact_ids", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.String(40), nullable=False),
        sa.Column("finished_at", sa.String(40)),
    )
    op.create_table(
        "rp_artifacts",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("run_id", sa.String(32), sa.ForeignKey("rp_runs.id"), nullable=False),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("media_type", sa.String(100), nullable=False),
        sa.Column("relative_path", sa.String(500), unique=True, nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
    )
    op.create_table(
        "rp_model_usage",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column("run_id", sa.String(32), sa.ForeignKey("rp_runs.id"), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("model", sa.String(180), nullable=False),
        sa.Column("stage", sa.String(60), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("reserved_output_tokens", sa.Integer(), nullable=False),
        sa.Column("estimated_cost", sa.Float()),
        sa.Column("reported", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
    )
    op.create_table(
        "rp_research_items",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("run_id", sa.String(32), sa.ForeignKey("rp_runs.id"), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
    )
    op.create_table(
        "rp_traces",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("run_id", sa.String(32), sa.ForeignKey("rp_runs.id"), nullable=False),
        sa.Column("url", sa.Text()),
        sa.Column("data", sa.JSON(), nullable=False),
    )
    for table, columns in {
        "rp_runs": ["project_id", "status"],
        "rp_jobs": ["status"],
        "rp_events": ["run_id"],
        "rp_decisions": ["run_id"],
        "rp_experiments": ["run_id"],
        "rp_artifacts": ["run_id"],
        "rp_model_usage": ["run_id", "created_at"],
        "rp_research_items": ["run_id"],
        "rp_traces": ["run_id"],
    }.items():
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade():
    for table in [
        "rp_traces",
        "rp_research_items",
        "rp_model_usage",
        "rp_artifacts",
        "rp_experiments",
        "rp_decisions",
        "rp_events",
        "rp_jobs",
        "rp_runs",
        "rp_projects",
    ]:
        op.drop_table(table)
