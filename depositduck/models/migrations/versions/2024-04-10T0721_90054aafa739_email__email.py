"""email__email

Revision ID: 90054aafa739
Revises: 28239c78fe9f
Create Date: 2024-04-10 07:21:47.833766

(c) 2024 Alberto Morón Hernández
"""

from typing import Sequence, Union

import sqlalchemy as sa
import sqlmodel
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "90054aafa739"
down_revision: Union[str, None] = "28239c78fe9f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "email__email",
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
        sa.Column("sender_address", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column(
            "recipient_address", sqlmodel.sql.sqltypes.AutoString(), nullable=False
        ),
        sa.Column("subject", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("body", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("recipient_id", UUID(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["recipient_id"],
            ["auth__user.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("email__email")
