from app.db.models import JobRequestStatus
from app.reference.job_request_status import JOB_REQUEST_STATUS_LABELS, job_request_status_label


def test_job_request_status_labels_are_russian() -> None:
    assert JOB_REQUEST_STATUS_LABELS[JobRequestStatus.draft] == "Черновик"
    assert JOB_REQUEST_STATUS_LABELS[JobRequestStatus.active] == "Активна"
    assert JOB_REQUEST_STATUS_LABELS[JobRequestStatus.filled] == "Закрыта"
    assert JOB_REQUEST_STATUS_LABELS[JobRequestStatus.cancelled] == "Отменена"
    assert JOB_REQUEST_STATUS_LABELS[JobRequestStatus.expired] == "Истекла"


def test_job_request_status_label_helper() -> None:
    assert job_request_status_label(JobRequestStatus.active) == "Активна"
