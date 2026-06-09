from app.repositories.document_repository import DocumentRepository
from app.services.embedding_service import EmbeddingService
from app.core.logging import get_logger

logger = get_logger(__name__)


class RetrievalService:
    def __init__(
        self,
        document_repository: DocumentRepository,
        embedding_service: EmbeddingService
    ) -> None:
        self.repo = document_repository
        self.embedding_service = embedding_service

    async def retrieve_relevant_chunks(self, question: str, limit: int = 5) -> list[dict]:
        """
        Embeds the question, searches for most similar chunks, and returns them formatted.
        """
        logger.info(f"Retrieving chunks for question: '{question}'")
        
        # 1. Generate embedding for the question
        query_embedding = await self.embedding_service.get_embedding(question)
        
        # 2. Search database for closest vectors
        chunks = await self.repo.search_similar_chunks(query_embedding, limit=limit)
        
        # 3. Format response to match required schema
        sources = []
        for chunk in chunks:
            sources.append({
                "document": chunk.document.filename if chunk.document else "Unknown",
                "chunk": chunk.chunk_text
            })
            
        return sources
