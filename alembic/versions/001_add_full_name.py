"""add_full_name_to_context_profile

Revision ID: 001_add_full_name
Revises: 
Create Date: 2026-08-08

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "001_add_full_name"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "context_profile",
        sa.Column("full_name", sa.String(255), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("context_profile", "full_name")
