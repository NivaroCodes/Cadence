"""add composite index to messages

Revision ID: 29d4286a9127
Revises: d76dd12ff473
Create Date: 2026-05-24 06:08:37.185367

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '29d4286a9127'
down_revision: Union[str, Sequence[str], None] = 'd76dd12ff473'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index('ix_messages_campaign_lead_seq', 'messages', ['campaign_id', 'lead_id', 'sequence_number'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_messages_campaign_lead_seq', table_name='messages')
