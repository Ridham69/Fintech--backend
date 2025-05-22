"""create admin tables

Revision ID: create_admin_tables
Revises: previous_revision
Create Date: 2024-03-14 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'create_admin_tables'
down_revision: Union[str, None] = 'previous_revision'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Create admin users and audit logs tables."""
    # Create admin_roles enum
    op.execute("""
        CREATE TYPE adminrole AS ENUM (
            'super_admin',
            'compliance',
            'support',
            'operations'
        )
    """)
    
    # Create admin_scopes enum
    op.execute("""
        CREATE TYPE adminscope AS ENUM (
            'admin:read:users',
            'admin:read:kyc',
            'admin:read:transactions',
            'admin:read:audit',
            'admin:read:system',
            'admin:act:freeze',
            'admin:act:notify',
            'admin:act:kyc',
            'admin:act:system'
        )
    """)
    
    # Create admin_users table
    op.create_table(
        'admin_users',
        sa.Column('id', postgresql.GUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.GUID(), nullable=False, unique=True, index=True),
        sa.Column('roles', postgresql.ARRAY(sa.Enum('super_admin', 'compliance', 'support', 'operations', name='adminrole')), nullable=False),
        sa.Column('scopes', postgresql.ARRAY(sa.Enum(
            'admin:read:users', 'admin:read:kyc', 'admin:read:transactions',
            'admin:read:audit', 'admin:read:system', 'admin:act:freeze',
            'admin:act:notify', 'admin:act:kyc', 'admin:act:system',
            name='adminscope'
        )), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('last_login', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), onupdate=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='fk_admin_users_user_id')
    )
    
    # Create admin_audit_logs table
    op.create_table(
        'admin_audit_logs',
        sa.Column('id', postgresql.GUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('admin_id', postgresql.GUID(), nullable=False, index=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', postgresql.GUID(), index=True),
        sa.Column('details', sa.String()),
        sa.Column('ip_address', sa.String(45), nullable=False),
        sa.Column('user_agent', sa.String(500), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), index=True),
        sa.ForeignKeyConstraint(['admin_id'], ['admin_users.id'], ondelete='CASCADE', name='fk_admin_audit_logs_admin_id')
    )
    
    # Add indexes
    op.create_index(
        'ix_admin_audit_logs_action_resource',
        'admin_audit_logs',
        ['action', 'resource_type', 'resource_id']
    )
    
    # Add comments
    op.execute("""
        COMMENT ON TABLE admin_users IS 'Admin users with role-based access control';
        COMMENT ON COLUMN admin_users.id IS 'Unique identifier for the admin user';
        COMMENT ON COLUMN admin_users.user_id IS 'ID of the associated user';
        COMMENT ON COLUMN admin_users.roles IS 'Array of admin roles';
        COMMENT ON COLUMN admin_users.scopes IS 'Array of permission scopes';
        COMMENT ON COLUMN admin_users.is_active IS 'Whether the admin account is active';
        COMMENT ON COLUMN admin_users.last_login IS 'Last login timestamp';
        COMMENT ON COLUMN admin_users.created_at IS 'When the admin user was created';
        COMMENT ON COLUMN admin_users.updated_at IS 'When the admin user was last updated';
        
        COMMENT ON TABLE admin_audit_logs IS 'Audit trail of admin actions';
        COMMENT ON COLUMN admin_audit_logs.id IS 'Unique identifier for the audit log';
        COMMENT ON COLUMN admin_audit_logs.admin_id IS 'ID of the admin who performed the action';
        COMMENT ON COLUMN admin_audit_logs.action IS 'Action performed';
        COMMENT ON COLUMN admin_audit_logs.resource_type IS 'Type of resource affected';
        COMMENT ON COLUMN admin_audit_logs.resource_id IS 'ID of resource affected';
        COMMENT ON COLUMN admin_audit_logs.details IS 'Additional details about the action';
        COMMENT ON COLUMN admin_audit_logs.ip_address IS 'IP address of the admin';
        COMMENT ON COLUMN admin_audit_logs.user_agent IS 'User agent of the admin';
        COMMENT ON COLUMN admin_audit_logs.created_at IS 'When the action was performed';
    """)

def downgrade() -> None:
    """Drop admin tables."""
    op.drop_table('admin_audit_logs')
    op.drop_table('admin_users')
    op.execute('DROP TYPE adminscope')
    op.execute('DROP TYPE adminrole') 
