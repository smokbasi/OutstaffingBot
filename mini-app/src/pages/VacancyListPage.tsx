import { useEffect, useState } from "react";
import {
  getWorkerProfile,
  listWorkerVacancies,
  searchMetroStations,
  type MetroStation,
  type VacancyListItem,
} from "../api/client";
import { formatHourlyRate } from "../utils/formatRate";

type VacancyListPageProps = {
  initData: string;
  reloadKey?: number;
  onOpenVacancy: (id: string) => void;
};

type ExperienceCategory = {
  id: number;
  name: string;
};

type ListState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; items: VacancyListItem[]; total: number; page: number };

function uniqueExperienceCategories(
  experiences: { category_id: number; category_name: string }[],
): ExperienceCategory[] {
  const seen = new Set<number>();
  const categories: ExperienceCategory[] = [];
  for (const exp of experiences) {
    if (seen.has(exp.category_id)) {
      continue;
    }
    seen.add(exp.category_id);
    categories.push({ id: exp.category_id, name: exp.category_name });
  }
  return categories;
}

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

function VacancyCard({
  item,
  onOpenVacancy,
}: {
  item: VacancyListItem;
  onOpenVacancy: (id: string) => void;
}) {
  return (
    <li className={`job-item${item.is_matched ? " job-item-matched" : ""}`}>
      <div className="job-item-header">
        <strong>{item.title}</strong>
      </div>
      <p className="hint">
        {item.category_name ?? "—"} · {item.metro_station_name ?? "—"}
      </p>
      <p>{formatHourlyRate(item.hourly_rate)}</p>
      <p className="hint">
        Ближайшая смена: {formatDate(item.next_shift_date)}
        {item.next_shift_start ? ` ${formatTime(item.next_shift_start)}` : ""}
        {item.available_slots > 0 ? ` · мест: ${item.available_slots}` : ""}
      </p>
      {item.includes_lunch ? <p className="hint">🍽 Обед включён</p> : null}
      <div className="job-actions">
        <button type="button" className="btn" onClick={() => onOpenVacancy(item.id)}>
          Подробнее
        </button>
      </div>
    </li>
  );
}

export function VacancyListPage({ initData, reloadKey = 0, onOpenVacancy }: VacancyListPageProps) {
  const [state, setState] = useState<ListState>({ status: "loading" });
  const [profileReady, setProfileReady] = useState(false);
  const [showAllVacancies, setShowAllVacancies] = useState(true);
  const [experienceCategories, setExperienceCategories] = useState<ExperienceCategory[]>([]);
  const [categoryId, setCategoryId] = useState<number | "">("");
  const [metroQuery, setMetroQuery] = useState("");
  const [metroStationId, setMetroStationId] = useState<number | null>(null);
  const [metroLabel, setMetroLabel] = useState("");
  const [metroResults, setMetroResults] = useState<MetroStation[]>([]);
  const [minRate, setMinRate] = useState("");
  const [page, setPage] = useState(1);
  const limit = 10;

  useEffect(() => {
    let cancelled = false;

    void getWorkerProfile(initData)
      .then((profile) => {
        if (cancelled) {
          return;
        }
        const categories = uniqueExperienceCategories(profile.experiences);
        setExperienceCategories(categories);
        setShowAllVacancies(profile.show_all_vacancies);
        setCategoryId((prev) => {
          if (prev === "" || categories.some((cat) => cat.id === prev)) {
            return prev;
          }
          return "";
        });
        setProfileReady(true);
      })
      .catch((err) => {
        if (cancelled) {
          return;
        }
        const message = err instanceof Error ? err.message : "Не удалось загрузить профиль";
        if (message.includes("404") || message.toLowerCase().includes("not found")) {
          setState({
            status: "error",
            message: "Профиль работника не найден. Заполните его в боте: «📝 Заполнить профиль».",
          });
        } else {
          setState({ status: "error", message });
        }
        setProfileReady(false);
      });

    return () => {
      cancelled = true;
    };
  }, [initData, reloadKey]);

  useEffect(() => {
    if (!profileReady) {
      return;
    }

    if (!showAllVacancies && experienceCategories.length === 0) {
      setState({
        status: "error",
        message:
          "В профиле нет категорий опыта — вакансии не показываются. Добавьте опыт во вкладке «Профиль» → «Добавить опыт».",
      });
      return;
    }

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
  }, [
    profileReady,
    showAllVacancies,
    experienceCategories,
    initData,
    categoryId,
    metroStationId,
    minRate,
    page,
    limit,
  ]);

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

  const matchedItems = state.status === "ready" ? state.items.filter((item) => item.is_matched) : [];
  const otherItems = state.status === "ready" ? state.items.filter((item) => !item.is_matched) : [];
  const showSections =
    showAllVacancies && matchedItems.length > 0 && otherItems.length > 0;

  return (
    <section className="card vacancy-list">
      <h2>Поиск вакансий</h2>
      <p className="hint">
        {showAllVacancies
          ? "Показываются все активные вакансии; подходящие по вашему опыту — сверху."
          : "Показываются только вакансии в категориях из вашего опыта."}
      </p>

      <div className="profile-form filters-form">
        {experienceCategories.length > 0 ? (
          <label className="form-field compact">
            <span>Категория</span>
            <select
              value={categoryId}
              onChange={(event) => {
                setCategoryId(event.target.value === "" ? "" : Number(event.target.value));
                setPage(1);
              }}
            >
              <option value="">{showAllVacancies ? "Все категории" : "Все из моего опыта"}</option>
              {experienceCategories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
          </label>
        ) : null}

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
        <p className="hint">
          {showAllVacancies
            ? "Активных вакансий пока нет. Попробуйте изменить фильтры."
            : `Подходящих вакансий пока нет${
                categoryId !== ""
                  ? ` («${experienceCategories.find((cat) => cat.id === categoryId)?.name ?? "выбранная категория"}»)`
                  : ""
              }. Попробуйте изменить фильтры, включите «Показывать все вакансии» в профиле или добавьте категорию опыта.`}
        </p>
      ) : null}

      {state.status === "ready" && state.items.length > 0 ? (
        <>
          <p className="hint">
            Найдено: {state.total} · стр. {state.page}/{totalPages}
          </p>
          {showSections ? (
            <>
              <h3 className="vacancy-section-title">Подходящие</h3>
              <ul className="jobs-list">
                {matchedItems.map((item) => (
                  <VacancyCard key={item.id} item={item} onOpenVacancy={onOpenVacancy} />
                ))}
              </ul>
              <h3 className="vacancy-section-title">Остальные</h3>
              <ul className="jobs-list">
                {otherItems.map((item) => (
                  <VacancyCard key={item.id} item={item} onOpenVacancy={onOpenVacancy} />
                ))}
              </ul>
            </>
          ) : (
            <ul className="jobs-list">
              {state.items.map((item) => (
                <VacancyCard key={item.id} item={item} onOpenVacancy={onOpenVacancy} />
              ))}
            </ul>
          )}
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
