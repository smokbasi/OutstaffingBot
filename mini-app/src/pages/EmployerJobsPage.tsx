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

export function EmployerJobsPage({ initData, onCreateClick, reloadKey = 0 }: EmployerJobsPageProps) {
  const [state, setState] = useState<JobsState>({ status: "loading" });
  const [applicantsState, setApplicantsState] = useState<ApplicantsState>({ status: "idle" });
  const [view, setView] = useState<View>("list");
  const [selectedJob, setSelectedJob] = useState<JobRequest | null>(null);
  const [selectedApplication, setSelectedApplication] = useState<EmployerComplaintApplication | null>(null);
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
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
