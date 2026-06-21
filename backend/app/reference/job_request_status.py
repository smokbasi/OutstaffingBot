"""Russian display labels for job request statuses."""

from app.db.models import JobRequestStatus

JOB_REQUEST_STATUS_LABELS: dict[JobRequestStatus, str] = {
    JobRequestStatus.draft: "Черновик",
    JobRequestStatus.active: "Активна",
    JobRequestStatus.filled: "Закрыта",
    JobRequestStatus.cancelled: "Отменена",
    JobRequestStatus.expired: "Истекла",
}


def job_request_status_label(status: JobRequestStatus) -> str:
    return JOB_REQUEST_STATUS_LABELS.get(status, status.value)
