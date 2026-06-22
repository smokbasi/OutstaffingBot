from uuid import uuid4

from app.core.mini_app_urls import parse_job_start_payload


def test_parse_job_start_payload_valid_uuid() -> None:
    job_id = uuid4()
    assert parse_job_start_payload(f"job_{job_id}") == job_id


def test_parse_job_start_payload_rejects_invalid() -> None:
    assert parse_job_start_payload("job_bad") is None
    assert parse_job_start_payload("vacancy_123") is None
