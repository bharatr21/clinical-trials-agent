"""Add client_id to conversations table.

Revision ID: 001
Revises:
Create Date: 2025-01-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add client_id column with default value for existing rows
    op.add_column(
        "conversations",
        sa.Column("client_id", sa.String(64), nullable=False, server_default="default"),
    )
    # Create index for efficient filtering by client_id
    op.create_index("ix_conversations_client_id", "conversations", ["client_id"])


def downgrade() -> None:
    op.drop_index("ix_conversations_client_id", table_name="conversations")
    op.drop_column("conversations", "client_id")
