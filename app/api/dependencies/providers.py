from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.document_repository import DocumentRepository
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService
from app.services.document_service import DocumentService


async def get_document_repository(db: AsyncSession = Depends(get_db)) -> DocumentRepository:
    """
    Dependency provider for DocumentRepository.
    """
    return DocumentRepository(db)


def get_embedding_service() -> EmbeddingService:
    """
    Dependency provider for EmbeddingService (cached/singleton instance pattern).
    """
    if not hasattr(get_embedding_service, "_instance"):
        get_embedding_service._instance = EmbeddingService()  # type: ignore
    return get_embedding_service._instance  # type: ignore


def get_llm_service() -> LLMService:
    """
    Dependency provider for LLMService (cached/singleton instance pattern).
    """
    if not hasattr(get_llm_service, "_instance"):
        get_llm_service._instance = LLMService()  # type: ignore
    return get_llm_service._instance  # type: ignore


def get_retrieval_service(
    repo: DocumentRepository = Depends(get_document_repository),
    embedding_service: EmbeddingService = Depends(get_embedding_service)
) -> RetrievalService:
    """
    Dependency provider for RetrievalService.
    """
    return RetrievalService(repo, embedding_service)


def get_document_service(
    repo: DocumentRepository = Depends(get_document_repository),
    embedding_service: EmbeddingService = Depends(get_embedding_service)
) -> DocumentService:
    """
    Dependency provider for DocumentService.
    """
    return DocumentService(repo, embedding_service)
