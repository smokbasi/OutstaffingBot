from datetime import date, time
from decimal import Decimal
from uuid import uuid4

from app.db.models import JobCategory, JobRequest, JobRequestStatus, MetroStation, ShiftSlot
from app.services.notification_service import format_new_vacancy_message


def test_format_new_vacancy_message_russian() -> None:
    job = JobRequest(
        id=uuid4(),
        employer_id=uuid4(),
        category_id=2,
        title="Официант на банкет",
        description="Обслуживание",
        metro_station_id=1,
        hourly_rate=Decimal("450.00"),
        workers_needed=2,
        status=JobRequestStatus.active,
    )
    job.category = JobCategory(id=2, slug="waiter", name_ru="Официант")
    job.metro_station = MetroStation(id=1, name="Автово", line_name="Красная")
    job.shift_slots = [
        ShiftSlot(
            id=uuid4(),
            job_request_id=job.id,
            shift_date=date(2026, 7, 10),
            start_time=time(12, 0),
            end_time=time(20, 0),
            slots_total=2,
            slots_filled=0,
        )
    ]

    text = format_new_vacancy_message(job)

    assert "Новая вакансия" in text
    assert "Официант на банкет" in text
    assert "Официант" in text
    assert "Автово" in text
    assert "450.00" in text
    assert "10.07.2026" in text
