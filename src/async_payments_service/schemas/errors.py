from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    location: str
    message: str
    type: str


class ErrorResponse(BaseModel):
    detail: str
    errors: list[ErrorDetail] = Field(default_factory=list)
