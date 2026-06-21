from app.reference.spb_metro import SPB_METRO_LINES, SPB_STATION_ORDER
from app.bot.handlers.worker_registration import _format_resume_header
from app.bot.keyboards.worker_registration import metro_lines_keyboard, metro_stations_keyboard
from app.db.models import Gender


def test_spb_metro_has_six_lines() -> None:
    assert len(SPB_METRO_LINES) == 6
    assert SPB_METRO_LINES[0].emoji == "🔴"
    assert SPB_METRO_LINES[0].hex_color == "D6083B"


def test_spb_station_order_loaded() -> None:
    assert len(SPB_STATION_ORDER) == 75
    assert SPB_STATION_ORDER[("Кировско-Выборгская", "Девяткино")] == 0


def test_metro_lines_keyboard_callback_data_within_limit() -> None:
    keyboard = metro_lines_keyboard()
    for row in keyboard.inline_keyboard:
        for button in row:
            assert len(button.callback_data.encode("utf-8")) <= 64


def test_metro_stations_keyboard_callback_data_within_limit() -> None:
    stations = [(index, f"Станция {index}") for index in range(1, 20)]
    keyboard = metro_stations_keyboard(stations)
    for row in keyboard.inline_keyboard:
        for button in row:
            assert len(button.callback_data.encode("utf-8")) <= 64


def test_metro_lines_keyboard_has_back_and_cancel() -> None:
    keyboard = metro_lines_keyboard()
    callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row]
    assert callbacks[-1] == "reg:cancel"
    assert all(callback.startswith("mline:") for callback in callbacks[:-1])


def test_metro_stations_keyboard_has_navigation() -> None:
    keyboard = metro_stations_keyboard([(1, "Автово")])
    callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row]
    assert "mback:lines" in callbacks
    assert "reg:cancel" in callbacks
    assert "mst:1" in callbacks


def test_resume_header_includes_profile_fields() -> None:
    text = _format_resume_header(
        {
            "first_name": "Иван",
            "last_name": "Петров",
            "age": 25,
            "gender": Gender.male,
            "metro_name": "Автово (Кировско-Выборгская)",
        }
    )
    assert "Иван" in text
    assert "Петров" in text
    assert "Автово" in text
