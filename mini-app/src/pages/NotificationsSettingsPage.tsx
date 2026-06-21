import { useEffect, useState, type FormEvent } from "react";
import {
  getWorkerPreferences,
  listCategories,
  searchMetroStations,
  updateWorkerPreferences,
  type JobCategory,
  type MetroStation,
  type WorkerPreferences,
} from "../api/client";

type NotificationsSettingsPageProps = {
  initData: string;
};

type PageState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; preferences: WorkerPreferences; categories: JobCategory[] };

type FormState = {
  notifications_enabled: boolean;
  category_ids: number[];
  metro_station_ids: number[];
  min_hourly_rate: string;
};

export function NotificationsSettingsPage({ initData }: NotificationsSettingsPageProps) {
  const [state, setState] = useState<PageState>({ status: "loading" });
  const [form, setForm] = useState<FormState | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [metroQuery, setMetroQuery] = useState("");
  const [metroResults, setMetroResults] = useState<MetroStation[]>([]);
  const [metroLoading, setMetroLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [preferences, categories] = await Promise.all([
          getWorkerPreferences(initData),
          listCategories(),
        ]);
        if (!cancelled) {
          setState({ status: "ready", preferences, categories });
          setForm({
            notifications_enabled: preferences.notifications_enabled,
            category_ids: [...preferences.category_ids],
            metro_station_ids: [...preferences.metro_station_ids],
            min_hourly_rate: preferences.min_hourly_rate ?? "",
          });
        }
      } catch (err) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : "Не удалось загрузить настройки";
          setState({ status: "error", message });
        }
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [initData]);

  useEffect(() => {
    const query = metroQuery.trim();
    if (query.length < 2) {
      setMetroResults([]);
      return;
    }

    let cancelled = false;
    const timer = setTimeout(() => {
      setMetroLoading(true);
      void searchMetroStations(query)
        .then((stations) => {
          if (!cancelled) {
            setMetroResults(stations);
          }
        })
        .catch(() => {
          if (!cancelled) {
            setMetroResults([]);
          }
        })
        .finally(() => {
          if (!cancelled) {
            setMetroLoading(false);
          }
        });
    }, 300);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [metroQuery]);

  function toggleCategory(categoryId: number) {
    setForm((prev) => {
      if (!prev) {
        return prev;
      }
      const has = prev.category_ids.includes(categoryId);
      return {
        ...prev,
        category_ids: has
          ? prev.category_ids.filter((id) => id !== categoryId)
          : [...prev.category_ids, categoryId],
      };
    });
    setSaveError(null);
  }

  function addMetro(station: MetroStation) {
    setForm((prev) => {
      if (!prev || prev.metro_station_ids.includes(station.id)) {
        return prev;
      }
      return {
        ...prev,
        metro_station_ids: [...prev.metro_station_ids, station.id],
      };
    });
    setMetroQuery("");
    setMetroResults([]);
    setSaveError(null);
  }

  function removeMetro(stationId: number) {
    setForm((prev) => {
      if (!prev) {
        return prev;
      }
      return {
        ...prev,
        metro_station_ids: prev.metro_station_ids.filter((id) => id !== stationId),
      };
    });
    setSaveError(null);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!form) {
      return;
    }

    setIsSaving(true);
    setSaveError(null);
    try {
      const updated = await updateWorkerPreferences(initData, {
        notifications_enabled: form.notifications_enabled,
        category_ids: form.category_ids,
        metro_station_ids: form.metro_station_ids,
        min_hourly_rate: form.min_hourly_rate.trim() || null,
      });
      if (state.status === "ready") {
        setState({ ...state, preferences: updated });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Не удалось сохранить настройки";
      setSaveError(message);
    } finally {
      setIsSaving(false);
    }
  }

  if (state.status === "loading") {
    return <p className="status">Загрузка настроек…</p>;
  }

  if (state.status === "error") {
    return (
      <section className="card">
        <p className="error">{state.message}</p>
      </section>
    );
  }

  if (!form) {
    return null;
  }

  const selectedMetroLabels = form.metro_station_ids.map((id) => {
    const fromResults = metroResults.find((s) => s.id === id);
    return fromResults ? fromResults.name : `Станция #${id}`;
  });

  return (
    <section className="card">
      <h2>Уведомления</h2>
      <p className="hint">
        Push о новых вакансиях по вашим категориям, ставке и метро. Пустые фильтры — все подходящие
        категории из опыта.
      </p>

      <form className="profile-form" onSubmit={(e) => void handleSubmit(e)}>
        <label className="form-field checkbox-field">
          <input
            type="checkbox"
            checked={form.notifications_enabled}
            disabled={isSaving}
            onChange={(e) =>
              setForm((prev) =>
                prev ? { ...prev, notifications_enabled: e.target.checked } : prev,
              )
            }
          />
          <span>Получать push-уведомления</span>
        </label>

        <div className="form-field">
          <span>Категории (пусто = все из опыта)</span>
          <ul className="checkbox-list">
            {state.categories.map((category) => (
              <li key={category.id}>
                <label>
                  <input
                    type="checkbox"
                    checked={form.category_ids.includes(category.id)}
                    disabled={isSaving}
                    onChange={() => toggleCategory(category.id)}
                  />
                  {category.name_ru}
                </label>
              </li>
            ))}
          </ul>
        </div>

        <label className="form-field">
          <span>Мин. ставка для push (₽/час)</span>
          <input
            type="number"
            min={0}
            step="1"
            value={form.min_hourly_rate}
            disabled={isSaving}
            onChange={(e) =>
              setForm((prev) => (prev ? { ...prev, min_hourly_rate: e.target.value } : prev))
            }
          />
        </label>

        <div className="form-field">
          <span>Станции метро (пусто = без фильтра)</span>
          <input
            type="text"
            value={metroQuery}
            placeholder="Добавить станцию…"
            disabled={isSaving}
            onChange={(e) => setMetroQuery(e.target.value)}
          />
          {metroLoading ? <p className="hint">Поиск…</p> : null}
          {metroResults.length > 0 ? (
            <ul className="metro-results">
              {metroResults.map((station) => (
                <li key={station.id}>
                  <button
                    type="button"
                    className="metro-option"
                    disabled={isSaving}
                    onClick={() => addMetro(station)}
                  >
                    {station.name}
                    <span className="hint"> ({station.line_name})</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
          {form.metro_station_ids.length > 0 ? (
            <ul className="chip-list">
              {form.metro_station_ids.map((id, index) => (
                <li key={id}>
                  <span className="chip">
                    {selectedMetroLabels[index]}
                    <button
                      type="button"
                      className="link-btn"
                      disabled={isSaving}
                      onClick={() => removeMetro(id)}
                    >
                      ✕
                    </button>
                  </span>
                </li>
              ))}
            </ul>
          ) : null}
        </div>

        {saveError ? <p className="error">{saveError}</p> : null}

        <div className="form-actions">
          <button type="submit" className="btn" disabled={isSaving}>
            {isSaving ? "Сохранение…" : "Сохранить"}
          </button>
        </div>
      </form>
    </section>
  );
}
