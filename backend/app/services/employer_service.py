from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Employer, User
from app.schemas.employer import EmployerProfileRead, EmployerProfileUpdate


async def get_employer_by_user_id(session: AsyncSession, user_id: UUID) -> Employer | None:
    return await session.scalar(select(Employer).where(Employer.user_id == user_id))


def _employer_to_profile(employer: Employer) -> EmployerProfileRead:
    return EmployerProfileRead(
        id=employer.id,
        company_name=employer.company_name,
        contact_phone=employer.contact_phone,
        contact_person=employer.contact_person,
        verified=employer.verified,
    )


async def get_employer_profile(session: AsyncSession, user: User) -> EmployerProfileRead | None:
    employer = await get_employer_by_user_id(session, user.id)
    if employer is None:
        return None
    return _employer_to_profile(employer)


async def upsert_employer_profile(
    session: AsyncSession,
    user: User,
    data: EmployerProfileUpdate,
) -> EmployerProfileRead:
    employer = await get_employer_by_user_id(session, user.id)
    if employer is None:
        employer = Employer(
            user_id=user.id,
            company_name=data.company_name,
            contact_phone=data.contact_phone,
            contact_person=data.contact_person,
        )
        session.add(employer)
    else:
        employer.company_name = data.company_name
        employer.contact_phone = data.contact_phone
        employer.contact_person = data.contact_person

    await session.flush()
    employer = await get_employer_by_user_id(session, user.id)
    assert employer is not None
    return _employer_to_profile(employer)
