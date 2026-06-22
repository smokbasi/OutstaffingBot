import { useEffect, useState } from "react";
import {
  APPLICATION_STATUS_LABELS,
  listJobApplications,
  updateEmployerApplication,
  type ApplicationStatus,
  type EmployerApplicationRead,
} from "../api/client";
import { triggerHaptic, triggerNotificationHaptic } from "../lib/telegram";
import { ContactBlock } from "../lib/contacts";

type EmployerApplicationsPageProps = {
  initData: string;
  jobId: string;
  jobTitle?: string;
  onBack: () => void;
};

type PageState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; items: EmployerApplicationRead[] };

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

export function EmployerApplicationsPage({
  initData,
  jobId,
  jobTitle,
  onBack,
}: EmployerApplicationsPageProps) {
  const [state, setState] = useState<PageState>({ status: "loading" });
  const [actionError, setActionError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function loadApplications() {
    setState({ status: "loading" });
    setActionError(null);
    try {
      const data = await listJobApplications(initData, jobId);
      setState({ status: "ready", items: data.items });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Не удалось загрузить отклики";
      setState({ status: "error", message });
    }
  }

  useEffect(() => {
    void loadApplications();
  }, [initData, jobId]);

  async function handleDecision(applicationId: string, status: "accepted" | "rejected") {
    setBusyId(applicationId);
    setActionError(null);
    try {
      const updated = await updateEmployerApplication(initData, applicationId, status);
      triggerHaptic("medium");
      triggerNotificationHaptic(status === "accepted" ? "success" : "warning");
      setState((prev) => {
        if (prev.status !== "ready") {
          return prev;
        }
        return {
          status: "ready",
          items: prev.items.map((item) => (item.id === applicationId ? updated : item)),
        };
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Не удалось обновить отклик";
      setActionError(message);
      triggerNotificationHaptic("error");
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
        <div className="form-actions">
          <button type="button" className="btn secondary" onClick={() => void loadApplications()}>
            Повторить
          </button>
          <button type="button" className="btn secondary" onClick={onBack}>
            Назад
          </button>
        </div>
      </section>
    );
  }

  const pendingCount = state.items.filter((item) => item.status === "pending").length;

  return (
    <section className="card">
      <button type="button" className="link-btn back-link" onClick={onBack}>
        ← К заявкам
      </button>
      <h2>Отклики{jobTitle ? `: ${jobTitle}` : ""}</h2>
      {pendingCount > 0 ? (
        <p className="hint">На рассмотрении: {pendingCount}</p>
      ) : null}
      {actionError ? <p className="error">{actionError}</p> : null}

      {state.items.length === 0 ? (
        <p className="hint">Откликов пока нет.</p>
      ) : (
        <ul className="applications-list employer-applications">
          {state.items.map((item) => (
            <li key={item.id} className="application-item employer-application-item">
              <div className="application-body">
                <strong>
                  {item.worker_first_name} {item.worker_last_name}
                </strong>
                <p className="hint">
                  {item.worker_age} лет
                  {item.worker_experience_months != null
                    ? ` · опыт ${item.worker_experience_months} мес.`
                    : ""}
                </p>
                <p>
                  {formatDate(item.shift_date)} {formatTime(item.start_time)}–{formatTime(item.end_time)}
                </p>
                <span className={`status-badge status-app-${item.status}`}>
                  {APPLICATION_STATUS_LABELS[item.status as ApplicationStatus] ?? item.status}
                </span>
                {item.status === "accepted" ? (
                  <ContactBlock
                    title="Контакты работника"
                    phone={item.worker_phone}
                    telegramUsername={item.worker_telegram_username}
                    telegramId={item.worker_telegram_id}
                  />
                ) : null}
              </div>
              {item.status === "pending" ? (
                <div className="application-actions">
                  <button
                    type="button"
                    className="btn small-btn"
                    disabled={busyId === item.id}
                    onClick={() => void handleDecision(item.id, "accepted")}
                  >
                    Принять
                  </button>
                  <button
                    type="button"
                    className="btn secondary small-btn"
                    disabled={busyId === item.id}
                    onClick={() => void handleDecision(item.id, "rejected")}
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
