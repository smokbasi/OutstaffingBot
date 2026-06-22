from uuid import UUID

from app.core.config import Settings
from app.core.mini_app_urls import build_mini_app_url, vacancy_deep_link

JOB_ID = UUID("c79947a1-104b-46cd-9e3b-800f92423e40")


def test_build_mini_app_url_preserves_query_params() -> None:
    settings = Settings(mini_app_url="https://www.outstaffingbot.online/?v=2")
    url = build_mini_app_url(settings, f"/vacancy/{JOB_ID}")

    assert url == f"https://www.outstaffingbot.online/vacancy/{JOB_ID}?v=2"


def test_build_mini_app_url_without_query() -> None:
    settings = Settings(mini_app_url="http://localhost:5173")
    url = build_mini_app_url(settings, f"/vacancy/{JOB_ID}")

    assert url == f"http://localhost:5173/vacancy/{JOB_ID}"


def test_vacancy_deep_link_helper() -> None:
    settings = Settings(mini_app_url="https://example.com/app")
    assert vacancy_deep_link(settings, JOB_ID) == f"https://example.com/app/vacancy/{JOB_ID}"


def test_vacancy_telegram_startapp_link() -> None:
    from app.core.mini_app_urls import vacancy_telegram_startapp_link

    assert (
        vacancy_telegram_startapp_link("Outstaffing_Work_BOT", JOB_ID)
        == f"https://t.me/Outstaffing_Work_BOT?startapp=vacancy_{JOB_ID}"
    )


def test_job_start_deep_link() -> None:
    from app.core.mini_app_urls import job_start_deep_link

    settings = Settings(bot_username="Outstaffing_Work_BOT")
    assert (
        job_start_deep_link(settings, JOB_ID)
        == f"https://t.me/Outstaffing_Work_BOT?start=job_{JOB_ID}"
    )
    assert (
        job_start_deep_link(settings, JOB_ID, bot_username="Custom_Bot")
        == f"https://t.me/Custom_Bot?start=job_{JOB_ID}"
    )


def test_parse_job_start_payload() -> None:
    from app.core.mini_app_urls import parse_job_start_payload

    assert parse_job_start_payload(None) is None
    assert parse_job_start_payload("") is None
    assert parse_job_start_payload("hello") is None
    assert parse_job_start_payload("job_not-a-uuid") is None
    assert parse_job_start_payload(f"job_{JOB_ID}") == JOB_ID
