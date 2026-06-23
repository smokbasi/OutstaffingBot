"""Tests for ApplicationComplaint model and enums (Phase 9.9.1)."""

from sqlalchemy import Index

from app.db.models import (
    ApplicationComplaint,
    ComplaintReporterRole,
    ComplaintStatus,
    ComplaintViolationType,
)


def test_complaint_enums_values() -> None:
    assert [e.value for e in ComplaintViolationType] == [
        "late",
        "no_show",
        "no_payment",
        "no_work",
    ]
    assert [e.value for e in ComplaintReporterRole] == ["worker", "employer"]
    assert [e.value for e in ComplaintStatus] == [
        "open",
        "under_review",
        "resolved",
        "dismissed",
    ]


def test_application_complaint_table_metadata() -> None:
    table = ApplicationComplaint.__table__
    assert table.name == "application_complaints"

    column_names = {col.name for col in table.columns}
    assert column_names == {
        "id",
        "application_id",
        "job_request_id",
        "shift_slot_id",
        "reporter_user_id",
        "reporter_role",
        "target_user_id",
        "violation_type",
        "description",
        "status",
        "admin_notes",
        "resolved_at",
        "resolved_by_telegram_id",
        "created_at",
    }

    fk_targets = {fk.target_fullname for fk in table.foreign_keys}
    assert fk_targets == {
        "applications.id",
        "job_requests.id",
        "shift_slots.id",
        "users.id",
    }
    assert sum(1 for fk in table.foreign_keys if fk.target_fullname == "users.id") == 2


def test_application_complaint_open_duplicate_partial_index() -> None:
    indexes = {idx.name: idx for idx in ApplicationComplaint.__table__.indexes}
    partial = indexes["uq_application_complaints_open_dup"]
    assert isinstance(partial, Index)
    assert partial.unique is True
    assert [col.name for col in partial.columns] == [
        "application_id",
        "reporter_user_id",
        "violation_type",
    ]
    assert partial.dialect_options["postgresql"]["where"] is not None
