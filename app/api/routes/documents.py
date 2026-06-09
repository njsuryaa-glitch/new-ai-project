from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from app.api.dependencies.providers import get_document_service, get_document_repository
from app.core.security import verify_api_key
from app.core.config import settings
from app.services.document_service import DocumentService
from app.repositories.document_repository import DocumentRepository
from app.schemas.document import DocumentResponse, UploadResponse, DeleteResponse
from app.core.logging import get_logger

logger = get_logger(__name__)

# Protect all document routes with API Key authentication
router = APIRouter(
    prefix="/documents",
    tags=["documents"],
    dependencies=[Depends(verify_api_key)]
)


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Document"
)
async def upload_document(
    file: UploadFile = File(...),
    doc_service: DocumentService = Depends(get_document_service)
) -> UploadResponse:
    """
    Upload a document (PDF, TXT, or DOCX), extract text, partition into chunks,
    generate vector embeddings, and save both text and embeddings to PostgreSQL.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is missing."
        )

    # 1. Validate File Format/Extension
    ext = file.filename.split(".")[-1].lower()
    if ext not in ("pdf", "docx", "txt"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension: .{ext}. Only PDF, DOCX, and TXT are supported."
        )

    # 2. Validate File Size
    # Read the file contents into memory to calculate size and prepare for parsing
    content = await file.read()
    content_size = len(content)
    
    if content_size > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File is too large ({content_size / (1024*1024):.2f} MB). Maximum size is {settings.MAX_FILE_SIZE_MB} MB."
        )

    if content_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )

    # 3. Process Document
    logger.info(f"Uploading and processing file: {file.filename} ({content_size} bytes)")
    doc, chunks_count = await doc_service.process_document(file.filename, content)

    return UploadResponse(
        document_id=doc.id,
        chunks_created=chunks_count
    )


@router.get(
    "",
    response_model=list[DocumentResponse],
    status_code=status.HTTP_200_OK,
    summary="List Documents"
)
async def list_documents(
    repo: DocumentRepository = Depends(get_document_repository)
) -> list[DocumentResponse]:
    """
    Get a list of all documents stored in the system.
    """
    documents = await repo.list_documents()
    return [DocumentResponse.model_validate(doc) for doc in documents]


@router.get(
    "/{id}",
    response_model=DocumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Document Details"
)
async def get_document(
    id: UUID,
    repo: DocumentRepository = Depends(get_document_repository)
) -> DocumentResponse:
    """
    Get metadata for a specific document by its unique UUID.
    """
    doc = await repo.get_document_by_id(id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {id} not found."
        )
    return DocumentResponse.model_validate(doc)


@router.delete(
    "/{id}",
    response_model=DeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete Document"
)
async def delete_document(
    id: UUID,
    repo: DocumentRepository = Depends(get_document_repository)
) -> DeleteResponse:
    """
    Delete a document and all of its associated vector chunks.
    """
    logger.info(f"Request to delete document ID: {id}")
    success = await repo.delete_document(id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {id} not found."
        )
    return DeleteResponse(
        success=True,
        message=f"Document with ID {id} and all its chunks deleted successfully."
    )
