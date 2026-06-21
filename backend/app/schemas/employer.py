from uuid import UUID

from pydantic import BaseModel, Field


class EmployerProfileRead(BaseModel):
    id: UUID
    company_name: str
    contact_phone: str | None = None
    contact_person: str | None = None
    verified: bool

    model_config = {"from_attributes": True}


class EmployerProfileUpdate(BaseModel):
    company_name: str = Field(min_length=1, max_length=200)
    contact_phone: str | None = Field(default=None, max_length=20)
    contact_person: str | None = Field(default=None, max_length=200)
