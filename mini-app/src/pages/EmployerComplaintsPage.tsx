import { useEffect, useState, type FormEvent } from "react";
import {
  APPLICATION_STATUS_LABELS,
  COMPLAINT_VIOLATION_TYPE_LABELS,
  createEmployerComplaint,
  formatJobRequestStatus,
  listEmployerComplaintApplications,
  listEmployerComplaintJobs,
  type ApplicationStatus,
  type ComplaintViolationType,
  type EmployerComplaintApplication,
  type EmployerComplaintJob,
} from "../api/client";
import { triggerNotificationHaptic } from "../lib/telegram";

type EmployerComplaintsPageProps = {
  initData: string;
  reloadKey?: number;
};

type JobsState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; items: EmployerComplaintJob[] };

type ApplicationsState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; items: EmployerComplaintApplication[]; job: EmployerComplaintJob };

type View = "jobs" | "applications" | "form" | "success";

const VIOLATION_TYPES: ComplaintViolationType[] = ["late", "no_show", "no_payment", "no_work"];

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

function workerLabel(item: EmployerComplaintApplication): string {
  const first = item.worker_first_name?.trim();
  const last = item.worker_last_name?.trim();
  if (first && last) {
    return `${first} ${last}`;
  }
  if (first) {
    return first;
  }
  return "Работник";
}

