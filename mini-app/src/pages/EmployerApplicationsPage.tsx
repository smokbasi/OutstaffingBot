import { useEffect, useState } from "react";
import {
  formatApplicationStatus,
  listEmployerApplications,
  updateEmployerApplicationStatus,
  type ApplicationRead,
  type ApplicationStatus,
} from "../api/client";
import { formatHourlyRate } from "../utils/formatRate";

type EmployerApplicationsPageProps = {
  initData: string;
  reloadKey?: number;
};

type FilterStatus = "all" | ApplicationStatus;

type PageState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; items: ApplicationRead[] };

const FILTER_OPTIONS: { value: FilterStatus; label: string }[] = [
  { value: "all", label: "Все" },
  { value: "pending", label: "На рассмотрении" },
  { value: "accepted", label: "Принятые" },
  { value: "rejected", label: "Отклонённые" },
];

function formatDate(iso: string): string {
  const [year, month, day] = iso.split("-");
  if (!year || !month || !day) {
    return iso;
  }
  return `${day}.${month}.${year}`;
}

function formatTime(value: string): string {
  return value.slice(0, 5);
}

function workerLabel(item: ApplicationRead): string {
  const first = item.worker_first_name?.trim();
  const last = item.worker_last_name?.trim();
  if (first && last) {
    return `${first} ${last}`;
  }
  if (first) {
    return first;
  }
  return "Кандидат";
}

export function EmployerApplicationsPage({ initData, reloadKey = 0 }: EmployerApplicationsPageProps) {
  const [filter, setFilter] = useState<FilterStatus>("all");
  const [state, setState] = useState<PageState>({ status: "loading" });
  const [actionError, setActionError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadApplications() {
      setState({ status: "loading" });
      setActionError(null);
      try {
        const data = await listEmployerApplications(initData, {
          status: filter === "all" ? undefined : filter,
        });
        if (!cancelled) {
          setState({ status: "ready", items: data.items });
        }
      } catch (err) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : "Не удалось загрузить отклики";
          setState({ status: "error", message });
        }
      }
    }

    void loadApplications();
    return () => {
      cancelled = true;
    };
  }, [initData, reloadKey, filter]);

  async function handleStatusChange(applicationId: string, status: "accepted" | "rejected") {
    setBusyId(applicationId);
    setActionError(null);
    try {
      const updated = await updateEmployerApplicationStatus(initData, applicationId, status);
      setState((prev) => {
        if (prev.status !== "ready") {
          return prev;
        }
        const nextItems =
          filter === "all" || filter === updated.status
            ? prev.items.map((item) => (item.id === applicationId ? updated : item))
            : prev.items.filter((item) => item.id !== applicationId);
        return { status: "ready", items: nextItems };
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Не удалось обновить отклик";
      setActionError(message);
    } finally {
      setBusyId(null);
    }
  }

  if (state.status === "loading") {
    return <p className="status">Загрузка откликов…</p>;
  }

  if (state.status === "error") {
    return (
      <section className="card">
        <p className="error">{state.message}</p>
      </section>
    );
  }

  const { items } = state;
  const pendingCount = items.filter((item) => item.status === "pending").length;

  return (
    <section className="card">
      <div className="profile-header">
        <h2>Отклики на заявки</h2>
        {pendingCount > 0 ? (
          <span className="status-badge status-pending">{pendingCount} новых</span>
        ) : null}
      </div>
      <p className="hint">
        Здесь отклики работников на ваши заявки. Для статуса «на рассмотрении» нажмите «Принять» или
        «Отклонить».
      </p>

      <div className="filter-chips">
        {FILTER_OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            className={`chip${filter === option.value ? " active" : ""}`}
            onClick={() => setFilter(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>

      {actionError ? <p className="error">{actionError}</p> : null}

      {items.length === 0 ? (
        <p className="hint">Откликов пока нет.</p>
      ) : (
        <ul className="applications-list">
          {items.map((item) => (
            <li key={item.id} className="application-item application-item-employer">
              <div className="application-item-body">
                <div className="application-item-header">
                  <strong>{workerLabel(item)}</strong>
                  <span className={`status-badge status-${item.status}`}>
                    {formatApplicationStatus(item.status)}
                  </span>
                </div>
                <p>
                  <strong>{item.job_title}</strong>
                </p>
                <p className="hint">
                  {item.category_name ?? "—"} · {item.metro_station_name ?? "—"} ·{" "}
                  {formatHourlyRate(item.hourly_rate)}
                </p>
                <p>
                  {formatDate(item.shift_date)} {formatTime(item.start_time)}–{formatTime(item.end_time)}
                </p>
              </div>
              {item.status === "pending" ? (
                <div className="application-actions">
                  <button
                    type="button"
                    className="btn small-btn"
                    disabled={busyId === item.id}
                    onClick={() => void handleStatusChange(item.id, "accepted")}
                  >
                    {busyId === item.id ? "…" : "Принять"}
                  </button>
                  <button
                    type="button"
                    className="btn secondary small-btn"
                    disabled={busyId === item.id}
                    onClick={() => void handleStatusChange(item.id, "rejected")}
                  >
                    Отклонить
                  </button>
                </div>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
