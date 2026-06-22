from uuid import UUID

from pydantic import BaseModel, Field, computed_field

from app.db.models import VerificationStatus


class EmployerProfileRead(BaseModel):
    id: UUID
    company_name: str
    contact_phone: str | None = None
    contact_person: str | None = None
    verification_status: VerificationStatus

    model_config = {"from_attributes": True}

    @computed_field  # type: ignore[prop-decorator]
    @property
    def verified(self) -> bool:
        return self.verification_status == VerificationStatus.verified


class EmployerProfileUpdate(BaseModel):
    company_name: str = Field(min_length=1, max_length=200)
    contact_phone: str | None = Field(default=None, max_length=20)
    contact_person: str | None = Field(default=None, max_length=200)
