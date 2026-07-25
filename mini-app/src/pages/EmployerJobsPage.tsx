import { useEffect, useState } from "react";
import {
  createEmployerComplaint,
  formatJobRequestStatus,
  listEmployerComplaintApplications,
  listEmployerJobs,
  updateJobStatus,
  type ComplaintViolationType,
  type EmployerComplaintApplication,
  type JobRequest,
  type JobRequestStatus,
} from "../api/client";
import { ComplaintForm, ComplaintSuccess } from "../components/ComplaintForm";
import { formatHourlyRate } from "../utils/formatRate";

type EmployerJobsPageProps = {
  initData: string;
  onCreateClick?: () => void;
  reloadKey?: number;
  variant?: "current" | "history";
};

type JobsState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; jobs: JobRequest[] };

type ApplicantsState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; items: EmployerComplaintApplication[] };

type View = "list" | "job-detail" | "complaint" | "complaint-success";

const DRAFTS_COLLAPSED_KEY = "employer_jobs_drafts_collapsed";

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

function parseShiftDate(iso: string): Date | null {
  const [year, month, day] = iso.split("-").map(Number);
  if (!year || !month || !day) {
    return null;
  }
  return new Date(year, month - 1, day);
}

function startOfToday(): Date {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return today;
}

/** Current jobs: drafts + active with today/future shifts (defensive if API lag). */
function isCurrentJob(job: JobRequest): boolean {
  if (job.status === "draft") {
    return true;
  }
  if (job.status !== "active") {
    return false;
  }
  if (job.shift_slots.length === 0) {
    return true;
  }
  const today = startOfToday();
  return job.shift_slots.some((slot) => {
    const shiftDate = parseShiftDate(slot.shift_date);
    return shiftDate !== null && shiftDate >= today;
  });
}

function loadDraftsCollapsed(): boolean {
  if (typeof localStorage === "undefined") {
    return false;
  }
  try {
    return localStorage.getItem(DRAFTS_COLLAPSED_KEY) === "1";
  } catch {
    return false;
  }
}

