import { useCallback, useEffect, useState } from "react";
import {
  getAdminAnalytics,
  getAdminAuditLog,
  getAdminStats,
  listPendingEmployers,
  listPendingWorkers,
  rejectEmployer,
  rejectWorker,
  verifyEmployer,
  verifyWorker,
  type AdminAnalytics,
  type AdminAuditEntry,
  type AdminStats,
  type PendingEmployer,
  type PendingWorker,
} from "../api/client";
import { triggerHaptic, triggerNotificationHaptic } from "../lib/telegram";

type AdminTab = "stats" | "verifications" | "audit";
type VerificationSubTab = "employers" | "workers";

type AdminPanelPageProps = {
  initData: string;
  initialTab?: AdminTab;
};

const AUDIT_ACTION_LABELS: Record<string, string> = {
  "job.create": "Создана заявка",
  "job.status_change": "Изменён статус заявки",
  "application.pending": "Новый отклик",
  "application.accepted": "Отклик принят",
  "application.rejected": "Отклик отклонён",
  "application.cancelled_by_worker": "Отклик отменён работником",
  "application.cancelled_by_employer": "Отклик отменён работодателем",
  "employer.verify": "Работодатель верифицирован",
  "employer.reject": "Работодатель отклонён",
  "worker.verify": "Работник верифицирован",
  "worker.reject": "Работник отклонён",
};

const ENTITY_TYPE_LABELS: Record<string, string> = {
  job_request: "заявка",
  application: "отклик",
  employer_profile: "работодатель",
  employer: "работодатель",
  worker: "работник",
  user: "пользователь",
};

function formatAuditEntry(entry: AdminAuditEntry): string {
  const date = new Date(entry.created_at);
  const ts = Number.isNaN(date.getTime())
    ? "—"
    : date.toLocaleString("ru-RU", {
        day: "2-digit",
        month: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      });
  const action = AUDIT_ACTION_LABELS[entry.action] ?? entry.action;
  const entity = ENTITY_TYPE_LABELS[entry.entity_type] ?? entry.entity_type;
  const shortId = entry.entity_id.slice(0, 8);
  return `${ts} — ${action} (${entity} ${shortId}…)`;
}

