"""create consent tables

Revision ID: create_consent_tables
Revises: previous_revision
Create Date: 2024-03-14 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'create_consent_tables'
down_revision: Union[str, None] = 'previous_revision'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    """Create document versions and user consents tables."""
    # Create document_versions table
    op.create_table(
        'document_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('type', sa.Enum('terms', 'privacy', 'kyc_disclosure', 'marketing', 'cookies', name='documenttype'), nullable=False, index=True),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('hash', sa.String(64), nullable=False, index=True),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), index=True),
        sa.UniqueConstraint('type', 'version', name='uq_document_versions_type_version')
    )
    
    # Create user_consents table
    op.create_table(
        'user_consents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP'), index=True),
        sa.Column('ip_address', sa.String(45), nullable=False),
        sa.Column('user_agent', sa.String(500), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['document_versions.id'], ondelete='CASCADE', name='fk_user_consents_document_id')
    )
    
    # Add indexes
    op.create_index(
        'ix_user_consents_user_id_document_id',
        'user_consents',
        ['user_id', 'document_id'],
        unique=True
    )
    
    # Add comments
    op.execute("""
        COMMENT ON TABLE document_versions IS 'Versioned legal documents requiring user consent';
        COMMENT ON COLUMN document_versions.id IS 'Unique identifier for the document version';
        COMMENT ON COLUMN document_versions.type IS 'Type of document (terms, privacy, etc.)';
        COMMENT ON COLUMN document_versions.version IS 'Version string (e.g., v1.1)';
        COMMENT ON COLUMN document_versions.hash IS 'SHA-256 hash of document content';
        COMMENT ON COLUMN document_versions.content IS 'Document content';
        COMMENT ON COLUMN document_versions.created_at IS 'When the version was created';
        
        COMMENT ON TABLE user_consents IS 'User consent records for document versions';
        COMMENT ON COLUMN user_consents.id IS 'Unique identifier for the consent record';
        COMMENT ON COLUMN user_consents.user_id IS 'ID of the user who gave consent';
        COMMENT ON COLUMN user_consents.document_id IS 'ID of the document version';
        COMMENT ON COLUMN user_consents.accepted_at IS 'When the consent was given';
        COMMENT ON COLUMN user_consents.ip_address IS 'IP address of the user';
        COMMENT ON COLUMN user_consents.user_agent IS 'User agent of the browser';
    """)

def downgrade() -> None:
    """Drop consent tables."""
    op.drop_table('user_consents')
    op.drop_table('document_versions')
    op.execute('DROP TYPE documenttype') 
