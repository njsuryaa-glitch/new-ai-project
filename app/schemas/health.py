from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., example="healthy")
    database: str = Field(..., example="connected")
    llm: str = Field(..., example="available")
