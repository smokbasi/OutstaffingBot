from datetime import date, time
from decimal import Decimal

import pytest

from app.bot.handlers.job_request import _build_job_create_payload, _format_job_summary
from app.bot.keyboards.job_request import (
    categories_keyboard,
    confirm_keyboard,
    metro_lines_keyboard,
    shift_dates_keyboard,
)
from app.bot.states.job_request import EmployerOnboarding, JobRequestCreation
from app.bot.validators.job_request import (
    format_shift_date,
    parse_hourly_rate,
    parse_optional_int,
    parse_shift_time,
    parse_workers_needed,
    upcoming_shift_dates,
    validate_shift_times,
)
from app.db.models import RequiredGender


def test_job_request_creation_states_defined() -> None:
    expected = {
        "category",
        "title",
        "description",
        "metro",
        "hourly_rate",
        "workers_needed",
        "shift_dates",
        "shift_start_time",
        "shift_end_time",
        "optional_menu",
        "confirm",
    }
    state_names = {state.state.split(":", 1)[-1] for state in JobRequestCreation.__states__}
    assert expected.issubset(state_names)


def test_employer_onboarding_has_company_name_state() -> None:
    assert EmployerOnboarding.company_name.state == "EmployerOnboarding:company_name"


def test_parse_hourly_rate_rejects_excessive() -> None:
    assert parse_hourly_rate("100000000") is None
    assert parse_hourly_rate("99999999.99") == Decimal("99999999.99")


def test_parse_hourly_rate_accepts_comma_decimal() -> None:
    assert parse_hourly_rate("400,50") == Decimal("400.50")
    assert parse_hourly_rate("-1") is None
    assert parse_hourly_rate("abc") is None


def test_parse_workers_needed_range() -> None:
    assert parse_workers_needed("2") == 2
    assert parse_workers_needed("0") is None
    assert parse_workers_needed("101") is None


def test_parse_shift_time_formats() -> None:
    assert parse_shift_time("10:00") == time(10, 0)
    assert parse_shift_time("22.30") == time(22, 30)
    assert parse_shift_time("invalid") is None


def test_validate_shift_times() -> None:
    assert validate_shift_times(time(10, 0), time(18, 0)) is True
    assert validate_shift_times(time(18, 0), time(10, 0)) is False
    assert validate_shift_times(time(10, 0), time(10, 0)) is False


def test_upcoming_shift_dates_count() -> None:
    dates = upcoming_shift_dates(days=7, start=date(2026, 6, 1))
    assert len(dates) == 7
    assert dates[0] == date(2026, 6, 1)
    assert format_shift_date(dates[0]) == "01.06.2026"


def test_parse_optional_int_bounds() -> None:
    assert parse_optional_int("25", min_value=16, max_value=70) == 25
    assert parse_optional_int("15", min_value=16, max_value=70) is None


def test_format_job_summary_includes_core_fields() -> None:
    text = _format_job_summary(
        {
            "category_name": "Официант",
            "title": "Смена в ресторане",
            "description": "Обслуживание зала",
            "metro_name": "Невский проспект (Кировско-Выборгская)",
            "hourly_rate": "450",
            "workers_needed": 3,
            "shift_slots": [
                {
                    "shift_date": "2026-06-25",
                    "start_time": "10:00",
                    "end_time": "22:00",
                }
            ],
            "post_to_groups": True,
        }
    )
    assert "Официант" in text
    assert "450" in text
    assert "25.06.2026" in text
    assert "В группы: да" in text


def test_build_job_create_payload_from_fsm_data() -> None:
    payload = _build_job_create_payload(
        {
            "category_id": 1,
            "title": "Официант",
            "description": "Зал",
            "metro_station_id": 5,
            "hourly_rate": "400",
            "workers_needed": 2,
            "required_gender": RequiredGender.any,
            "post_to_groups": False,
            "shift_slots": [
                {
                    "shift_date": "2026-06-25",
                    "start_time": "10:00",
                    "end_time": "22:00",
                }
            ],
        }
    )
    assert payload.title == "Официант"
    assert payload.hourly_rate == Decimal("400")
    assert len(payload.shift_slots) == 1
    assert payload.shift_slots[0].start_time == time(10, 0)


def test_build_job_create_payload_includes_lunch() -> None:
    payload = _build_job_create_payload(
        {
            "category_id": 1,
            "title": "Официант",
            "description": "Зал",
            "metro_station_id": 5,
            "hourly_rate": "400",
            "workers_needed": 2,
            "includes_lunch": True,
            "post_to_groups": False,
            "shift_slots": [
                {
                    "shift_date": "2026-06-25",
                    "start_time": "10:00",
                    "end_time": "22:00",
                }
            ],
        }
    )
    assert payload.includes_lunch is True


def test_format_job_summary_shows_lunch_when_included() -> None:
    text = _format_job_summary(
        {
            "category_name": "Официант",
            "title": "Смена",
            "description": "Зал",
            "metro_name": "Автово",
            "hourly_rate": "400",
            "workers_needed": 2,
            "shift_slots": [],
            "includes_lunch": True,
        }
    )
    assert "Обед: включён" in text


def test_format_job_summary_hides_lunch_when_not_included() -> None:
    text = _format_job_summary(
        {
            "category_name": "Официант",
            "title": "Смена",
            "description": "Зал",
            "metro_name": "Автово",
            "hourly_rate": "400",
            "workers_needed": 2,
            "shift_slots": [],
            "includes_lunch": False,
        }
    )
    assert "Обед" not in text


def test_job_keyboard_callback_data_within_limit() -> None:
    keyboards = [
        categories_keyboard([(1, "Официант"), (2, "Повар")]),
        metro_lines_keyboard(),
        shift_dates_keyboard(upcoming_shift_dates(days=3), {"2026-06-01"}),
        confirm_keyboard(),
    ]
    for keyboard in keyboards:
        for row in keyboard.inline_keyboard:
            for button in row:
                assert len(button.callback_data.encode("utf-8")) <= 64


@pytest.mark.parametrize(
    "start,end,valid",
    [
        ("09:00", "18:00", True),
        ("18:00", "09:00", False),
    ],
)
def test_shift_time_validation_param(start: str, end: str, valid: bool) -> None:
    parsed_start = parse_shift_time(start)
    parsed_end = parse_shift_time(end)
    assert parsed_start is not None
    assert parsed_end is not None
    assert validate_shift_times(parsed_start, parsed_end) is valid
