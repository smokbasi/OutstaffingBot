from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.models import ReviewerRole


class ReviewCreate(BaseModel):
    application_id: UUID
    reviewer_role: ReviewerRole
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


class ReviewRead(BaseModel):
    id: UUID
    application_id: UUID
    reviewer_user_id: UUID
    reviewed_user_id: UUID
    reviewer_role: ReviewerRole
    rating: int
    comment: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
