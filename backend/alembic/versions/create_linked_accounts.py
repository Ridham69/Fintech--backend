"""create linked accounts

Revision ID: create_linked_accounts
Revises: previous_revision
Create Date: 2024-03-14 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'create_linked_accounts'
down_revision: Union[str, None] = 'previous_revision'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Create linked accounts table."""
    # Create account_type enum
    op.execute("""
        CREATE TYPE accounttype AS ENUM (
            'bank',
            'upi',
            'card',
            'wallet'
        )
    """)
    
    # Create linked_accounts table
    op.create_table(
        'linked_accounts',
        sa.Column('id', postgresql.GUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.GUID(), nullable=False, index=True),
        sa.Column('account_type', sa.Enum('bank', 'upi', 'card', 'wallet', name='accounttype'), nullable=False),
        sa.Column('provider', sa.String(100), nullable=False),
        sa.Column('account_number_masked', sa.String(50), nullable=False),
        sa.Column('account_ref_id', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('is_primary', sa.Boolean(), nullable=False, default=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('metadata', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='fk_linked_accounts_user_id')
    )
    
    # Add indexes
    op.create_index(
        'ix_linked_accounts_user_primary',
        'linked_accounts',
        ['user_id', 'is_primary'],
        unique=True,
        postgresql_where=sa.text('is_primary = true')
    )
    
    # Add comments
    op.execute("""
        COMMENT ON TABLE linked_accounts IS 'Linked external accounts and wallets';
        COMMENT ON COLUMN linked_accounts.id IS 'Unique identifier for the linked account';
        COMMENT ON COLUMN linked_accounts.user_id IS 'ID of the user who owns this account';
        COMMENT ON COLUMN linked_accounts.account_type IS 'Type of account (bank, upi, card, wallet)';
        COMMENT ON COLUMN linked_accounts.provider IS 'Provider name (e.g. SBI, Google Pay)';
        COMMENT ON COLUMN linked_accounts.account_number_masked IS 'Masked account number';
        COMMENT ON COLUMN linked_accounts.account_ref_id IS 'External reference or tokenized ID';
        COMMENT ON COLUMN linked_accounts.is_primary IS 'Whether this is the primary account';
        COMMENT ON COLUMN linked_accounts.is_active IS 'Whether this account is active';
        COMMENT ON COLUMN linked_accounts.metadata IS 'Additional account metadata';
        COMMENT ON COLUMN linked_accounts.created_at IS 'When the account was linked';
        COMMENT ON COLUMN linked_accounts.updated_at IS 'When the account was last updated';
    """)

def downgrade() -> None:
    """Drop linked accounts table."""
    op.drop_table('linked_accounts')
    op.execute('DROP TYPE accounttype') 
