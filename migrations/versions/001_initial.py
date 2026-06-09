"""initial

Revision ID: 001_initial
Revises: 
Create Date: 2026-06-08 22:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ensure vector extension is created
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    
    # Create table documents
    op.create_table(
        'documents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create table document_chunks
    op.create_table(
        'document_chunks',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('embedding', Vector(dim=1536), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indices
    op.create_index(
        'ix_document_chunks_document_id',
        'document_chunks',
        ['document_id'],
        unique=False
    )
    
    # Create ivfflat vector index
    op.execute(
        "CREATE INDEX document_chunks_embedding_idx ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS document_chunks_embedding_idx;")
    op.drop_index('ix_document_chunks_document_id', table_name='document_chunks')
    op.drop_table('document_chunks')
    op.drop_table('documents')
    op.execute("DROP EXTENSION IF EXISTS vector;")
