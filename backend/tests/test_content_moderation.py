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
from app.services.moderation_lemmatizer import lemmatize_ru_token
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


# --- Phase 9.3.7.1: intra-word space collapse (Level 2) ---


@pytest.mark.parametrize(
    "text",
    [
        "и щ у д е в о ч к у д л я и н т и м а",
        "п р о д а ю м е т а д о н",
        "б л я т ь , о т л и ч н а я р а б о т а",
        "с е к с услуги срочно",
        "к у п л ю г е р о и н",
        "г е р о и н",
        "з а к л а д к а",
        "м е ф е д р о н",
        "п р о д а ю к о к а и н",
    ],
)
def test_level2_spaced_letter_evasion_blocked(text: str) -> None:
    violation = content_moderation_service.check_text("description", text)
    assert violation is not None


@pytest.mark.parametrize(
    "text",
    [
        "и щ у официанта",
        "в и т а м и н ы",
        "(м. рядом)",
        "Обслуживание зала в ресторане",
    ],
)
def test_level2_spaced_letter_regression_passes(text: str) -> None:
    assert content_moderation_service.check_text("description", text) is None


def test_collapse_intra_word_spaces_normalizes_spaced_runs() -> None:
    assert (
        content_moderation_service.normalize_for_matching("и щ у д е в о ч к у")
        == "ищудевочку"
    )
    assert (
        content_moderation_service.normalize_for_matching("с е к с услуги")
        == "секс услуги"
    )
    assert (
        content_moderation_service.normalize_for_matching("и щ у официанта")
        == "ищу официанта"
    )


# --- Phase 9.3.7.2: Cyrillic leet (Level 3) ---


@pytest.mark.parametrize(
    "text",
    [
        "ищу д3в0чку для 1нтимa",
        "пр0даю м3тад0н",
        "1нтимa",
        "м3тад0н",
        "г3р0ин",
        "к0каин",
    ],
)
def test_level3_cyrillic_leet_blocked(text: str) -> None:
    violation = content_moderation_service.check_text("description", text)
    assert violation is not None


@pytest.mark.parametrize(
    "text",
    [
        "3 смены в неделю",
        "опыт 10 лет",
    ],
)
def test_level3_cyrillic_leet_regression_passes(text: str) -> None:
    assert content_moderation_service.check_text("description", text) is None


def test_level3_cyrillic_leet_at_symbol_still_blocks() -> None:
    violation = content_moderation_service.check_text("description", "бл@ть это пиздец")
    assert violation is not None
    assert violation.matched_term in {"пиздец", "pizdec", "pizdets"}


# --- Phase 9.3.7.3: translit / mixed-script (Level 4) ---


@pytest.mark.parametrize(
    "text",
    [
        "prodau metadon",
        "ищу девочку для intiма",
        "vip devushki escort",
        "zakladka v centre",
        "продам gashish",
    ],
)
def test_level4_translit_mixed_script_blocked(text: str) -> None:
    violation = content_moderation_service.check_text("description", text)
    assert violation is not None


@pytest.mark.parametrize(
    "text",
    [
        "nuzhen escort na segodnya",
        "McDonald's",
        "IT support",
        "KFC lounge bar",
    ],
)
def test_level4_translit_regression(text: str) -> None:
    if text == "nuzhen escort na segodnya":
        violation = content_moderation_service.check_text("description", text)
        assert violation is not None
        assert violation.matched_term in {"escort", "escort services", "escort service"}
    else:
        assert content_moderation_service.check_text("description", text) is None


# --- Phase 9.3.7.5: full bypass audit regression (44 phrases, slang deferred) ---

