from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    created_at: datetime

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    document_id: UUID
    chunks_created: int


class DeleteResponse(BaseModel):
    success: bool
    message: str