function saveDraftsCollapsed(collapsed: boolean): void {
  if (typeof localStorage === "undefined") {
    return;
  }
  try {
    localStorage.setItem(DRAFTS_COLLAPSED_KEY, collapsed ? "1" : "0");
  } catch {
    // ignore quota / private mode
  }
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

export function EmployerJobsPage({
  initData,
  onCreateClick,
  reloadKey = 0,
  variant = "current",
}: EmployerJobsPageProps) {
  const [state, setState] = useState<JobsState>({ status: "loading" });
  const [applicantsState, setApplicantsState] = useState<ApplicantsState>({ status: "idle" });
  const [view, setView] = useState<View>("list");
  const [selectedJob, setSelectedJob] = useState<JobRequest | null>(null);
  const [selectedApplication, setSelectedApplication] = useState<EmployerComplaintApplication | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [busyJobId, setBusyJobId] = useState<string | null>(null);
  const [draftsCollapsed, setDraftsCollapsed] = useState(loadDraftsCollapsed);

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

  async function handleOpenJob(job: JobRequest) {
    setSelectedJob(job);
    setView("job-detail");
    setApplicantsState({ status: "loading" });
    try {
      const data = await listEmployerComplaintApplications(initData, job.id);
      setApplicantsState({ status: "ready", items: data.items });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Не удалось загрузить отклики";
      setApplicantsState({ status: "error", message });
    }
  }

  function handleBackToList() {
    setSelectedJob(null);
    setSelectedApplication(null);
    setApplicantsState({ status: "idle" });
    setView("list");
  }

  function handleBackToJobDetail() {
    setSelectedApplication(null);
    setView("job-detail");
  }

  function handleToggleDrafts() {
    setDraftsCollapsed((prev) => {
      const next = !prev;
      saveDraftsCollapsed(next);
      return next;
    });
  }

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
      if (selectedJob?.id === jobId) {
        setSelectedJob(updated);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Не удалось обновить статус";
      setActionError(message);
    } finally {
      setBusyJobId(null);
    }
  }

  async function handleSubmitComplaint(data: {
    violationType: ComplaintViolationType;
    description: string;
  }) {
    if (!selectedApplication) {
      return;
    }
    await createEmployerComplaint(initData, {
      application_id: selectedApplication.id,
      violation_type: data.violationType,
      description: data.description || null,
    });
    setView("complaint-success");
  }

  function renderJobItem(job: JobRequest, allowActions: boolean) {
    return (
      <li key={job.id} className="job-item">
        <button type="button" className="complaint-select-btn" onClick={() => void handleOpenJob(job)}>
          <div className="job-item-header">
            <strong>{job.title}</strong>
            <span className={`status-badge status-${job.status}`}>
              {formatJobRequestStatus(job.status)}
            </span>
          </div>
          <p className="hint">
            {job.category_name ?? "Категория"} · {job.metro_station_name ?? "Метро"} ·{" "}
            {formatHourlyRate(job.hourly_rate)} · {job.workers_needed} чел.
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
        </button>
        {allowActions ? (
          <div className="job-actions">
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
        ) : null}
      </li>
    );
  }

  if (view === "complaint-success") {
    return (
      <ComplaintSuccess
        doneLabel="К заявке"
        onDone={() => {
          setSelectedApplication(null);
          setView("job-detail");
        }}
      />
    );
  }

  if (view === "complaint" && selectedApplication) {
    return (
      <ComplaintForm
        title="Пожаловаться на работника"
        hints={[
          `${selectedApplication.job_title} · ${workerLabel(selectedApplication)}`,
          `${formatDate(selectedApplication.shift_date)} ${formatTime(selectedApplication.start_time)}–${formatTime(selectedApplication.end_time)}`,
        ]}
        descriptionRequired={false}
        onBack={handleBackToJobDetail}
        onSubmit={handleSubmitComplaint}
      />
    );
  }

  if (view === "job-detail" && selectedJob) {
    const allowActions = isCurrentJob(selectedJob);
    return (
      <section className="card jobs-list-card">
        <button type="button" className="link-btn back-link" onClick={handleBackToList}>
          ← Назад
        </button>
        <div className="job-item-header">
          <h2>{selectedJob.title}</h2>
          <span className={`status-badge status-${selectedJob.status}`}>
            {formatJobRequestStatus(selectedJob.status)}
          </span>
        </div>
        <p className="hint">
          {selectedJob.category_name ?? "Категория"} · {selectedJob.metro_station_name ?? "Метро"} ·{" "}
          {formatHourlyRate(selectedJob.hourly_rate)} · {selectedJob.workers_needed} чел.
        </p>
        {selectedJob.shift_slots.length > 0 ? (
          <ul className="job-shifts">
            {selectedJob.shift_slots.map((slot) => (
              <li key={slot.id}>
                {formatDate(slot.shift_date)} {formatTime(slot.start_time)}–{formatTime(slot.end_time)}
              </li>
            ))}
          </ul>
        ) : null}
        {allowActions ? (
          <div className="job-actions">
            {selectedJob.status === "draft" ? (
              <button
                type="button"
                className="btn"
                disabled={busyJobId === selectedJob.id}
                onClick={() => void handleStatusChange(selectedJob.id, "active")}
              >
                Опубликовать
              </button>
            ) : null}
            {selectedJob.status === "draft" || selectedJob.status === "active" ? (
              <button
                type="button"
                className="btn secondary"
                disabled={busyJobId === selectedJob.id}
                onClick={() => void handleStatusChange(selectedJob.id, "cancelled")}
              >
                Отменить
              </button>
            ) : null}
          </div>
        ) : null}

        <h3>Принятые работники</h3>
        {applicantsState.status === "loading" ? (
          <p className="status">Загрузка откликов…</p>
        ) : applicantsState.status === "error" ? (
          <p className="error">{applicantsState.message}</p>
        ) : applicantsState.status === "ready" && applicantsState.items.length === 0 ? (
          <p className="hint">Нет принятых откликов для жалобы по этой заявке.</p>
        ) : applicantsState.status === "ready" ? (
          <ul className="applications-list">
            {applicantsState.items.map((item) => (
              <li key={item.id} className="application-item application-item-employer">
                <div className="application-item-body">
                  <strong>{workerLabel(item)}</strong>
                  <p>
                    {formatDate(item.shift_date)} {formatTime(item.start_time)}–{formatTime(item.end_time)}
                  </p>
                </div>
                <button
                  type="button"
                  className="btn secondary small-btn"
                  onClick={() => {
                    setSelectedApplication(item);
                    setView("complaint");
                  }}
                >
                  Пожаловаться
                </button>
              </li>
            ))}
          </ul>
        ) : null}
      </section>
    );
  }

  if (state.status === "loading") {
    return <p className="status">Загрузка заявок…</p>;
  }

  if (state.status === "error") {
    return (
      <section className="card">
        <p className="error">{state.message}</p>
        {onCreateClick && variant === "current" ? (
          <button type="button" className="btn secondary" onClick={onCreateClick}>
            Создать заявку
          </button>
        ) : null}
      </section>
    );
  }

  const { jobs } = state;
  const visibleJobs =
    variant === "history" ? jobs.filter((job) => !isCurrentJob(job)) : jobs.filter(isCurrentJob);
  const draftJobs = visibleJobs.filter((job) => job.status === "draft");
  const activeJobs = visibleJobs.filter((job) => job.status !== "draft");
  const isHistory = variant === "history";

  return (
    <section className="card jobs-list-card">
      <div className="profile-header">
        <h2>{isHistory ? "История" : "Мои заявки"}</h2>
        {!isHistory && onCreateClick ? (
          <button type="button" className="btn" onClick={onCreateClick}>
            + Создать
          </button>
        ) : null}
      </div>

      {actionError ? <p className="error">{actionError}</p> : null}

      {visibleJobs.length === 0 ? (
        <p className="hint">
          {isHistory
            ? "В истории пока нет заявок."
            : "Заявок пока нет. Создайте первую."}
        </p>
      ) : isHistory ? (
        <ul className="jobs-list">{visibleJobs.map((job) => renderJobItem(job, false))}</ul>
      ) : (
        <>
          {draftJobs.length > 0 ? (
            <div className="jobs-drafts-block">
              <div className="jobs-section-header">
                {!draftsCollapsed ? (
                  <h3 className="vacancy-section-title">Черновики ({draftJobs.length})</h3>
                ) : (
                  <span />
                )}
                <button type="button" className="link-btn" onClick={handleToggleDrafts}>
                  {draftsCollapsed
                    ? `Показать черновики (${draftJobs.length})`
                    : "Скрыть черновики"}
                </button>
              </div>
              {!draftsCollapsed ? (
                <ul className="jobs-list">
                  {draftJobs.map((job) => renderJobItem(job, true))}
                </ul>
              ) : null}
            </div>
          ) : null}

          {activeJobs.length > 0 ? (
            <div className="jobs-active-block">
              {draftJobs.length > 0 ? (
                <h3 className="vacancy-section-title">Активные</h3>
              ) : null}
              <ul className="jobs-list">
                {activeJobs.map((job) => renderJobItem(job, true))}
              </ul>
            </div>
          ) : null}

          {draftJobs.length > 0 && activeJobs.length === 0 && draftsCollapsed ? (
            <p className="hint">Черновики скрыты. Активных заявок нет.</p>
          ) : null}
        </>
      )}
    </section>
  );
}