# (phrase, level, expect_block) — baseline audit 2026-07: 20 BLOCK / 24 PASS;
# after 9.3.7.1–9.3.7.3: 27 BLOCK / 17 PASS (9.3.7.4 slang skipped).
_BYPASS_AUDIT: list[tuple[str, int, bool]] = [
    # Level 1 — direct match
    ("Ищу девочку для интима сегодня", 1, True),
    ("Продаю метадон", 1, True),
    ("Бля, это пиздец какая работа", 1, True),
    ("Нужна проститутка на ночь", 1, True),
    ("Куплю героин", 1, True),
    # Level 2 — spaced letters
    ("и щ у д е в о ч к у д л я и н т и м а", 2, True),
    ("п р о д а ю м е т а д о н", 2, True),
    ("б л я т ь , о т л и ч н а я р а б о т а", 2, True),
    ("с е к с услуги срочно", 2, True),
    ("к у п л ю г е р ы ч", 2, True),  # герыч — blind block (9.3.7.6)
    # Level 3 — Cyrillic leet
    ("ищу д3в0чку для 1нтимa", 3, True),
    ("пр0даю м3тад0н", 3, True),
    ("бл@ть это пиздец", 3, True),
    ("секс-услуги, минет, полный сервис", 3, True),
    ("куплю geroин или m3ф", 3, True),
    # Level 4 — translit / homoglyphs
    ("ищу девочку для intiма", 4, True),
    ("prodau metadon", 4, True),
    ("блять это pizdec", 4, True),
    ("nuzhen escort na segodnya", 4, True),
    ("kuplyu g3roin ili meфedron", 4, True),
    ("сeкс услуги, минeт, анал", 4, True),
    ("ищу шлюxу на выезд", 4, True),
    # Level 5 — slang (partial; 9.3.7.4 skipped)
    ("Ищу тёлку на расслабон с полным контактом", 5, True),
    ("Нужен мальчик для массажа с продолжением", 5, False),
    ("Продаю белый порошок, хорошее качество", 5, False),
    ("Ищу кекс на ночь с допами", 5, False),
    ("Есть витамины", 5, False),
    ("Нужна массажистка с happy end", 5, False),
    ("бля буду, нормальная подработка", 5, True),
    ("Ищу девчонку на интим без резины", 5, True),
    ('Продам "снег" или "лед" в хорошем состоянии', 5, False),
    ("Нужен друг для взрослых игр, выезд", 5, False),
    ("Ищу лялю на 2-3 часа с полным сервисом", 5, False),
    ('Есть "колеса" и "марки", звони', 5, True),
    # Level 6 — combined bypasses
    ("ищу tелку na rasslabon c happyend", 6, True),
    ("пр0даю бeлый", 6, False),
    ("нyжeн бoй для v3рослых игр", 6, False),
    ("есть мд, ск, кокс", 6, True),
    ("ищу шлюшку на вы3d с p0лным k0ntakt0m", 6, True),
    ("массаж + продолжение, без цензуры", 6, False),
    ("кекс на ночь, допы приветствуются", 6, False),
    ("ищу девчoнку для v3чeринки с продолжeниeм", 6, False),
    ('продам "сахар" или "муку"', 6, False),
    ("Нужна ласточка на пару часов с глубоким массажем", 6, False),
]


@pytest.mark.parametrize(("phrase", "level", "expect_block"), _BYPASS_AUDIT)
def test_bypass_audit_level(phrase: str, level: int, expect_block: bool) -> None:
    violation = content_moderation_service.check_text("description", phrase)
    if expect_block:
        assert violation is not None, f"L{level} expected BLOCK: {phrase!r}"
    else:
        assert violation is None, (
            f"L{level} expected PASS: {phrase!r} (matched {violation.matched_term})"
        )


def test_bypass_audit_summary_stats() -> None:
    """Document aggregate bypass coverage (9.3.7.5)."""
    blocked = sum(
        1
        for phrase, _, expect_block in _BYPASS_AUDIT
        if expect_block
    )
    total = len(_BYPASS_AUDIT)
    assert total == 44
    assert blocked == 29  # +1: марки (LSD) now blind block per wiki curation


def test_est_common_verb_not_blocked() -> None:
    """«есть» removed from profanity — everyday phrase must pass."""
    assert content_moderation_service.check_text("description", "Есть витамины") is None
    assert content_moderation_service.check_text("title", "Есть витамины") is None


def test_profanity_still_blocked_after_est_removed() -> None:
    violation = content_moderation_service.check_text("description", "Это полный govno текст")
    assert violation is not None
    assert violation.matched_term in {"govno", "говно"}


