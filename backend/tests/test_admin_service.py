from uuid import uuid4

import pytest

from app.db.models import VerificationStatus
from app.services.admin_service import verify_employer


class FakeEmployer:
    def __init__(self):
        self.id = uuid4()
        self.company_name = "Test Co"
        self.verification_status = VerificationStatus.pending


class FakeSession:
    def __init__(self, employer):
        self.employer = employer
        self.audit_calls = []

    async def scalar(self, stmt):
        return self.employer

    async def flush(self):
        pass


@pytest.mark.asyncio
async def test_verify_employer_approve(monkeypatch):
    employer = FakeEmployer()
    session = FakeSession(employer)

    async def fake_log_audit(session, **kwargs):
        session.audit_calls.append(kwargs)

    monkeypatch.setattr("app.services.admin_service.audit_service.log_audit", fake_log_audit)

    actor_id = uuid4()
    result = await verify_employer(session, employer.id, actor_id=actor_id, approve=True)
    assert result is employer
    assert employer.verification_status == VerificationStatus.verified
    assert len(session.audit_calls) == 1
    assert session.audit_calls[0]["action"] == "employer.verify"


@pytest.mark.asyncio
async def test_verify_employer_reject(monkeypatch):
    employer = FakeEmployer()
    session = FakeSession(employer)

    async def fake_log_audit(session, **kwargs):
        session.audit_calls.append(kwargs)

    monkeypatch.setattr("app.services.admin_service.audit_service.log_audit", fake_log_audit)

    result = await verify_employer(session, employer.id, actor_id=uuid4(), approve=False)
    assert result is employer
    assert employer.verification_status == VerificationStatus.rejected
