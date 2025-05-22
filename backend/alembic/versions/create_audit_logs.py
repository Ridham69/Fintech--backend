"""create audit logs table

Revision ID: create_audit_logs
Revises: previous_revision
Create Date: 2024-03-14 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'create_audit_logs'
down_revision: Union[str, None] = 'previous_revision'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Create audit_logs table."""
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True, index=True),
        sa.Column('action', sa.String(100), nullable=False, index=True),
        sa.Column('target_table', sa.String(100), nullable=False, index=True),
        sa.Column('target_id', sa.String(100), nullable=False, index=True),
        sa.Column('ip_address', sa.String(45), nullable=False),
        sa.Column('user_agent', sa.String(500), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), index=True),
        sa.Column('metadata', postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Index('ix_audit_logs_user_id_action', 'user_id', 'action'),
        sa.Index('ix_audit_logs_target_table_target_id', 'target_table', 'target_id'),
        sa.Index('ix_audit_logs_timestamp_desc', 'timestamp', postgresql_ops={'timestamp': 'DESC'})
    )
    
    # Add comments
    op.execute("""
        COMMENT ON TABLE audit_logs IS 'Audit trail of system events';
        COMMENT ON COLUMN audit_logs.id IS 'Unique identifier for the audit log entry';
        COMMENT ON COLUMN audit_logs.user_id IS 'ID of the user who performed the action';
        COMMENT ON COLUMN audit_logs.action IS 'Action performed (e.g., kyc.update, transaction.create)';
        COMMENT ON COLUMN audit_logs.target_table IS 'Table where the action was performed';
        COMMENT ON COLUMN audit_logs.target_id IS 'ID of the affected record';
        COMMENT ON COLUMN audit_logs.ip_address IS 'IP address of the actor';
        COMMENT ON COLUMN audit_logs.user_agent IS 'User agent of the actor';
        COMMENT ON COLUMN audit_logs.timestamp IS 'When the action was performed';
        COMMENT ON COLUMN audit_logs.metadata IS 'Additional event metadata (e.g., changes, context)';
    """)

def downgrade() -> None:
    """Drop audit_logs table."""
    op.drop_table('audit_logs') 
