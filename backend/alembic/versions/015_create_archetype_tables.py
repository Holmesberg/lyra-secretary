"""create archetype + assignment tables and seed 5 archetypes

Revision ID: 015
Revises: 014
Create Date: 2026-04-09

Multi-user pivot Phase 1. Implements clustering_spec.md §4 and §7:
- archetype lookup (5 hand-seeded rows from the literature priors)
- archetype_assignment per-user (raw instrument scores + assigned slug)

Slug primary keys per Q2 confirmation (Apr 9 2026).
"""
from alembic import op
import sqlalchemy as sa

revision = "015"
down_revision = "014"
branch_labels = None
depends_on = None


ARCHETYPES = [
    ("disciplined_lark",     "Disciplined Lark",     0.95, 0.15, "Closest to plan; slight underestimate. Buehler 1994."),
    ("disciplined_owl",      "Disciplined Owl",      1.05, 0.20, "Same discipline, mornings structurally harder."),
    ("diffuse_average",      "Diffuse Average",      1.30, 0.30, "Population midpoint. Roy 2005 meta-analytic 1.3x."),
    ("procrastinator",       "Procrastinator",       1.80, 0.40, "Heavy planning-fallacy load. Steel 2010 1.6-2.2x."),
    ("lark_low_discipline",  "Lark Low-Discipline",  1.50, 0.35, "Morning chronotype partially compensates for low discipline."),
]


def upgrade():
    op.create_table(
        "archetype",
        sa.Column("archetype_id", sa.String(40), primary_key=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("prior_bias_factor", sa.Float(), nullable=False),
        sa.Column("prior_sigma", sa.Float(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
    )

    op.create_table(
        "archetype_assignment",
        sa.Column("assignment_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("archetype_id", sa.String(40), nullable=False),
        sa.Column("meq_score", sa.Integer(), nullable=True),
        sa.Column("bfi_c_score", sa.Integer(), nullable=True),
        sa.Column("bscs_score", sa.Integer(), nullable=True),
        sa.Column("gp_score", sa.Integer(), nullable=True),
        sa.Column("chronotype", sa.String(20), nullable=True),
        sa.Column("discipline_z", sa.Float(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_archetype_assignment_user", "archetype_assignment", ["user_id"])

    conn = op.get_bind()
    for slug, name, prior, sigma, desc in ARCHETYPES:
        conn.execute(
            sa.text(
                "INSERT INTO archetype (archetype_id, name, prior_bias_factor, prior_sigma, description) "
                "VALUES (:slug, :name, :prior, :sigma, :desc)"
            ),
            {"slug": slug, "name": name, "prior": prior, "sigma": sigma, "desc": desc},
        )


def downgrade():
    op.drop_index("idx_archetype_assignment_user", table_name="archetype_assignment")
    op.drop_table("archetype_assignment")
    op.drop_table("archetype")
