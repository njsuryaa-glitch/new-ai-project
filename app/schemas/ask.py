from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, description="The query to ask the knowledge base")


class SourceSchema(BaseModel):
    document: str = Field(..., description="Name of the source document")
    chunk: str = Field(..., description="Text segment from the document")


class AskResponse(BaseModel):
    answer: str = Field(..., description="Generated contextual answer")
    sources: list[SourceSchema] = Field(..., description="Relevant sources retrieved to answer the question")
