from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_current_employer, get_current_user
from app.db.models import JobRequestStatus, User, UserRole, Employer
from app.db.session import get_db_session
from app.main import app
from app.services import content_moderation_service, job_service
from app.schemas.job_request import JobRequestUpdate
from tests.helpers.init_data import build_test_init_data


def test_clean_text_passes() -> None:
    assert (
        content_moderation_service.check_text(
            "description",
            "Обслуживание зала в ресторане, опыт приветствуется",
        )
        is None
    )


def test_explicit_profanity_blocked() -> None:
    violation = content_moderation_service.check_text("description", "Это полный govno текст")
    assert violation is not None
    assert violation.field == "description"
    assert violation.matched_term in {"govno", "говно"}


def test_obfuscation_blocked() -> None:
    violation = content_moderation_service.check_text("description", "Тут g.o.v.n.o в описании")
    assert violation is not None
    assert violation.matched_term in {"govno", "говно"}


def test_translit_blocked() -> None:
    violation = content_moderation_service.check_text("description", "Only PIDOR allowed")
    assert violation is not None
    assert violation.matched_term in {"pidor", "пидор"}


def test_alcohol_terms_allowed() -> None:
    text = "Ищем бармена: коктейли, алкогольное меню, винная карта"
    assert content_moderation_service.check_text("description", text) is None


@pytest.mark.parametrize(
    "field",
    ["description", "title", "role_title", "address", "dress_code", "contact_info"],
)
def test_alcohol_terms_allowed_in_any_field(field: str) -> None:
    """Phase 9.5: alcohol whitelist is platform-wide, not category-specific."""
    text = "бармен, коктейли, алкогольное меню"
    assert content_moderation_service.check_text(field, text) is None


@pytest.mark.parametrize(
    "text",
    [
        "сомелье, винная карта",
        "бармен, коктейли, алкогольное меню",
        "lounge bar bartender whiskey craft beer",
        "винный бар, шампанское, mixologist",
    ],
)
def test_alcohol_phrases_pass_platform_wide(text: str) -> None:
    assert content_moderation_service.check_text("description", text) is None
    assert content_moderation_service.check_text("title", text) is None


@pytest.mark.parametrize(
    ("text", "expected_terms"),
    [
        ("escort services", {"escort services", "escort"}),
        ("эскорт услуги", {"эскорт услуги", "эскорт"}),
        ("vip escort", {"escort", "vip escort"}),
        ("проститутка на смене", {"проститутка", "проститут"}),
    ],
)
def test_escort_still_blocked_with_alcohol_whitelist(
    text: str,
    expected_terms: set[str],
) -> None:
    violation = content_moderation_service.check_text("description", text)
    assert violation is not None
    assert violation.matched_term in expected_terms


def test_alcohol_plus_profanity_still_blocked() -> None:
    violation = content_moderation_service.check_text(
        "description",
        "бармен, коктейли, алкогольное меню — без govno на смене",
    )
    assert violation is not None
    assert violation.matched_term in {"govno", "говно"}


def test_mask_alcohol_terms_strips_allow_phrases() -> None:
    normalized = content_moderation_service.normalize_for_matching(
        "бармен, коктейли, алкогольное меню"
    )
    masked = content_moderation_service._mask_alcohol_terms(normalized)
    assert masked == ""


def test_moderate_job_for_publish_raises_on_violation() -> None:
    with pytest.raises(content_moderation_service.ContentRejectedError) as exc_info:
        content_moderation_service.moderate_job_for_publish(
            title="Официант",
            description="Работа без blyat на смене",
        )
    assert exc_info.value.violation.field == "description"


def test_moderate_company_name_blocks_translit() -> None:
    with pytest.raises(content_moderation_service.ContentRejectedError):
        content_moderation_service.moderate_company_name("Super PIZDA LLC")