def test_explicit_profanity_blocked() -> None:
    violation = content_moderation_service.check_text("description", "Это полный govno текст")
    assert violation is not None
    assert violation.field == "description"
    assert violation.matched_term in {"govno", "говно"}


@pytest.mark.parametrize(
    ("text", "field", "expected_terms"),
    [
        ("Разбивка гашиша", "title", {"гашиш"}),
        ("Разбивка гашиша", "description", {"гашиш"}),
        ("гашиш", "title", {"гашиш"}),
        ("продажа героина", "description", {"героин"}),
    ],
)
def test_inflected_cyrillic_blocked_via_lemma(
    text: str,
    field: str,
    expected_terms: set[str],
) -> None:
    violation = content_moderation_service.check_text(field, text)
    assert violation is not None
    assert violation.field == field
    assert violation.matched_term in expected_terms
    assert violation.category == "drugs"


def test_lemmatize_ru_token_inflects_hashish() -> None:
    assert lemmatize_ru_token("гашиша") == "гашиш"
    assert lemmatize_ru_token("гашиш") == "гашиш"


def test_lemmatize_skips_latin_tokens() -> None:
    assert lemmatize_ru_token("govno") == "govno"


def test_moderate_job_for_publish_blocks_inflected_drug_title() -> None:
    with pytest.raises(content_moderation_service.ContentRejectedError) as exc_info:
        content_moderation_service.moderate_job_for_publish(
            title="Разбивка гашиша",
            description="Обслуживание зала в ресторане",
        )
    assert exc_info.value.violation.field == "title"
    assert exc_info.value.violation.matched_term == "гашиш"


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


def test_moderate_job_for_publish_allows_latin_brand_title() -> None:
    content_moderation_service.moderate_job_for_publish(
        title="Официант McDonald's",
        description="Нормальное описание",
    )


def test_moderate_job_for_publish_raises_on_violation() -> None:
    with pytest.raises(content_moderation_service.ContentRejectedError) as exc_info:
        content_moderation_service.moderate_job_for_publish(
            title="Официант",
            description="Работа с хуйня на смене",
        )
    assert exc_info.value.violation.field == "description"


def test_moderate_company_name_blocks_profanity() -> None:
    with pytest.raises(content_moderation_service.ContentRejectedError):
        content_moderation_service.moderate_company_name("Супер пизда")


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
        ("No BLYAT on shift", {"blyat", "блять", "блядь"}),
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
def test_company_name_latin_brands_allowed(company_name: str) -> None:
    assert content_moderation_service.check_text("company_name", company_name) is None


@pytest.mark.parametrize(
    ("text", "expected_terms"),
    [
        ("Нужен косяк на смену", {"косяк"}),
        ("Только шмаль", {"шмаль"}),
        ("vip девушки на вечер", {"vip девушки"}),
    ],
)
def test_slang_manual_exact_match(text: str, expected_terms: set[str]) -> None:
    violation = content_moderation_service.check_text("description", text)
    assert violation is not None
    assert violation.matched_term in expected_terms


@pytest.mark.parametrize(
    ("text", "expected_terms"),
    [
        ("Только Хyй", {"хуй", "hui", "huy"}),
        ("Пиздa в заголовке", {"пизда", "pizda"}),
        ("Сукa на смене", {"сука", "suka"}),
    ],
)
def test_visual_homoglyph_mixed_script_blocked(text: str, expected_terms: set[str]) -> None:
    violation = content_moderation_service.check_text("title", text)
    assert violation is not None
    assert violation.matched_term in expected_terms


def test_company_name_still_blocks_profanity() -> None:
    violation = content_moderation_service.check_text("company_name", "Супер пизда")
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
            self.description = "Работа с хуйня"
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


