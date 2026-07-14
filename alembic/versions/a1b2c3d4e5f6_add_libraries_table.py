"""add libraries table

Revision ID: a1b2c3d4e5f6
Revises: 52a6abce1999
Create Date: 2026-07-12 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "52a6abce1999"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "libraries",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("library_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("libraries", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_libraries_id"), ["id"], unique=False)
        batch_op.create_index(batch_op.f("ix_libraries_library_id"), ["library_id"], unique=True)

    # Seed a default "local" library that represents the existing filesystem gallery, carrying
    # over the previously global active filter so slideshow selection is unchanged after upgrade.
    connection = op.get_bind()
    active_filter_row = connection.execute(
        sa.text("SELECT value FROM config WHERE key = 'active_filter'")
    ).fetchone()
    active_filter_id = active_filter_row[0] if active_filter_row is not None else None
    filter_id = int(active_filter_id) if active_filter_id not in (None, "") else None

    libraries_table = sa.table(
        "libraries",
        sa.column("library_id", sa.String),
        sa.column("name", sa.String),
        sa.column("source_type", sa.String),
        sa.column("enabled", sa.Boolean),
        sa.column("weight", sa.Float),
        sa.column("config", sa.JSON),
    )
    op.bulk_insert(
        libraries_table,
        [
            {
                "library_id": "local",
                "name": "Local Gallery",
                "source_type": "local",
                "enabled": True,
                "weight": 1.0,
                "config": {"filter_id": filter_id},
            }
        ],
    )

    # Rewrite the legacy integer CURRENT_ACTIVE_IMAGE value ("N") into a composite id ("local:N")
    # so it resolves through the new library abstraction.
    connection.execute(
        sa.text(
            "UPDATE config SET value = 'local:' || value "
            "WHERE key = 'current_active_image' AND value IS NOT NULL AND value != '' "
            "AND value NOT LIKE '%:%'"
        )
    )


def downgrade() -> None:
    with op.batch_alter_table("libraries", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_libraries_library_id"))
        batch_op.drop_index(batch_op.f("ix_libraries_id"))

    op.drop_table("libraries")
