from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Employer, User
from app.schemas.employer import EmployerProfileRead, EmployerProfileUpdate
from app.services import audit_log_service, content_moderation_service, user_service

EMPLOYER_NOT_VERIFIED_MESSAGE = (
    "Профиль работодателя не верифицирован. Опубликуйте заявку после проверки администратором."
)


class EmployerNotVerifiedError(Exception):
    def __init__(self, message: str = EMPLOYER_NOT_VERIFIED_MESSAGE) -> None:
        self.message = message
        super().__init__(message)


def ensure_verified(employer: Employer) -> None:
    if not employer.verified:
        raise EmployerNotVerifiedError()


@dataclass(frozen=True)
class VerifyActionResult:
    employer: Employer | None
    user: User | None
    changed: bool
    message: str


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
    content_moderation_service.moderate_company_name(data.company_name)

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


async def verify_employer_by_telegram_id(
    session: AsyncSession,
    telegram_id: int,
    *,
    actor_telegram_id: int,
) -> VerifyActionResult:
    user = await user_service.get_user_by_telegram_id(session, telegram_id)
    if user is None:
        return VerifyActionResult(
            employer=None,
            user=None,
            changed=False,
            message="Пользователь не найден.",
        )

    employer = await get_employer_by_user_id(session, user.id)
    if employer is None:
        return VerifyActionResult(
            employer=None,
            user=user,
            changed=False,
            message="Профиль работодателя не найден.",
        )

    if employer.verified:
        return VerifyActionResult(
            employer=employer,
            user=user,
            changed=False,
            message="Работодатель уже верифицирован.",
        )

    employer.verified = True
    await session.flush()
    await audit_log_service.record_audit(
        session,
        action="employer.verify",
        actor_telegram_id=actor_telegram_id,
        target_user=user,
        details={"company_name": employer.company_name, "previous_verified": False},
    )
    return VerifyActionResult(
        employer=employer,
        user=user,
        changed=True,
        message="Работодатель верифицирован.",
    )
