from datetime import date, datetime, time, timezone
from uuid import uuid4

import pytest

from app.db.models import ApplicationStatus
from app.schemas.worker import WorkerProfileUpdate
from app.services.application_service import (
    _application_read_load_options,
    _application_to_employer_read,
    _application_to_read,
)


class _User:
    def __init__(self, *, username: str | None = None, telegram_id: int = 123456) -> None:
        self.username = username
        self.telegram_id = telegram_id


class _Employer:
    def __init__(self) -> None:
        self.company_name = "ООО Тест"
        self.contact_phone = "+79990001122"
        self.user = _User(username="employer_tg", telegram_id=111)


class _Worker:
    def __init__(self) -> None:
        self.id = uuid4()
        self.first_name = "Пётр"
        self.last_name = "Иванов"
        self.age = 25
        self.phone = "+79998887766"
        self.experiences: list = []
        self.user = _User(username="worker_tg", telegram_id=222)


class _Job:
    def __init__(self) -> None:
        self.id = uuid4()
        self.title = "Официант"
        self.hourly_rate = "400.00"
        self.category = type("Cat", (), {"name_ru": "Официант"})()
        self.metro_station = type("Metro", (), {"name": "Автово"})()
        self.employer = _Employer()


class _Slot:
    def __init__(self) -> None:
        self.shift_date = date(2026, 6, 25)
        self.start_time = time(10, 0)
        self.end_time = time(22, 0)


class _Application:
    def __init__(self, *, status: ApplicationStatus) -> None:
        self.id = uuid4()
        self.job_request_id = uuid4()
        self.shift_slot_id = uuid4()
        self.worker_id = uuid4()
        self.status = status
        self.applied_at = datetime.now(timezone.utc)
        self.cancelled_at = None
        self.shift_slot = _Slot()
        self.job_request = _Job()
        self.worker = _Worker()


def test_employer_sees_worker_contacts_only_on_accepted() -> None:
    pending = _application_to_employer_read(_Application(status=ApplicationStatus.pending))
    assert pending.worker_phone is None
    assert pending.worker_telegram_username is None
    assert pending.worker_telegram_id is None

    accepted = _application_to_employer_read(_Application(status=ApplicationStatus.accepted))
    assert accepted.worker_phone == "+79998887766"
    assert accepted.worker_telegram_username == "worker_tg"
    assert accepted.worker_telegram_id == 222


def test_application_read_load_options_includes_employer_chain() -> None:
    options = _application_read_load_options()
    assert len(options) == 4
    path_strings = [str(opt.path) for opt in options]
    assert any("employer" in p and "user" in p for p in path_strings)
    pending = _application_to_read(_Application(status=ApplicationStatus.pending))
    assert pending.employer_contact_phone is None
    assert pending.employer_company_name == ""
    assert pending.employer_telegram_username is None
    assert pending.employer_telegram_id is None

    accepted = _application_to_read(_Application(status=ApplicationStatus.accepted))
    assert accepted.employer_contact_phone == "+79990001122"
    assert accepted.employer_company_name == "ООО Тест"
    assert accepted.employer_telegram_username == "employer_tg"
    assert accepted.employer_telegram_id == 111


def test_worker_profile_update_accepts_phone() -> None:
    profile = WorkerProfileUpdate(
        first_name="Иван",
        last_name="Петров",
        age=25,
        phone="+79991234567",
    )
    assert profile.phone == "+79991234567"


def test_worker_profile_update_rejects_invalid_phone() -> None:
    with pytest.raises(ValueError):
        WorkerProfileUpdate(
            first_name="Иван",
            last_name="Петров",
            age=25,
            phone="not-a-phone",
        )


def test_worker_profile_update_allows_empty_phone() -> None:
    profile = WorkerProfileUpdate(
        first_name="Иван",
        last_name="Петров",
        age=25,
        phone="   ",
    )
    assert profile.phone is None
