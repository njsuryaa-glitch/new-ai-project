"""gemini embeddings

Revision ID: 002_gemini_embeddings
Revises: 001_initial
Create Date: 2026-06-09 02:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '002_gemini_embeddings'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Drop index
    op.execute("DROP INDEX IF EXISTS document_chunks_embedding_idx;")
    # 2. Truncate document_chunks because old 1536 vectors cannot match the new 768 schema constraint
    op.execute("TRUNCATE TABLE document_chunks CASCADE;")
    # 3. Alter column
    op.alter_column('document_chunks', 'embedding', type_=Vector(768))
    # 4. Recreate index
    op.execute(
        "CREATE INDEX document_chunks_embedding_idx ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS document_chunks_embedding_idx;")
    op.execute("TRUNCATE TABLE document_chunks CASCADE;")
    op.alter_column('document_chunks', 'embedding', type_=Vector(1536))
    op.execute(
        "CREATE INDEX document_chunks_embedding_idx ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);"
    )
