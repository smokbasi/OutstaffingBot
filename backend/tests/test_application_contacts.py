from datetime import date, datetime, time, timezone
from uuid import uuid4

from app.db.models import ApplicationStatus
from app.services.application_service import _application_to_read


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
        self.first_name = "Пётр"
        self.last_name = "Иванов"
        self.phone = "+79998887766"
        self.user = _User(username="worker_tg", telegram_id=222)


class _Job:
    def __init__(self) -> None:
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
    def __init__(self, *, status: ApplicationStatus, include_worker: bool = False) -> None:
        self.id = uuid4()
        self.job_request_id = uuid4()
        self.shift_slot_id = uuid4()
        self.status = status
        self.applied_at = datetime.now(timezone.utc)
        self.cancelled_at = None
        self.shift_slot = _Slot()
        self.job_request = _Job()
        self.worker = _Worker() if include_worker else None


def test_application_read_hides_contacts_until_accepted() -> None:
    pending = _application_to_read(_Application(status=ApplicationStatus.pending))
    assert pending.employer_contact_phone is None
    assert pending.worker_phone is None

    accepted_worker_view = _application_to_read(_Application(status=ApplicationStatus.accepted))
    assert accepted_worker_view.employer_contact_phone == "+79990001122"
    assert accepted_worker_view.employer_company_name == "ООО Тест"
    assert accepted_worker_view.employer_telegram_username == "employer_tg"

    accepted_employer_view = _application_to_read(
        _Application(status=ApplicationStatus.accepted, include_worker=True),
        include_worker=True,
    )
    assert accepted_employer_view.worker_phone == "+79998887766"
    assert accepted_employer_view.worker_telegram_username == "worker_tg"
