from app.db.models import ApplicationStatus
from app.schemas.application import APPLICATION_STATUS_LABELS, format_application_status


def test_application_status_labels_russian() -> None:
    assert APPLICATION_STATUS_LABELS[ApplicationStatus.pending] == "На рассмотрении"
    assert APPLICATION_STATUS_LABELS[ApplicationStatus.cancelled_by_worker] == "Отменён вами"


def test_format_application_status_fallback() -> None:
    assert format_application_status(ApplicationStatus.accepted) == "Принят"