function formatDateTime(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return iso;
  }
  return date.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function StatsTab({ initData }: { initData: string }) {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [analytics, setAnalytics] = useState<AdminAnalytics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [statsData, analyticsData] = await Promise.all([
          getAdminStats(initData),
          getAdminAnalytics(initData),
        ]);
        if (!cancelled) {
          setStats(statsData);
          setAnalytics(analyticsData);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Не удалось загрузить статистику");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [initData]);

  if (loading) {
    return <p className="status">Загрузка статистики…</p>;
  }
  if (error) {
    return <p className="error">{error}</p>;
  }
  if (!stats || !analytics) {
    return null;
  }

  return (
    <div className="admin-stats">
      <div className="stat-grid">
        <div className="stat-card">
          <span className="stat-value">{stats.workers_count}</span>
          <span className="stat-label">Работники</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{stats.employers_count}</span>
          <span className="stat-label">Работодатели</span>
        </div>
        <div className="stat-card">
          <span className="stat-value">{stats.jobs_count}</span>
          <span className="stat-label">Заявки</span>
        </div>
        <div className="stat-card stat-card-warn">
          <span className="stat-value">{stats.pending_verifications}</span>
          <span className="stat-label">На верификации</span>
        </div>
      </div>

      {Object.keys(analytics.jobs_by_status).length > 0 ? (
        <section className="admin-subsection">
          <h3>Заявки по статусам</h3>
          <ul className="admin-kv-list">
            {Object.entries(analytics.jobs_by_status).map(([status, count]) => (
              <li key={status}>
                <span>{status}</span>
                <strong>{count}</strong>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {Object.keys(analytics.applications_by_status).length > 0 ? (
        <section className="admin-subsection">
          <h3>Отклики по статусам</h3>
          <ul className="admin-kv-list">
            {Object.entries(analytics.applications_by_status).map(([status, count]) => (
              <li key={status}>
                <span>{status}</span>
                <strong>{count}</strong>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}

function EmployerVerificationsList({
  employers,
  busyId,
  onVerify,
  onReject,
}: {
  employers: PendingEmployer[];
  busyId: string | null;
  onVerify: (id: string) => void;
  onReject: (id: string) => void;
}) {
  if (employers.length === 0) {
    return <p className="hint">Нет компаний, ожидающих верификации.</p>;
  }

  return (
    <ul className="admin-list">
      {employers.map((employer) => (
        <li key={employer.id} className="admin-list-item">
          <div className="admin-list-main">
            <strong>{employer.company_name}</strong>
            {employer.contact_person ? (
              <span className="hint">{employer.contact_person}</span>
            ) : null}
            {employer.contact_phone ? (
              <span className="hint">{employer.contact_phone}</span>
            ) : null}
            <span className="hint">
              TG: {employer.username ? `@${employer.username}` : employer.telegram_id}
              {" · "}
              {formatDateTime(employer.created_at)}
            </span>
          </div>
          <div className="admin-list-actions">
            <button
              type="button"
              className="btn btn-sm"
              disabled={busyId === employer.id}
              onClick={() => {
                triggerHaptic("light");
                onVerify(employer.id);
              }}
            >
              Верифицировать
            </button>
            <button
              type="button"
              className="btn btn-sm btn-danger"
              disabled={busyId === employer.id}
              onClick={() => {
                triggerHaptic("light");
                onReject(employer.id);
              }}
            >
              Отклонить
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}

function WorkerVerificationsList({
  workers,
  busyId,
  onVerify,
  onReject,
}: {
  workers: PendingWorker[];
  busyId: string | null;
  onVerify: (id: string) => void;
  onReject: (id: string) => void;
}) {
  if (workers.length === 0) {
    return <p className="hint">Нет работников, ожидающих верификации.</p>;
  }

  return (
    <ul className="admin-list">
      {workers.map((worker) => (
        <li key={worker.id} className="admin-list-item">
          <div className="admin-list-main">
            <strong>
              {worker.first_name} {worker.last_name}
            </strong>
            <span className="hint">
              {worker.age} лет
              {worker.metro_station_name ? ` · ${worker.metro_station_name}` : ""}
            </span>
            {worker.categories.length > 0 ? (
              <span className="hint">{worker.categories.join(", ")}</span>
            ) : null}
            <span className="hint">
              TG: {worker.username ? `@${worker.username}` : worker.telegram_id}
              {" · "}
              {formatDateTime(worker.created_at)}
            </span>
          </div>
          <div className="admin-list-actions">
            <button
              type="button"
              className="btn btn-sm"
              disabled={busyId === worker.id}
              onClick={() => {
                triggerHaptic("light");
                onVerify(worker.id);
              }}
            >
              Верифицировать
            </button>
            <button
              type="button"
              className="btn btn-sm btn-danger"
              disabled={busyId === worker.id}
              onClick={() => {
                triggerHaptic("light");
                onReject(worker.id);
              }}
            >
              Отклонить
            </button>
          </div>
        </li>
      ))}
    </ul>
  );
}

function VerificationsTab({ initData }: { initData: string }) {
  const [subTab, setSubTab] = useState<VerificationSubTab>("employers");
  const [employers, setEmployers] = useState<PendingEmployer[]>([]);
  const [workers, setWorkers] = useState<PendingWorker[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [employerItems, workerItems] = await Promise.all([
        listPendingEmployers(initData),
        listPendingWorkers(initData),
      ]);
      setEmployers(employerItems);
      setWorkers(workerItems);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить список");
    } finally {
      setLoading(false);
    }
  }, [initData]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleVerifyEmployer(employerId: string) {
    setBusyId(employerId);
    setError(null);
    try {
      await verifyEmployer(initData, employerId);
      triggerNotificationHaptic("success");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось верифицировать");
      triggerNotificationHaptic("error");
    } finally {
      setBusyId(null);
    }
  }

  async function handleRejectEmployer(employerId: string) {
    setBusyId(employerId);
    setError(null);
    try {
      await rejectEmployer(initData, employerId);
      triggerNotificationHaptic("success");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось отклонить");
      triggerNotificationHaptic("error");
    } finally {
      setBusyId(null);
    }
  }

  async function handleVerifyWorker(workerId: string) {
    setBusyId(workerId);
    setError(null);
    try {
      await verifyWorker(initData, workerId);
      triggerNotificationHaptic("success");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось верифицировать");
      triggerNotificationHaptic("error");
    } finally {
      setBusyId(null);
    }
  }

  async function handleRejectWorker(workerId: string) {
    setBusyId(workerId);
    setError(null);
    try {
      await rejectWorker(initData, workerId);
      triggerNotificationHaptic("success");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось отклонить");
      triggerNotificationHaptic("error");
    } finally {
      setBusyId(null);
    }
  }

  if (loading) {
    return <p className="status">Загрузка верификаций…</p>;
  }

  return (
    <div className="admin-verifications">
      <nav className="app-nav admin-subtabs">
        <button
          type="button"
          className={`nav-btn${subTab === "employers" ? " active" : ""}`}
          onClick={() => {
            triggerHaptic("light");
            setSubTab("employers");
          }}
        >
          Компании ({employers.length})
        </button>
        <button
          type="button"
          className={`nav-btn${subTab === "workers" ? " active" : ""}`}
          onClick={() => {
            triggerHaptic("light");
            setSubTab("workers");
          }}
        >
          Работники ({workers.length})
        </button>
      </nav>

      {error ? <p className="error">{error}</p> : null}

      {subTab === "employers" ? (
        <EmployerVerificationsList
          employers={employers}
          busyId={busyId}
          onVerify={(id) => void handleVerifyEmployer(id)}
          onReject={(id) => void handleRejectEmployer(id)}
        />
      ) : (
        <WorkerVerificationsList
          workers={workers}
          busyId={busyId}
          onVerify={(id) => void handleVerifyWorker(id)}
          onReject={(id) => void handleRejectWorker(id)}
        />
      )}
    </div>
  );
}

function AuditTab({ initData }: { initData: string }) {
  const [entries, setEntries] = useState<AdminAuditEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const items = await getAdminAuditLog(initData);
        if (!cancelled) {
          setEntries(items);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Не удалось загрузить журнал");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [initData]);

  if (loading) {
    return <p className="status">Загрузка журнала…</p>;
  }
  if (error) {
    return <p className="error">{error}</p>;
  }

  return (
    <div className="admin-audit">
      {entries.length === 0 ? (
        <p className="hint">Записей пока нет.</p>
      ) : (
        <ul className="admin-audit-list">
          {entries.map((entry) => (
            <li key={entry.id}>{formatAuditEntry(entry)}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function AdminPanelPage({ initData, initialTab = "stats" }: AdminPanelPageProps) {
  const [tab, setTab] = useState<AdminTab>(initialTab);

  return (
    <section className="card admin-panel">
      <h2>Админ-панель</h2>
      <nav className="app-nav admin-tabs">
        <button
          type="button"
          className={`nav-btn${tab === "stats" ? " active" : ""}`}
          onClick={() => {
            triggerHaptic("light");
            setTab("stats");
          }}
        >
          Статистика
        </button>
        <button
          type="button"
          className={`nav-btn${tab === "verifications" ? " active" : ""}`}
          onClick={() => {
            triggerHaptic("light");
            setTab("verifications");
          }}
        >
          Верификации
        </button>
        <button
          type="button"
          className={`nav-btn${tab === "audit" ? " active" : ""}`}
          onClick={() => {
            triggerHaptic("light");
            setTab("audit");
          }}
        >
          Журнал
        </button>
      </nav>

      {tab === "stats" ? <StatsTab initData={initData} /> : null}
      {tab === "verifications" ? <VerificationsTab initData={initData} /> : null}
      {tab === "audit" ? <AuditTab initData={initData} /> : null}
    </section>
  );
}

export function AdminAccessDenied() {
  return (
    <section className="card">
      <h2>Нет доступа</h2>
      <p className="hint">Админ-панель доступна только администраторам бота.</p>
    </section>
  );
}
