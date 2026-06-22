from pydantic import BaseModel, Field


class ContentRejectedResponse(BaseModel):
    detail: str = Field(description="User-facing message in Russian")
    code: str = Field(default="content_rejected")
    field: str | None = None
