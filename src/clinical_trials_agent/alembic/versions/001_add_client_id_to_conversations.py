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
    op.execute(
        "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS "
        "client_id VARCHAR(64) NOT NULL DEFAULT 'default'"
    )
    op.execute("ALTER TABLE conversations ALTER COLUMN client_id DROP DEFAULT")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_conversations_client_id "
        "ON conversations (client_id)"
    )


def downgrade() -> None:
    op.drop_index("ix_conversations_client_id", table_name="conversations")
    op.drop_column("conversations", "client_id")
