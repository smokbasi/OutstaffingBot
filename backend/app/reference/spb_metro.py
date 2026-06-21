import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SpbMetroLine:
    id: int
    name: str
    short_label: str
    emoji: str
    hex_color: str


SPB_METRO_LINES: tuple[SpbMetroLine, ...] = (
    SpbMetroLine(1, "Кировско-Выборгская", "К-В", "🔴", "D6083B"),
    SpbMetroLine(2, "Московско-Петроградская", "М-П", "🔵", "0078C9"),
    SpbMetroLine(3, "Невско-Василеостровская", "Н-В", "🟢", "009A49"),
    SpbMetroLine(4, "Лахтинско-Правобережная", "Л-П", "🟠", "EA7125"),
    SpbMetroLine(5, "Фрунзенско-Приморская", "Ф-П", "🟣", "702785"),
    SpbMetroLine(6, "Красносельско-Калининская", "К-К", "🟤", "8C5646"),
)

SPB_METRO_LINE_BY_ID: dict[int, SpbMetroLine] = {line.id: line for line in SPB_METRO_LINES}
SPB_METRO_LINE_BY_NAME: dict[str, SpbMetroLine] = {line.name: line for line in SPB_METRO_LINES}


def _load_station_order() -> dict[tuple[str, str], int]:
    data_path = Path(__file__).resolve().parents[3] / "scripts" / "data" / "metro_stations_spb.json"
    if not data_path.exists():
        return {}
    stations = json.loads(data_path.read_text(encoding="utf-8"))
    return {(item["line_name"], item["name"]): item["line_order"] for item in stations}


SPB_STATION_ORDER: dict[tuple[str, str], int] = _load_station_order()


def sort_stations_on_line(stations: list) -> list:
    return sorted(
        stations,
        key=lambda station: SPB_STATION_ORDER.get((station.line_name, station.name), 999),
    )