def test_normalize_for_matching_lowercases_and_collapses_separators() -> None:
    normalized = content_moderation_service.normalize_for_matching("G.O.V.N.O")
    assert normalized == "говно"


@pytest.mark.parametrize(
    ("text", "expected_term"),
    [
        ("зак[лад]ка в описании", "закладка"),
        ("SE[X services here", "sex"),
        ("п[и]дор в тексте", "пидор"),
        ("Тут g.o.v.n.o в описании", "говно"),
        ("зак{лад}ка", "закладка"),
    ],
)
def test_bracket_and_separator_obfuscation_blocked(text: str, expected_term: str) -> None:
    violation = content_moderation_service.check_text("description", text)
    assert violation is not None
    assert violation.matched_term == expected_term


@pytest.mark.parametrize(
    "text",
    [
        "Работа (удобный график) в центре",
        "Офис (стр. 2), метро рядом",
        "Вакансия (опыт приветствуется)",
        "Локация (корп. 3)",
        "Адрес (д. 5)",
        "(м. рядом)",
        "(лит. А)",
        "Обслуживание зала (удобный график), опыт приветствуется",
    ],
)
def test_legitimate_parentheses_in_description_and_address_pass(text: str) -> None:
    assert content_moderation_service.check_text("description", text) is None


def test_normalize_for_matching_deobfuscates_suspicious_tokens_only() -> None:
    assert content_moderation_service.normalize_for_matching("SE[X") == "sex"
    assert content_moderation_service.normalize_for_matching("зак[лад]ка") == "закладка"
    assert (
        content_moderation_service.normalize_for_matching("Работа (удобный график)")
        == "работа (удобный график)"
    )
    assert (
        content_moderation_service.normalize_for_matching("Офис (стр. 2)")
        == "офис (стр. 2)"
    )


def test_zakladka_bracket_obfuscation_regression() -> None:
    violation = content_moderation_service.check_text(
        "description",
        "Ищем курьера, зак[лад]ка в описании",
    )
    assert violation is not None
    assert violation.matched_term == "закладка"
    assert violation.field == "description"


@pytest.mark.parametrize(
    ("text", "expected_terms"),
    [
        ("GOVNO everywhere", {"govno", "говно"}),
        ("No BLYAT on shift", {"blyat", "блять"}),
        ("HUY and nahuy", {"huy", "хуй", "nahuy", "нахуй"}),
        ("Mephedron delivery", {"mephedron", "мефедрон"}),
        ("selling mephedrone", {"mephedrone", "мефедрон"}),
        ("only zakladka work", {"zakladka", "закладка"}),
        ("plain suka talk", {"suka", "сука"}),
        ("pizda in latin", {"pizda", "пизда"}),
    ],
)
def test_translit_variants_blocked(text: str, expected_terms: set[str]) -> None:
    violation = content_moderation_service.check_text("description", text)
    assert violation is not None
    assert violation.matched_term in expected_terms


def test_homoglyph_cyrillic_o_in_govno_blocked() -> None:
    # Latin g,v,n + Cyrillic о (homoglyph evasion)
    violation = content_moderation_service.check_text("description", "Это gоvnо")
    assert violation is not None
    assert violation.matched_term in {"govno", "говно"}


def test_mixed_script_pidor_blocked() -> None:
    violation = content_moderation_service.check_text("description", "Только пидor")
    assert violation is not None
    assert violation.matched_term in {"pidor", "пидор"}


def test_mixed_script_pizda_blocked() -> None:
    violation = content_moderation_service.check_text("description", "Latin pizdа")
    assert violation is not None
    assert violation.matched_term in {"pizda", "пизда"}


def test_normalize_translit_to_cyrillic() -> None:
    assert content_moderation_service.normalize_for_matching("BLYAT") == "блять"
    assert content_moderation_service.normalize_for_matching("zakladka") == "закладка"
    assert content_moderation_service.normalize_for_matching("Mephedron") == "мефедрон"


