from uuid import uuid4

import pytest

from app.db.models import VerificationStatus
from app.services.admin_service import verify_employer, verify_worker


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


class FakeWorker:
    def __init__(self):
        self.id = uuid4()
        self.first_name = "Иван"
        self.last_name = "Иванов"
        self.verification_status = VerificationStatus.pending


class FakeWorkerSession:
    def __init__(self, worker):
        self.worker = worker
        self.audit_calls = []

    async def scalar(self, stmt):
        return self.worker

    async def flush(self):
        pass


@pytest.mark.asyncio
async def test_verify_worker_approve(monkeypatch):
    worker = FakeWorker()
    session = FakeWorkerSession(worker)

    async def fake_log_audit(session, **kwargs):
        session.audit_calls.append(kwargs)

    monkeypatch.setattr("app.services.admin_service.audit_service.log_audit", fake_log_audit)

    actor_id = uuid4()
    result = await verify_worker(session, worker.id, actor_id=actor_id, approve=True)
    assert result is worker
    assert worker.verification_status == VerificationStatus.verified
    assert len(session.audit_calls) == 1
    assert session.audit_calls[0]["action"] == "worker.verify"


@pytest.mark.asyncio
async def test_verify_worker_reject(monkeypatch):
    worker = FakeWorker()
    session = FakeWorkerSession(worker)

    async def fake_log_audit(session, **kwargs):
        session.audit_calls.append(kwargs)

    monkeypatch.setattr("app.services.admin_service.audit_service.log_audit", fake_log_audit)

    result = await verify_worker(session, worker.id, actor_id=uuid4(), approve=False)
    assert result is worker
    assert worker.verification_status == VerificationStatus.rejected
    assert session.audit_calls[0]["action"] == "worker.reject"


class FakeBannedWorker:
    def __init__(self):
        self.id = uuid4()
        self.is_banned = False


class FakeBanSession:
    def __init__(self, entity):
        self.entity = entity
        self.audit_calls = []

    async def scalar(self, stmt):
        return self.entity

    async def flush(self):
        pass


@pytest.mark.asyncio
async def test_ban_worker_sets_flag_and_logs_audit(monkeypatch):
    from app.services.admin_service import ban_worker

    worker = FakeBannedWorker()
    session = FakeBanSession(worker)

    async def fake_log_audit(session, **kwargs):
        session.audit_calls.append(kwargs)

    monkeypatch.setattr("app.services.admin_service.audit_service.log_audit", fake_log_audit)

    result = await ban_worker(session, worker.id, actor_id=uuid4(), ban=True)
    assert result is worker
    assert worker.is_banned is True
    assert session.audit_calls[0]["action"] == "worker.ban"


@pytest.mark.asyncio
async def test_unban_worker_clears_flag(monkeypatch):
    from app.services.admin_service import ban_worker

    worker = FakeBannedWorker()
    worker.is_banned = True
    session = FakeBanSession(worker)

    async def fake_log_audit(session, **kwargs):
        session.audit_calls.append(kwargs)

    monkeypatch.setattr("app.services.admin_service.audit_service.log_audit", fake_log_audit)

    result = await ban_worker(session, worker.id, actor_id=uuid4(), ban=False)
    assert result is worker
    assert worker.is_banned is False
    assert session.audit_calls[0]["action"] == "worker.unban"


@pytest.mark.asyncio
async def test_ban_employer_sets_flag_and_logs_audit(monkeypatch):
    from app.services.admin_service import ban_employer

    employer = FakeEmployer()
    employer.is_banned = False
    session = FakeBanSession(employer)

    async def fake_log_audit(session, **kwargs):
        session.audit_calls.append(kwargs)

    monkeypatch.setattr("app.services.admin_service.audit_service.log_audit", fake_log_audit)

    result = await ban_employer(session, employer.id, actor_id=uuid4(), ban=True)
    assert result is employer
    assert employer.is_banned is True
    assert session.audit_calls[0]["action"] == "employer.ban"