@pytest.mark.asyncio
async def test_api_create_job_returns_content_rejected(moderation_api_client: AsyncClient, monkeypatch) -> None:
    record_mock = AsyncMock(return_value=False)
    monkeypatch.setattr(
        "app.api.routes.employer.moderation_violation_service.record_content_rejection",
        record_mock,
    )

    async def mock_create(session, employer_id, data):
        raise content_moderation_service.ContentRejectedError(
            content_moderation_service.ModerationViolation(
                field="title",
                matched_term="гашиш",
                normalized_snippet="гашиша",
                raw_snippet="Разбивка гашиша",
                category="drugs",
            )
        )

    monkeypatch.setattr("app.api.routes.employer.job_service.create_job_request", mock_create)

    payload = {
        "category_id": 1,
        "title": "Разбивка гашиша",
        "description": "Обслуживание зала",
        "metro_station_id": 1,
        "address": "ул. Примерная, 1",
        "contact_phone": "+79990000000",
        "hourly_rate": "400.00",
        "workers_needed": 2,
        "includes_lunch": True,
        "post_to_groups": True,
        "notify_matching_workers": True,
        "shift_slots": [
            {
                "shift_date": "2026-06-25",
                "start_time": "10:00:00",
                "end_time": "22:00:00",
            }
        ],
    }

    response = await moderation_api_client.post(
        "/api/v1/employer/jobs",
        headers={"Authorization": f"tma {build_test_init_data(TEST_BOT_TOKEN, 54321)}"},
        json=payload,
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "content_rejected"
    assert body["field"] == "title"
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
        ("contact@bar.ru blyat", {"blyat", "блять", "блядь"}),
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


def test_drugs_wordlist_count_after_wiki_rollback() -> None:
    """Phase B wiki bulk removed — drugs restored to pre-wiki range."""
    content_moderation_service._wordlists.cache_clear()
    _, _, _, drugs, _, _, _ = content_moderation_service._wordlists()
    assert len(drugs) == 673
    assert len(drugs) < 700


def test_violence_category_loads_after_merge() -> None:
    """Violence bucket enabled after candidates merge."""
    content_moderation_service._wordlists.cache_clear()
    _, _, violence, _, _, _, slang = content_moderation_service._wordlists()
    assert len(violence) > 400
    assert "игил" in violence
    assert "сдохнуть" in violence
    assert content_moderation_service._category_for_term("игил") == "violence"
    assert "убью тебя" in slang


@pytest.mark.parametrize(
    ("text", "expected_categories", "expected_terms"),
    [
        ("сдохни уже", {"violence", "slang"}, {"сдохни", "сдохни уже", "сдохнуть"}),
        (
            "зарежу тебя если опоздаешь",
            {"violence", "slang"},
            {"зарежу", "зарежу тебя", "зарежу если", "зарезать"},
        ),
        ("поддержка игил запрещена", {"violence"}, {"игил"}),
        ("путин убийца и вор", {"violence", "slang"}, {"путин убийца"}),
        ("ты хохол и москаль", {"violence"}, {"хохол", "москаль"}),
        ("чурка в тексте", {"violence"}, {"чурка"}),
    ],
)
def test_violence_terms_blocked(
    text: str,
    expected_categories: set[str],
    expected_terms: set[str],
) -> None:
    content_moderation_service._wordlists.cache_clear()
    violation = content_moderation_service.check_text("description", text)
    assert violation is not None
    assert violation.category in expected_categories
    assert violation.matched_term in expected_terms


@pytest.mark.parametrize(
    "text",
    [
        "президент компании ищет менеджера",
        "исламский банк открыл вакансию",
        "доставка дронами по городу",
        "оператор дрона на складе",
        "президент фирмы на связи",
    ],
)
def test_violence_context_required_false_positives_pass(text: str) -> None:
    content_moderation_service._wordlists.cache_clear()
    assert content_moderation_service.check_text("description", text) is None


def test_violence_putin_neutral_mention_passes() -> None:
    """«путин» alone is context_required — no blind block."""
    content_moderation_service._wordlists.cache_clear()
    assert content_moderation_service.check_text("description", "новости про путин") is None


def test_phase_a_drug_terms_still_blocked() -> None:
    """Explicit Phase A additions must remain after wiki rollback."""
    for term in ("марка", "фен", "колоться", "колиться", "укол", "ешка"):
        _, _, _, drugs, _, _, _ = content_moderation_service._wordlists()
        assert term in drugs, f"Phase A term missing: {term}"
    violation = content_moderation_service.check_text(
        "description",
        'Есть "колеса" и "марки", звони',
    )
    assert violation is not None
    assert violation.category == "drugs"