@pytest.mark.parametrize(
    "company_name",
    [
        "McDonald's",
        "KFC",
        "ООО McDonald's Russia",
        "Burger King LLC",
    ],
)
def test_company_name_allows_legitimate_latin_brands(company_name: str) -> None:
    assert content_moderation_service.check_text("company_name", company_name) is None


def test_company_name_still_blocks_translit_profanity() -> None:
    violation = content_moderation_service.check_text("company_name", "Super PIZDA LLC")
    assert violation is not None
    assert violation.matched_term in {"pizda", "пизда"}


@pytest.mark.asyncio
async def test_update_job_request_blocks_draft_to_active_with_bad_description(monkeypatch) -> None:
    job_id = uuid4()
    employer_id = uuid4()
    now = datetime.now(timezone.utc)

    class FakeJob:
        def __init__(self, status: JobRequestStatus):
            self.id = job_id
            self.status = status
            self.notify_matching_workers = False
            self.post_to_groups = False
            self.employer_id = employer_id
            self.category_id = 1
            self.title = "Официант"
            self.description = "Работа с govno"
            self.metro_station_id = 1
            self.hourly_rate = Decimal("400")
            self.workers_needed = 1
            self.min_experience_months = None
            self.required_gender = None
            self.min_age = None
            self.max_age = None
            self.dress_code = None
            self.contact_info = None
            self.address = None
            self.includes_lunch = False
            self.created_at = now
            self.updated_at = now
            self.shift_slots = []
            self.category = None
            self.metro_station = None

    fake_job = FakeJob(JobRequestStatus.draft)

    class VerifiedEmployer:
        verified = True

    class DummySession:
        async def flush(self) -> None:
            return None

        async def scalar(self, stmt):
            return fake_job

        async def get(self, model, pk):
            from app.db.models import Employer

            if model is Employer and pk == employer_id:
                return VerifiedEmployer()
            return None

    with pytest.raises(content_moderation_service.ContentRejectedError):
        await job_service.update_job_request(
            DummySession(),
            employer_id,
            job_id,
            JobRequestUpdate(status=JobRequestStatus.active),
        )

    assert fake_job.status == JobRequestStatus.draft


@pytest.mark.asyncio
async def test_update_job_request_allows_clean_draft_to_active(monkeypatch) -> None:
    job_id = uuid4()
    employer_id = uuid4()
    now = datetime.now(timezone.utc)

    class FakeJob:
        def __init__(self, status: JobRequestStatus):
            self.id = job_id
            self.status = status
            self.notify_matching_workers = False
            self.post_to_groups = False
            self.employer_id = employer_id
            self.category_id = 1
            self.title = "Официант"
            self.description = "Обслуживание зала"
            self.metro_station_id = 1
            self.hourly_rate = Decimal("400")
            self.workers_needed = 1
            self.min_experience_months = None
            self.required_gender = None
            self.min_age = None
            self.max_age = None
            self.dress_code = None
            self.contact_info = None
            self.address = None
            self.includes_lunch = False
            self.created_at = now
            self.updated_at = now
            self.shift_slots = []
            self.category = None
            self.metro_station = None

    fake_job = FakeJob(JobRequestStatus.draft)

    class VerifiedEmployer:
        verified = True

    class DummySession:
        async def flush(self) -> None:
            fake_job.status = JobRequestStatus.active

        async def scalar(self, stmt):
            return fake_job

        async def get(self, model, pk):
            from app.db.models import Employer

            if model is Employer and pk == employer_id:
                return VerifiedEmployer()
            return None

    enqueue_mock = AsyncMock(return_value="job-123")
    monkeypatch.setattr(job_service, "enqueue_job", enqueue_mock)

    result = await job_service.update_job_request(
        DummySession(),
        employer_id,
        job_id,
        JobRequestUpdate(status=JobRequestStatus.active),
    )

    assert result.status == JobRequestStatus.active


TEST_BOT_TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"


