from pathlib import Path

from app.bot.startup_announcement import (
    DEFAULT_RELEASE_NOTES,
    format_update_message,
    resolve_release_notes,
)
from app.core.config import Settings


def test_format_update_message_uses_release_notes() -> None:
    text = format_update_message("Добавлен профиль работника")
    assert text == "Бот обновлен!\n(Добавлен профиль работника)"


def test_format_update_message_falls_back_to_default() -> None:
    text = format_update_message("   ")
    assert text == f"Бот обновлен!\n({DEFAULT_RELEASE_NOTES})"


def test_resolve_release_notes_prefers_env(tmp_path: Path) -> None:
    notes_file = tmp_path / "RELEASE_NOTES.txt"
    notes_file.write_text("from file", encoding="utf-8")
    settings = Settings(
        bot_release_notes="from env",
        release_notes_file=str(notes_file),
    )
    assert resolve_release_notes(settings) == "from env"


def test_resolve_release_notes_reads_file(tmp_path: Path) -> None:
    notes_file = tmp_path / "RELEASE_NOTES.txt"
    notes_file.write_text("  from file  \n", encoding="utf-8")
    settings = Settings(
        bot_release_notes="",
        release_notes_file=str(notes_file),
    )
    assert resolve_release_notes(settings) == "from file"


def test_resolve_release_notes_default_when_missing() -> None:
    settings = Settings(
        bot_release_notes="",
        release_notes_file="/nonexistent/RELEASE_NOTES.txt",
    )
    assert resolve_release_notes(settings) == DEFAULT_RELEASE_NOTES
