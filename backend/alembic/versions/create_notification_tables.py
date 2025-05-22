"""create notification tables

Revision ID: create_notification_tables
Revises: previous_revision
Create Date: 2024-03-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'create_notification_tables'
down_revision = 'previous_revision'  # Update this with your previous migration
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create notification categories enum type
    notification_category = postgresql.ENUM(
        'SYSTEM',
        'TRANSACTIONAL',
        'PROMOTIONAL',
        'SECURITY',
        'INVESTMENT',
        name='notification_category',
        create_type=False
    )
    notification_category.create(op.get_bind(), checkfirst=True)
    
    # Create notification priority enum type
    notification_priority = postgresql.ENUM(
        'LOW',
        'MEDIUM',
        'HIGH',
        'URGENT',
        name='notification_priority',
        create_type=False
    )
    notification_priority.create(op.get_bind(), checkfirst=True)
    
    # Create notification channel enum type
    notification_channel = postgresql.ENUM(
        'IN_APP',
        'EMAIL',
        'SMS',
        'PUSH',
        name='notification_channel',
        create_type=False
    )
    notification_channel.create(op.get_bind(), checkfirst=True)
    
    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('category', sa.Enum('SYSTEM', 'TRANSACTIONAL', 'PROMOTIONAL', 'SECURITY', 'INVESTMENT', name='notification_category'), nullable=False, server_default='SYSTEM'),
        sa.Column('priority', sa.Enum('LOW', 'MEDIUM', 'HIGH', 'URGENT', name='notification_priority'), nullable=False, server_default='MEDIUM'),
        sa.Column('channels', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create notification preferences table
    op.create_table(
        'notification_preferences',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('sms_enabled', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('push_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('in_app_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('system_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('transactional_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('promotional_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('security_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('investment_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('quiet_hours_start', sa.String(5), nullable=True),
        sa.Column('quiet_hours_end', sa.String(5), nullable=True),
        sa.Column('email_frequency', sa.String(10), nullable=False, server_default='IMMEDIATE'),
        sa.Column('sms_frequency', sa.String(10), nullable=False, server_default='IMMEDIATE'),
        sa.Column('push_frequency', sa.String(10), nullable=False, server_default='IMMEDIATE'),
        sa.Column('preferred_language', sa.String(5), nullable=False, server_default='en'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_notification_preferences_user_id')
    )
    
    # Create indexes
    op.create_index(
        'ix_notifications_user_id',
        'notifications',
        ['user_id']
    )
    op.create_index(
        'ix_notifications_category',
        'notifications',
        ['category']
    )
    op.create_index(
        'ix_notifications_created_at',
        'notifications',
        ['created_at']
    )
    op.create_index(
        'ix_notifications_is_read',
        'notifications',
        ['is_read']
    )
    op.create_index(
        'ix_notification_preferences_user_id',
        'notification_preferences',
        ['user_id']
    )
    
    # Create unique constraint for notifications
    op.create_unique_constraint(
        'uq_notification_user_title_time',
        'notifications',
        ['user_id', 'title', 'created_at']
    )

def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_notifications_user_id')
    op.drop_index('ix_notifications_category')
    op.drop_index('ix_notifications_created_at')
    op.drop_index('ix_notifications_is_read')
    op.drop_index('ix_notification_preferences_user_id')
    
    # Drop unique constraints
    op.drop_constraint('uq_notification_user_title_time', 'notifications', type_='unique')
    op.drop_constraint('uq_notification_preferences_user_id', 'notification_preferences', type_='unique')
    
    # Drop tables
    op.drop_table('notification_preferences')
    op.drop_table('notifications')
    
    # Drop enum types
    op.execute('DROP TYPE notification_category')
    op.execute('DROP TYPE notification_priority')
    op.execute('DROP TYPE notification_channel') 
