"""llm__snippet

Revision ID: d6e60a817251
Revises: cb55ea348903
Create Date: 2024-03-23 12:34:01.564063

(c) 2024 Alberto Morón Hernández
"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "d6e60a817251"
down_revision: Union[str, None] = "cb55ea348903"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "llm__snippet",
        sa.Column(
            "id",
            UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("source_text_id", UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_text_id"],
            ["llm__source_text.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_unique_constraint(
        "uq_source_text_content", "llm__snippet", ["source_text_id", "content"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_source_text_content", "llm__snippet", type_="unique")
    op.drop_table("llm__snippet")
