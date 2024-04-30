"""
Mixins to help build base models and tables in the context-specific
modules (auth, LLM, etc.) in this package.

(c) 2024 Alberto Morón Hernández
"""

from datetime import datetime
from uuid import UUID

import sqlalchemy as sa
from pydantic import BaseModel
from sqlalchemy import func
from sqlmodel import Field, SQLModel

# --- Table models -----------------------------------------------------------------------


class IdMixin:
    id: UUID = Field(
        primary_key=True,
        sa_column_kwargs=dict(server_default=func.gen_random_uuid()),
    )


class CreatedAtMixin:
    created_at: datetime = Field(  # type: ignore
        sa_type=sa.DateTime(timezone=True),
        sa_column_kwargs=dict(server_default=func.now()),
    )


# TODO: created_by
# TODO: updated_at, updated_by, etc. should be inferred from an `audit` table
# updated_at: datetime | None = Field(
#     sa_column=Column(DateTime(), onupdate=func.now())
# )


class DeletedAtMixin:
    deleted_at: datetime | None = Field(sa_type=sa.DateTime(timezone=True), nullable=True)  # type: ignore


class TableBase(SQLModel, DeletedAtMixin, CreatedAtMixin, IdMixin):
    pass


# --- Request bodies ---------------------------------------------------------------------


class EntityById(BaseModel):
    id: UUID


# --- Response objects -------------------------------------------------------------------


class TwoOhOneCreatedCount(BaseModel):
    created_count: int
