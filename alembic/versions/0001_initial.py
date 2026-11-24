"""Initial Beacon schema."""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("password_hash", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "organisations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_organisations_slug", "organisations", ["slug"], unique=True)
    op.create_table(
        "memberships",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.UniqueConstraint("user_id", "organisation_id"),
    )
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"])
    op.create_index("ix_memberships_organisation_id", "memberships", ["organisation_id"])
    op.create_table(
        "applications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("key", sa.String(80), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organisation_id", "key"),
    )
    op.create_index("ix_applications_organisation_id", "applications", ["organisation_id"])
    op.create_table(
        "environments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("application_id", sa.String(36), sa.ForeignKey("applications.id"), nullable=False),
        sa.Column("key", sa.String(80), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.UniqueConstraint("application_id", "key"),
    )
    op.create_index("ix_environments_application_id", "environments", ["application_id"])
    op.create_table(
        "sdk_keys",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("environment_id", sa.String(36), sa.ForeignKey("environments.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sdk_keys_environment_id", "sdk_keys", ["environment_id"])
    op.create_index("ix_sdk_keys_token_hash", "sdk_keys", ["token_hash"], unique=True)
    op.create_table(
        "feature_flags",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("application_id", sa.String(36), sa.ForeignKey("applications.id"), nullable=False),
        sa.Column("key", sa.String(80), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("variations", sa.JSON(), nullable=False),
        sa.UniqueConstraint("application_id", "key"),
    )
    op.create_index("ix_feature_flags_application_id", "feature_flags", ["application_id"])
    op.create_table(
        "flag_environments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("flag_id", sa.String(36), sa.ForeignKey("feature_flags.id"), nullable=False),
        sa.Column("environment_id", sa.String(36), sa.ForeignKey("environments.id"), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("off_variation", sa.String(80), nullable=False),
        sa.Column("fallthrough_variation", sa.String(80), nullable=False),
        sa.Column("rollout_basis_points", sa.Integer(), nullable=True),
        sa.Column("salt", sa.String(80), nullable=False),
        sa.Column("rules", sa.JSON(), nullable=False),
        sa.UniqueConstraint("flag_id", "environment_id"),
    )
    op.create_index("ix_flag_environments_flag_id", "flag_environments", ["flag_id"])
    op.create_index("ix_flag_environments_environment_id", "flag_environments", ["environment_id"])
    op.create_table(
        "segments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("application_id", sa.String(36), sa.ForeignKey("applications.id"), nullable=False),
        sa.Column("key", sa.String(80), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("clauses", sa.JSON(), nullable=False),
        sa.UniqueConstraint("application_id", "key"),
    )
    op.create_index("ix_segments_application_id", "segments", ["application_id"])
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organisation_id", sa.String(36), sa.ForeignKey("organisations.id"), nullable=False),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("resource", sa.String(200), nullable=False),
        sa.Column("detail", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_org_time", "audit_logs", ["organisation_id", "created_at"])
    op.create_table(
        "evaluation_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("environment_id", sa.String(36), sa.ForeignKey("environments.id"), nullable=False),
        sa.Column("flag_key", sa.String(80), nullable=False),
        sa.Column("user_key", sa.String(200), nullable=False),
        sa.Column("variation", sa.String(80), nullable=False),
        sa.Column("reason", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_events_env_time", "evaluation_events", ["environment_id", "created_at"])
    op.create_index("ix_evaluation_events_created_at", "evaluation_events", ["created_at"])


def downgrade() -> None:
    for name in (
        "evaluation_events",
        "audit_logs",
        "segments",
        "flag_environments",
        "feature_flags",
        "sdk_keys",
        "environments",
        "applications",
        "memberships",
        "organisations",
        "users",
    ):
        op.drop_table(name)