@pytest.fixture
async def moderation_api_client(monkeypatch: pytest.MonkeyPatch):
    from app.core import config

    monkeypatch.setenv("BOT_TOKEN", TEST_BOT_TOKEN)
    config.get_settings.cache_clear()

    test_user = User(
        id=uuid4(),
        telegram_id=54321,
        username="employer1",
        role=UserRole.employer,
    )
    test_employer = Employer(
        id=uuid4(),
        user_id=test_user.id,
        company_name="ООО Тест",
        contact_phone="+79990001122",
        contact_person="Иван",
        verified=False,
    )

    async def override_user():
        return test_user

    async def override_employer():
        return test_employer

    async def override_session():
        class DummySession:
            async def commit(self) -> None:
                return None

        yield DummySession()

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_current_employer] = override_employer
    app.dependency_overrides[get_db_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client

    app.dependency_overrides.clear()
    config.get_settings.cache_clear()


@pytest.mark.asyncio
async def test_api_publish_returns_content_rejected(moderation_api_client: AsyncClient, monkeypatch) -> None:
    record_mock = AsyncMock(return_value=False)
    monkeypatch.setattr(
        "app.api.routes.employer.moderation_violation_service.record_content_rejection",
        record_mock,
    )

    async def mock_update(session, employer_id, job_id, data):
        raise content_moderation_service.ContentRejectedError(
            content_moderation_service.ModerationViolation(
                field="description",
                matched_term="govno",
                normalized_snippet="govno",
                raw_snippet="govno",
            )
        )

    monkeypatch.setattr("app.api.routes.employer.job_service.update_job_request", mock_update)

    response = await moderation_api_client.patch(
        f"/api/v1/employer/jobs/{uuid4()}",
        headers={"Authorization": f"tma {build_test_init_data(TEST_BOT_TOKEN, 54321)}"},
        json={"status": "active"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "content_rejected"
    assert body["field"] == "description"
    assert body["detail"] == content_moderation_service.CONTENT_REJECTED_MESSAGE
    assert "matched_term" not in body
    assert "govno" not in body["detail"]
    record_mock.assert_awaited_once()


@pytest.mark.parametrize(
    "contact_info",
    [
        "contact@bar.ru",
        "@employer_spb",
        "contact@bar.ru, @employer_spb",
        "govno@mail.ru",
        "pidor@gmail.com",
        "@suka_bot",
        "t.me/pizda_channel",
        "https://t.me/mybar",
        "+79990001122",
    ],
)
def test_contact_info_skips_wordlist_on_email_and_telegram(contact_info: str) -> None:
    assert content_moderation_service.check_text("contact_info", contact_info) is None


@pytest.mark.parametrize(
    ("contact_info", "expected_terms"),
    [
        ("contact@bar.ru blyat", {"blyat", "блять"}),
        ("@employer_spb — пидor", {"pidor", "пидор"}),
        ("+79990001122, звоните suka", {"suka", "сука"}),
        ("89991234567 pidor", {"pidor", "пидор"}),
        ("t.me/mybar; только govno", {"govno", "говно"}),
    ],
)
def test_contact_info_blocks_profanity_in_free_text(
    contact_info: str,
    expected_terms: set[str],
) -> None:
    violation = content_moderation_service.check_text("contact_info", contact_info)
    assert violation is not None
    assert violation.field == "contact_info"
    assert violation.matched_term in expected_terms


def test_parse_contact_info_segments_splits_mixed_contact() -> None:
    text = "contact@bar.ru, @employer_spb, +79990001122, звоните"
    segments = content_moderation_service.parse_contact_info_segments(text)

    assert [segment.kind for segment in segments] == [
        "email",
        "text",
        "telegram",
        "text",
        "phone",
        "text",
    ]
    assert segments[0].value == "contact@bar.ru"
    assert segments[2].value == "@employer_spb"
    assert "+79990001122" in segments[4].value
