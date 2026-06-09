from pydantic import BaseModel, Field


class ErrorDetails(BaseModel):
    code: str = Field(..., description="Unique machine-readable error code")
    message: str = Field(..., description="Human-readable error description")


class ErrorResponse(BaseModel):
    success: bool = Field(default=False)
    error: ErrorDetails
