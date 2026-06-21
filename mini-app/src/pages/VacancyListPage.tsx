import { useEffect, useState } from "react";
import {
  listCategories,
  listWorkerVacancies,
  searchMetroStations,
  type JobCategory,
  type MetroStation,
  type VacancyListItem,
} from "../api/client";

type VacancyListPageProps = {
  initData: string;
  onOpenVacancy: (id: string) => void;
};

type ListState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; items: VacancyListItem[]; total: number; page: number };

function formatDate(iso: string | null): string {
  if (!iso) {
    return "—";
  }
  const [year, month, day] = iso.split("-");
  if (!year || !month || !day) {
    return iso;
  }
  return `${day}.${month}.${year}`;
}

function formatTime(value: string | null): string {
  if (!value) {
    return "";
  }
  return value.slice(0, 5);
}

function formatRate(rate: string): string {
  const num = Number(rate);
  return Number.isNaN(num) ? rate : `${num.toLocaleString("ru-RU")} ₽/час`;
}

export function VacancyListPage({ initData, onOpenVacancy }: VacancyListPageProps) {
  const [state, setState] = useState<ListState>({ status: "loading" });
  const [categories, setCategories] = useState<JobCategory[]>([]);
  const [categoryId, setCategoryId] = useState<number | "">("");
  const [metroQuery, setMetroQuery] = useState("");
  const [metroStationId, setMetroStationId] = useState<number | null>(null);
  const [metroLabel, setMetroLabel] = useState("");
  const [metroResults, setMetroResults] = useState<MetroStation[]>([]);
  const [minRate, setMinRate] = useState("");
  const [page, setPage] = useState(1);
  const limit = 10;

  useEffect(() => {
    void listCategories()
      .then(setCategories)
      .catch(() => setCategories([]));
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadVacancies() {
      setState({ status: "loading" });
      try {
        const response = await listWorkerVacancies(initData, {
          category_id: categoryId === "" ? undefined : categoryId,
          metro_station_id: metroStationId ?? undefined,
          min_hourly_rate: minRate.trim() ? minRate.trim() : undefined,
          page,
          limit,
        });
        if (!cancelled) {
          setState({
            status: "ready",
            items: response.items,
            total: response.total,
            page: response.page,
          });
        }
      } catch (err) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : "Не удалось загрузить вакансии";
          if (message.includes("404") || message.toLowerCase().includes("worker profile")) {
            setState({
              status: "error",
              message: "Профиль работника не найден. Заполните его в боте: «📝 Заполнить профиль».",
            });
          } else {
            setState({ status: "error", message });
          }
        }
      }
    }

    void loadVacancies();
    return () => {
      cancelled = true;
    };
  }, [initData, categoryId, metroStationId, minRate, page, limit]);

  useEffect(() => {
    if (!metroQuery.trim()) {
      setMetroResults([]);
      return;
    }
    const timer = window.setTimeout(() => {
      void searchMetroStations(metroQuery)
        .then(setMetroResults)
        .catch(() => setMetroResults([]));
    }, 300);
    return () => window.clearTimeout(timer);
  }, [metroQuery]);

  function handleMetroSelect(station: MetroStation) {
    setMetroStationId(station.id);
    setMetroLabel(`${station.name} (${station.line_name})`);
    setMetroQuery("");
    setMetroResults([]);
    setPage(1);
  }

  function clearMetro() {
    setMetroStationId(null);
    setMetroLabel("");
    setMetroQuery("");
    setPage(1);
  }

  const totalPages =
    state.status === "ready" ? Math.max(1, Math.ceil(state.total / limit)) : 1;

  return (
    <section className="card vacancy-list">
      <h2>Поиск вакансий</h2>
      <p className="hint">Показываются активные заявки по вашим категориям опыта.</p>

      <div className="profile-form filters-form">
        <label className="form-field compact">
          <span>Категория</span>
          <select
            value={categoryId}
            onChange={(event) => {
              setCategoryId(event.target.value === "" ? "" : Number(event.target.value));
              setPage(1);
            }}
          >
            <option value="">Все из моего опыта</option>
            {categories.map((category) => (
              <option key={category.id} value={category.id}>
                {category.name_ru}
              </option>
            ))}
          </select>
        </label>

        <label className="form-field compact">
          <span>Мин. ставка (₽/час)</span>
          <input
            type="number"
            min={0}
            value={minRate}
            onChange={(event) => {
              setMinRate(event.target.value);
              setPage(1);
            }}
            placeholder="350"
          />
        </label>

        <label className="form-field compact">
          <span>Метро</span>
          {metroStationId ? (
            <div className="metro-selected">
              <span>{metroLabel}</span>
              <button type="button" className="link-btn" onClick={clearMetro}>
                Сбросить
              </button>
            </div>
          ) : (
            <>
              <input
                type="search"
                value={metroQuery}
                onChange={(event) => setMetroQuery(event.target.value)}
                placeholder="Поиск станции"
              />
              {metroResults.length > 0 ? (
                <ul className="metro-results">
                  {metroResults.map((station) => (
                    <li key={station.id}>
                      <button
                        type="button"
                        className="metro-option"
                        onClick={() => handleMetroSelect(station)}
                      >
                        {station.name} ({station.line_name})
                      </button>
                    </li>
                  ))}
                </ul>
              ) : null}
            </>
          )}
        </label>
      </div>

      {state.status === "loading" ? <p className="status">Загрузка…</p> : null}
      {state.status === "error" ? <p className="error">{state.message}</p> : null}

      {state.status === "ready" && state.items.length === 0 ? (
        <p className="hint">Подходящих вакансий пока нет. Попробуйте изменить фильтры.</p>
      ) : null}

      {state.status === "ready" && state.items.length > 0 ? (
        <>
          <p className="hint">
            Найдено: {state.total} · стр. {state.page}/{totalPages}
          </p>
          <ul className="jobs-list">
            {state.items.map((item) => (
              <li key={item.id} className="job-item">
                <div className="job-item-header">
                  <strong>{item.title}</strong>
                </div>
                <p className="hint">
                  {item.category_name ?? "—"} · {item.metro_station_name ?? "—"}
                </p>
                <p>{formatRate(item.hourly_rate)}</p>
                <p className="hint">
                  Ближайшая смена: {formatDate(item.next_shift_date)}
                  {item.next_shift_start ? ` ${formatTime(item.next_shift_start)}` : ""}
                  {item.available_slots > 0 ? ` · мест: ${item.available_slots}` : ""}
                </p>
                <div className="job-actions">
                  <button type="button" className="btn" onClick={() => onOpenVacancy(item.id)}>
                    Подробнее
                  </button>
                </div>
              </li>
            ))}
          </ul>
          <div className="pagination">
            <button
              type="button"
              className="btn secondary"
              disabled={state.page <= 1}
              onClick={() => setPage((prev) => Math.max(1, prev - 1))}
            >
              Назад
            </button>
            <button
              type="button"
              className="btn secondary"
              disabled={state.page >= totalPages}
              onClick={() => setPage((prev) => prev + 1)}
            >
              Далее
            </button>
          </div>
        </>
      ) : null}
    </section>
  );
}
