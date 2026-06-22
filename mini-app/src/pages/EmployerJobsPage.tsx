import { useEffect, useState } from "react";
import {
  formatJobRequestStatus,
  listEmployerJobs,
  updateJobStatus,
  type JobRequest,
  type JobRequestStatus,
} from "../api/client";
import { triggerHaptic } from "../lib/telegram";

type EmployerJobsPageProps = {
  initData: string;
  onCreateClick?: () => void;
  onViewApplications?: (jobId: string, jobTitle: string) => void;
  reloadKey?: number;
};

type JobsState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; jobs: JobRequest[] };

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

function formatRate(rate: string): string {
  const num = Number(rate);
  return Number.isNaN(num) ? rate : `${num.toLocaleString("ru-RU")} ₽/час`;
}

export function EmployerJobsPage({
  initData,
  onCreateClick,
  onViewApplications,
  reloadKey = 0,
}: EmployerJobsPageProps) {
  const [state, setState] = useState<JobsState>({ status: "loading" });
  const [actionError, setActionError] = useState<string | null>(null);
  const [busyJobId, setBusyJobId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadJobs() {
      setState({ status: "loading" });
      try {
        const jobs = await listEmployerJobs(initData);
        if (!cancelled) {
          setState({ status: "ready", jobs });
        }
      } catch (err) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : "Не удалось загрузить заявки";
          if (message.includes("404") || message.toLowerCase().includes("employer profile")) {
            setState({
              status: "error",
              message: "Профиль работодателя не найден. Заполните его в боте: «🏢 Работодатель».",
            });
          } else {
            setState({ status: "error", message });
          }
        }
      }
    }

    void loadJobs();
    return () => {
      cancelled = true;
    };
  }, [initData, reloadKey]);

  async function handleStatusChange(jobId: string, status: JobRequestStatus) {
    setBusyJobId(jobId);
    setActionError(null);
    try {
      const updated = await updateJobStatus(initData, jobId, status);
      setState((prev) => {
        if (prev.status !== "ready") {
          return prev;
        }
        return {
          status: "ready",
          jobs: prev.jobs.map((job) => (job.id === jobId ? updated : job)),
        };
      });
      triggerHaptic("light");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Не удалось обновить статус";
      setActionError(message);
    } finally {
      setBusyJobId(null);
    }
  }

  if (state.status === "loading") {
    return <p className="status">Загрузка заявок…</p>;
  }

  if (state.status === "error") {
    return (
      <section className="card">
        <p className="error">{state.message}</p>
        {onCreateClick ? (
          <button type="button" className="btn secondary" onClick={onCreateClick}>
            Создать заявку
          </button>
        ) : null}
      </section>
    );
  }

  const { jobs } = state;

  return (
    <section className="card jobs-list-card">
      <div className="profile-header">
        <h2>Мои заявки</h2>
        {onCreateClick ? (
          <button type="button" className="btn" onClick={onCreateClick}>
            + Создать
          </button>
        ) : null}
      </div>

      {actionError ? <p className="error">{actionError}</p> : null}

      {jobs.length === 0 ? (
        <p className="hint">Заявок пока нет. Создайте первую.</p>
      ) : (
        <ul className="jobs-list">
          {jobs.map((job) => (
            <li key={job.id} className="job-item">
              <div className="job-item-header">
                <strong>{job.title}</strong>
                <span className={`status-badge status-${job.status}`}>
                  {formatJobRequestStatus(job.status)}
                </span>
              </div>
              <p className="hint">
                {job.category_name ?? "Категория"} · {job.metro_station_name ?? "Метро"} ·{" "}
                {formatRate(job.hourly_rate)} · {job.workers_needed} чел.
              </p>
              {job.shift_slots.length > 0 ? (
                <ul className="job-shifts">
                  {job.shift_slots.map((slot) => (
                    <li key={slot.id}>
                      {formatDate(slot.shift_date)} {formatTime(slot.start_time)}–
                      {formatTime(slot.end_time)}
                    </li>
                  ))}
                </ul>
              ) : null}
              <div className="job-actions">
                {onViewApplications && job.status !== "draft" ? (
                  <button
                    type="button"
                    className="btn"
                    onClick={() => onViewApplications(job.id, job.title)}
                  >
                    Отклики
                  </button>
                ) : null}
                {job.status === "draft" ? (
                  <button
                    type="button"
                    className="btn"
                    disabled={busyJobId === job.id}
                    onClick={() => void handleStatusChange(job.id, "active")}
                  >
                    Опубликовать
                  </button>
                ) : null}
                {job.status === "draft" || job.status === "active" ? (
                  <button
                    type="button"
                    className="btn secondary"
                    disabled={busyJobId === job.id}
                    onClick={() => void handleStatusChange(job.id, "cancelled")}
                  >
                    Отменить
                  </button>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
