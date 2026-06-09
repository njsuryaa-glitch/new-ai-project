from typing import Optional, Sequence
from uuid import UUID
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Document, DocumentChunk


class DocumentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def save_document(self, document: Document) -> Document:
        """
        Saves a Document record to the database.
        """
        self.db.add(document)
        await self.db.flush()
        return document

    async def get_document_by_id(self, document_id: UUID) -> Optional[Document]:
        """
        Retrieves a Document by its UUID.
        """
        stmt = select(Document).where(Document.id == document_id)
        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def list_documents(self) -> Sequence[Document]:
        """
        Lists all uploaded documents.
        """
        stmt = select(Document).order_by(Document.created_at.desc())
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def delete_document(self, document_id: UUID) -> bool:
        """
        Deletes a Document by its UUID. Cascades to chunks automatically via DB constraint.
        """
        stmt = delete(Document).where(Document.id == document_id)
        result = await self.db.execute(stmt)
        await self.commit()
        return (result.rowcount or 0) > 0

    async def save_chunks(self, chunks: list[DocumentChunk]) -> None:
        """
        Saves a batch of DocumentChunk records.
        """
        self.db.add_all(chunks)
        await self.db.flush()

    async def search_similar_chunks(
        self, query_embedding: list[float], limit: int = 5
    ) -> Sequence[DocumentChunk]:
        """
        Performs similarity search on document_chunks using pgvector cosine distance.
        Eagerly loads the associated Document.
        """
        # cosine_distance maps directly to '<=>' operator in pgvector
        stmt = (
            select(DocumentChunk)
            .options(selectinload(DocumentChunk.document))
            .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def commit(self) -> None:
        """
        Commits the current database transaction.
        Keeping commit() inside the repository maintains the abstraction boundary
        and makes mocking straightforward.
        """
        await self.db.commit()
