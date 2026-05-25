"""add_multi_tenant_base

Revision ID: 4fb66c8f2b84
Revises: 577eec80d419
Create Date: 2026-05-25 15:07:01.679805

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4fb66c8f2b84'
down_revision: Union[str, Sequence[str], None] = '577eec80d419'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 2. Insert Default Admin User with secure pre-generated bcrypt hash
    # AdminDefaultPassword123! -> $2b$12$kqmhJcDUSQHyV.MtX1aOWODcJcnRFOBWEJB6I1YL.mIX.X/tKRAKe
    admin_uuid = '00000000-0000-0000-0000-000000000000'
    op.execute(
        f"INSERT INTO users (id, email, hashed_password, is_active) VALUES "
        f"('{admin_uuid}', 'admin@cadence.kz', '$2b$12$kqmhJcDUSQHyV.MtX1aOWODcJcnRFOBWEJB6I1YL.mIX.X/tKRAKe', true)"
    )

    # 3. Create gmail_credentials table
    op.create_table(
        'gmail_credentials',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('token', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_gmail_credentials_user_id'), 'gmail_credentials', ['user_id'], unique=False)

    # 4. Create api_keys table
    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('key_hash', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('prefix', sa.String(length=10), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index(op.f('ix_api_keys_key_hash'), 'api_keys', ['key_hash'], unique=True)
    op.create_index(op.f('ix_api_keys_user_id'), 'api_keys', ['user_id'], unique=False)

    # 5. Add user_id column as nullable initially to allow safe data backfill
    op.add_column('leads', sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('campaigns', sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('messages', sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True))

    # 6. Backfill existing records to our static system admin
    op.execute(f"UPDATE leads SET user_id = '{admin_uuid}' WHERE user_id IS NULL")
    op.execute(f"UPDATE campaigns SET user_id = '{admin_uuid}' WHERE user_id IS NULL")
    op.execute(f"UPDATE messages SET user_id = '{admin_uuid}' WHERE user_id IS NULL")

    # 7. Make the columns non-nullable after backfill is completed
    op.alter_column('leads', 'user_id', nullable=False)
    op.alter_column('campaigns', 'user_id', nullable=False)
    op.alter_column('messages', 'user_id', nullable=False)

    # 8. Create Foreign Key constraints with CASCADE delete for strict isolation
    op.create_foreign_key('fk_leads_user_id', 'leads', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_campaigns_user_id', 'campaigns', 'users', ['user_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_messages_user_id', 'messages', 'users', ['user_id'], ['id'], ondelete='CASCADE')

    # 9. Create composite indexes on (user_id, created_at) for fast multi-tenant sorted queries
    op.create_index('ix_leads_user_created_at', 'leads', ['user_id', 'created_at'], unique=False)
    op.create_index('ix_campaigns_user_created_at', 'campaigns', ['user_id', 'created_at'], unique=False)
    op.create_index('ix_messages_user_created_at', 'messages', ['user_id', 'created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # 1. Drop composite indexes
    op.drop_index('ix_messages_user_created_at', table_name='messages')
    op.drop_index('ix_campaigns_user_created_at', table_name='campaigns')
    op.drop_index('ix_leads_user_created_at', table_name='leads')

    # 2. Drop Foreign Key constraints
    op.drop_constraint('fk_messages_user_id', 'messages', type_='foreignkey')
    op.drop_constraint('fk_campaigns_user_id', 'campaigns', type_='foreignkey')
    op.drop_constraint('fk_leads_user_id', 'leads', type_='foreignkey')

    # 3. Drop columns
    op.drop_column('messages', 'user_id')
    op.drop_column('campaigns', 'user_id')
    op.drop_column('leads', 'user_id')

    # 4. Drop api_keys, gmail_credentials, and users tables
    op.drop_index(op.f('ix_api_keys_user_id'), table_name='api_keys')
    op.drop_index(op.f('ix_api_keys_key_hash'), table_name='api_keys')
    op.drop_table('api_keys')

    op.drop_index(op.f('ix_gmail_credentials_user_id'), table_name='gmail_credentials')
    op.drop_table('gmail_credentials')

    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
