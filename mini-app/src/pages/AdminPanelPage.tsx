import { useCallback, useEffect, useState } from "react";
import {
  getAdminAnalytics,
  getAdminAuditLog,
  getAdminStats,
  listPendingEmployers,
  rejectEmployer,
  verifyEmployer,
  type AdminAnalytics,
  type AdminAuditEntry,
  type AdminStats,
  type PendingEmployer,
} from "../api/client";
import { triggerHaptic, triggerNotificationHaptic } from "../lib/telegram";

type AdminTab = "stats" | "verifications" | "audit";

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
};

const ENTITY_TYPE_LABELS: Record<string, string> = {
  job_request: "заявка",
  application: "отклик",
  employer_profile: "работодатель",
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

function VerificationsTab({ initData }: { initData: string }) {
  const [employers, setEmployers] = useState<PendingEmployer[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const items = await listPendingEmployers(initData);
      setEmployers(items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить список");
    } finally {
      setLoading(false);
    }
  }, [initData]);

  useEffect(() => {
    void load();
  }, [load]);

  async function handleVerify(employerId: string) {
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

  async function handleReject(employerId: string) {
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

  if (loading) {
    return <p className="status">Загрузка верификаций…</p>;
  }

  return (
    <div className="admin-verifications">
      {error ? <p className="error">{error}</p> : null}
      {employers.length === 0 ? (
        <p className="hint">Нет работодателей, ожидающих верификации.</p>
      ) : (
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
                    void handleVerify(employer.id);
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
                    void handleReject(employer.id);
                  }}
                >
                  Отклонить
                </button>
              </div>
            </li>
          ))}
        </ul>
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
