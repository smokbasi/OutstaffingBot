import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["mode"] in {"polling", "webhook"}


@pytest.mark.asyncio
async def test_webhook_disabled_returns_404(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WEBHOOK_URL", raising=False)
    monkeypatch.delenv("WEBHOOK_SECRET", raising=False)
    get_settings.cache_clear()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/webhook/any-secret", json={"update_id": 1})
    assert response.status_code == 404

    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_webhook_rejects_invalid_secret_header(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WEBHOOK_URL", "https://example.com/webhook/top-secret")
    monkeypatch.setenv("WEBHOOK_SECRET", "top-secret")
    monkeypatch.setenv("BOT_TOKEN", "123456:ABC-DEF")
    get_settings.cache_clear()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/webhook/top-secret",
            json={"update_id": 1},
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
        )
    assert response.status_code == 403

    get_settings.cache_clear()
