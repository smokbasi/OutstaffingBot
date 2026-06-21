from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation


def upcoming_shift_dates(*, days: int = 14, start: date | None = None) -> list[date]:
    base = start or date.today()
    return [base + timedelta(days=offset) for offset in range(days)]


def format_shift_date(value: date) -> str:
    return value.strftime("%d.%m.%Y")


def parse_hourly_rate(text: str) -> Decimal | None:
    cleaned = text.strip().replace(",", ".")
    try:
        rate = Decimal(cleaned)
    except (InvalidOperation, ValueError):
        return None
    if rate < 0:
        return None
    return rate


def parse_workers_needed(text: str) -> int | None:
    try:
        count = int(text.strip())
    except ValueError:
        return None
    if count < 1 or count > 100:
        return None
    return count


def parse_shift_time(text: str) -> time | None:
    cleaned = text.strip()
    for fmt in ("%H:%M", "%H.%M"):
        try:
            parsed = datetime.strptime(cleaned, fmt).time()
        except ValueError:
            continue
        return parsed
    return None


def validate_shift_times(start: time, end: time) -> bool:
    return start < end


def parse_optional_int(text: str, *, min_value: int, max_value: int) -> int | None:
    try:
        value = int(text.strip())
    except ValueError:
        return None
    if value < min_value or value > max_value:
        return None
    return value