export function EmployerComplaintsPage({ initData, reloadKey = 0 }: EmployerComplaintsPageProps) {
  const [jobsState, setJobsState] = useState<JobsState>({ status: "loading" });
  const [applicationsState, setApplicationsState] = useState<ApplicationsState>({ status: "idle" });
  const [view, setView] = useState<View>("jobs");
  const [selectedApplication, setSelectedApplication] = useState<EmployerComplaintApplication | null>(null);
  const [violationType, setViolationType] = useState<ComplaintViolationType>("late");
  const [description, setDescription] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function loadJobs() {
    setJobsState({ status: "loading" });
    try {
      const data = await listEmployerComplaintJobs(initData);
      setJobsState({ status: "ready", items: data.items });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Не удалось загрузить заявки";
      setJobsState({ status: "error", message });
    }
  }

  useEffect(() => {
    void loadJobs();
    setView("jobs");
    setApplicationsState({ status: "idle" });
    setSelectedApplication(null);
  }, [initData, reloadKey]);

  async function handleSelectJob(job: EmployerComplaintJob) {
    setApplicationsState({ status: "loading" });
    setView("applications");
    try {
      const data = await listEmployerComplaintApplications(initData, job.id);
      setApplicationsState({ status: "ready", items: data.items, job });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Не удалось загрузить отклики";
      setApplicationsState({ status: "error", message });
    }
  }

  function handleSelectApplication(item: EmployerComplaintApplication) {
    setSelectedApplication(item);
    setViolationType("late");
    setDescription("");
    setFormError(null);
    setView("form");
  }

  function handleBackToJobs() {
    setView("jobs");
    setApplicationsState({ status: "idle" });
    setSelectedApplication(null);
    setFormError(null);
  }

  function handleBackToApplications() {
    setSelectedApplication(null);
    setFormError(null);
    if (applicationsState.status === "ready") {
      setView("applications");
    } else {
      setView("jobs");
    }
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!selectedApplication) {
      return;
    }
    setBusy(true);
    setFormError(null);
    try {
      const trimmed = description.trim();
      await createEmployerComplaint(initData, {
        application_id: selectedApplication.id,
        violation_type: violationType,
        description: trimmed || null,
      });
      triggerNotificationHaptic("success");
      setView("success");
    } catch (err) {
      triggerNotificationHaptic("error");
      const message = err instanceof Error ? err.message : "Не удалось отправить жалобу";
      setFormError(message);
    } finally {
      setBusy(false);
    }
  }

  if (view === "success") {
    return (
      <section className="card">
        <h2>Жалоба отправлена</h2>
        <p className="success">Мы получили вашу жалобу. Администратор рассмотрит её в ближайшее время.</p>
        <button
          type="button"
          className="btn"
          onClick={() => {
            setView("jobs");
            setSelectedApplication(null);
            setApplicationsState({ status: "idle" });
            void loadJobs();
          }}
        >
          К списку заявок
        </button>
      </section>
    );
  }

  if (view === "form" && selectedApplication) {
    return (
      <section className="card">
        <button type="button" className="link-btn back-link" onClick={handleBackToApplications}>
          ← Назад
        </button>
        <h2>Пожаловаться на работника</h2>
        <p className="hint">
          {selectedApplication.job_title} · {workerLabel(selectedApplication)}
        </p>
        <p className="hint">
          {formatDate(selectedApplication.shift_date)}{" "}
          {formatTime(selectedApplication.start_time)}–{formatTime(selectedApplication.end_time)}
        </p>
        <form className="profile-form" onSubmit={(event) => void handleSubmit(event)}>
          <fieldset className="form-field">
            <span>Тип нарушения</span>
            <ul className="radio-list">
              {VIOLATION_TYPES.map((type) => (
                <li key={type}>
                  <label className="form-field checkbox-field">
                    <input
                      type="radio"
                      name="violation_type"
                      value={type}
                      checked={violationType === type}
                      onChange={() => setViolationType(type)}
                      disabled={busy}
                    />
                    <span>{COMPLAINT_VIOLATION_TYPE_LABELS[type]}</span>
                  </label>
                </li>
              ))}
            </ul>
          </fieldset>
          <label className="form-field">
            <span>Описание (необязательно)</span>
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Дополнительные детали…"
              rows={5}
              disabled={busy}
            />
          </label>
          {formError ? <p className="error">{formError}</p> : null}
          <div className="form-actions">
            <button type="submit" className="btn" disabled={busy}>
              {busy ? "Отправка…" : "Отправить жалобу"}
            </button>
          </div>
        </form>
      </section>
    );
  }

  if (view === "applications") {
    if (applicationsState.status === "loading") {
      return <p className="status">Загрузка откликов…</p>;
    }
    if (applicationsState.status === "error") {
      return (
        <section className="card">
          <button type="button" className="link-btn back-link" onClick={handleBackToJobs}>
            ← Назад
          </button>
          <p className="error">{applicationsState.message}</p>
        </section>
      );
    }
    if (applicationsState.status === "ready") {
      const { job, items } = applicationsState;
      return (
        <section className="card">
          <button type="button" className="link-btn back-link" onClick={handleBackToJobs}>
            ← Назад
          </button>
          <h2>{job.title}</h2>
          <p className="hint">{formatJobRequestStatus(job.status)}</p>
          {items.length === 0 ? (
            <p className="hint">Нет принятых откликов для жалобы по этой заявке.</p>
          ) : (
            <>
              <p className="hint">Выберите работника:</p>
              <ul className="applications-list">
                {items.map((item) => (
                  <li key={item.id} className="application-item">
                    <button
                      type="button"
                      className="complaint-select-btn"
                      onClick={() => handleSelectApplication(item)}
                    >
                      <strong>{workerLabel(item)}</strong>
                      <p className="hint">{item.job_title}</p>
                      <p>
                        {formatDate(item.shift_date)} {formatTime(item.start_time)}–
                        {formatTime(item.end_time)}
                      </p>
                      <p className="hint">
                        {APPLICATION_STATUS_LABELS[item.status as ApplicationStatus] ?? item.status}
                      </p>
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      );
    }
  }

  if (jobsState.status === "loading") {
    return <p className="status">Загрузка…</p>;
  }

  if (jobsState.status === "error") {
    return (
      <section className="card">
        <p className="error">{jobsState.message}</p>
        <button type="button" className="btn secondary" onClick={() => void loadJobs()}>
          Повторить
        </button>
      </section>
    );
  }

  if (jobsState.items.length === 0) {
    return (
      <section className="card">
        <h2>Пожаловаться</h2>
        <p className="hint">Нет заявок с принятыми откликами для жалобы.</p>
      </section>
    );
  }

  return (
    <section className="card">
      <h2>Пожаловаться</h2>
      <p className="hint">Выберите заявку, по которой хотите подать жалобу на работника.</p>
      <ul className="applications-list">
        {jobsState.items.map((job) => (
          <li key={job.id} className="application-item">
            <button type="button" className="complaint-select-btn" onClick={() => void handleSelectJob(job)}>
              <strong>{job.title}</strong>
              <p className="hint">
                {formatJobRequestStatus(job.status)} · откликов: {job.applications_count}
              </p>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
