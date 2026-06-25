import { useCallback, useEffect, useState } from "react";
import {
  blockModerationUser,
  dismissModerationUser,
  formatComplaintStatus,
  formatJobRequestStatus,
  getAdminAnalytics,
  getAdminAuditLog,
  getAdminStats,
  getModerationUserDetail,
  listAdminApplicationViolations,
  listAdminBlockedUsers,
  listAdminEmployers,
  listAdminJobs,
  listAdminWorkers,
  listModerationQueue,
  listPendingEmployers,
  rejectEmployer,
  unblockModerationUser,
  verifyEmployer,
  type AdminAnalytics,
  type AdminAuditEntry,
  type AdminBlockedUserListItem,
  type AdminComplaintListItem,
  type AdminEmployerListItem,
  type AdminJobListItem,
  type AdminStats,
  type AdminWorkerListItem,
  type ModerationQueueEntry,
  type ModerationUserDetail,
  type PendingEmployer,
} from "../api/client";
import { triggerHaptic, triggerNotificationHaptic } from "../lib/telegram";

type AdminTab = "stats" | "verifications" | "moderation" | "audit";

type StatDrillDown = "workers" | "employers" | "jobs" | "blocked" | "complaints";

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
  "moderation.user_block": "Пользователь заблокирован",
  "moderation.user_unblock": "Пользователь разблокирован",
  "moderation.review_dismiss": "Review модерации отклонён",
  "complaint.created": "Жалоба по заявке создана",
  "complaint.status_change": "Статус жалобы изменён",
};

const ENTITY_TYPE_LABELS: Record<string, string> = {
  job_request: "заявка",
  application: "отклик",
  employer_profile: "работодатель",
  application_complaint: "жалоба",
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

function formatTelegramUser(username: string | null, telegramId: number): string {
  return username ? `@${username}` : String(telegramId);
}

type StatCardButtonProps = {
  value: number;
  label: string;
  warn?: boolean;
  onClick: () => void;
};

function StatCardButton({ value, label, warn, onClick }: StatCardButtonProps) {
  return (
    <button
      type="button"
      className={`stat-card stat-card-btn${warn ? " stat-card-warn" : ""}`}
      onClick={() => {
        triggerHaptic("light");
        onClick();
      }}
    >
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
    </button>
  );
}

type StatDrillDownViewProps = {
  initData: string;
  drillDown: StatDrillDown;
  onBack: () => void;
};

function StatDrillDownView({ initData, drillDown, onBack }: StatDrillDownViewProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [workers, setWorkers] = useState<AdminWorkerListItem[]>([]);
  const [employers, setEmployers] = useState<AdminEmployerListItem[]>([]);
  const [jobs, setJobs] = useState<AdminJobListItem[]>([]);
  const [blocked, setBlocked] = useState<AdminBlockedUserListItem[]>([]);
  const [complaints, setComplaints] = useState<AdminComplaintListItem[]>([]);
  const [total, setTotal] = useState(0);

  const titles: Record<StatDrillDown, string> = {
    workers: "Работники",
    employers: "Работодатели",
    jobs: "Заявки",
    blocked: "Заблокированные",
    complaints: "Нарушения по заявкам",
  };

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (drillDown === "workers") {
        const data = await listAdminWorkers(initData, { limit: 50 });
        setWorkers(data.items);
        setTotal(data.total);
      } else if (drillDown === "employers") {
        const data = await listAdminEmployers(initData, { limit: 50 });
        setEmployers(data.items);
        setTotal(data.total);
      } else if (drillDown === "jobs") {
        const data = await listAdminJobs(initData, { limit: 50 });
        setJobs(data.items);
        setTotal(data.total);
      } else if (drillDown === "blocked") {
        const data = await listAdminBlockedUsers(initData, { limit: 50 });
        setBlocked(data.items);
        setTotal(data.total);
      } else {
        const data = await listAdminApplicationViolations(initData, { limit: 50 });
        setComplaints(data.items);
        setTotal(data.total);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить список");
    } finally {
      setLoading(false);
    }
  }, [drillDown, initData]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="admin-drilldown">
      <div className="admin-drilldown-header">
        <button
          type="button"
          className="btn btn-sm"
          onClick={() => {
            triggerHaptic("light");
            onBack();
          }}
        >
          ← Статистика
        </button>
        <h3>{titles[drillDown]}</h3>
        {!loading && !error ? <p className="hint">Всего: {total}</p> : null}
      </div>
      {loading ? <p className="status">Загрузка…</p> : null}
      {error ? <p className="error">{error}</p> : null}
      {!loading && !error && drillDown === "workers" ? (
        workers.length === 0 ? (
          <p className="hint">Работников пока нет.</p>
        ) : (
          <ul className="admin-list">
            {workers.map((worker) => (
              <li key={worker.id} className="admin-list-item">
                <div className="admin-list-main">
                  <strong>
                    {worker.first_name} {worker.last_name}
                  </strong>
                  <span className="hint">
                    TG: {formatTelegramUser(worker.username, worker.telegram_id)}
                    {" · "}
                    {worker.verified ? "верифицирован" : "не верифицирован"}
                    {" · "}
                    {worker.city}
                  </span>
                  <span className="hint">{formatDateTime(worker.created_at)}</span>
                </div>
              </li>
            ))}
          </ul>
        )
      ) : null}
      {!loading && !error && drillDown === "employers" ? (
        employers.length === 0 ? (
          <p className="hint">Работодателей пока нет.</p>
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
                    TG: {formatTelegramUser(employer.username, employer.telegram_id)}
                    {" · "}
                    {employer.verified ? "верифицирован" : "не верифицирован"}
                    {" · "}
                    {formatDateTime(employer.created_at)}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )
      ) : null}
      {!loading && !error && drillDown === "jobs" ? (
        jobs.length === 0 ? (
          <p className="hint">Заявок пока нет.</p>
        ) : (
          <ul className="admin-list">
            {jobs.map((job) => (
              <li key={job.id} className="admin-list-item">
                <div className="admin-list-main">
                  <strong>{job.title}</strong>
                  <span className="hint">{job.company_name}</span>
                  <span className="hint">
                    {formatJobRequestStatus(job.status)}
                    {" · "}
                    {job.hourly_rate} ₽/ч
                    {" · "}
                    {formatDateTime(job.created_at)}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )
      ) : null}
      {!loading && !error && drillDown === "blocked" ? (
        blocked.length === 0 ? (
          <p className="hint">Заблокированных пользователей нет.</p>
        ) : (
          <ul className="admin-list">
            {blocked.map((user) => (
              <li key={user.telegram_id} className="admin-list-item">
                <div className="admin-list-main">
                  <strong>{user.display_name ?? formatTelegramUser(user.username, user.telegram_id)}</strong>
                  <span className="hint">
                    TG: {formatTelegramUser(user.username, user.telegram_id)}
                    {" · "}
                    {user.role}
                  </span>
                  <span className="hint">{formatDateTime(user.created_at)}</span>
                </div>
              </li>
            ))}
          </ul>
        )
      ) : null}
      {!loading && !error && drillDown === "complaints" ? (
        complaints.length === 0 ? (
          <p className="hint">Жалоб по заявкам пока нет.</p>
        ) : (
          <ul className="admin-list">
            {complaints.map((item) => (
              <li key={item.id} className="admin-list-item">
                <div className="admin-list-main">
                  <strong>{item.violation_type_label}</strong>
                  <span className="hint">
                    {item.job_title}
                    {item.company_name ? ` · ${item.company_name}` : ""}
                  </span>
                  <span className="hint">
                    {formatComplaintStatus(item.status)}
                    {" · "}
                    {item.reporter_role === "worker" ? "от работника" : "от работодателя"}
                    {" · "}
                    {formatDateTime(item.created_at)}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )
      ) : null}
    </div>
  );
}

function StatsTab({
  initData,
  onNavigateTab,
}: {
  initData: string;
  onNavigateTab: (tab: AdminTab) => void;
}) {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [analytics, setAnalytics] = useState<AdminAnalytics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [drillDown, setDrillDown] = useState<StatDrillDown | null>(null);

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

  if (drillDown !== null) {
    return (
      <StatDrillDownView
        initData={initData}
        drillDown={drillDown}
        onBack={() => setDrillDown(null)}
      />
    );
  }

  return (
    <div className="admin-stats">
      <div className="stat-grid">
        <StatCardButton
          value={stats.workers_count}
          label="Работники"
          onClick={() => setDrillDown("workers")}
        />
        <StatCardButton
          value={stats.employers_count}
          label="Работодатели"
          onClick={() => setDrillDown("employers")}
        />
        <StatCardButton
          value={stats.jobs_count}
          label="Заявки"
          onClick={() => setDrillDown("jobs")}
        />
        <StatCardButton
          value={stats.pending_verifications}
          label="На верификации"
          warn
          onClick={() => onNavigateTab("verifications")}
        />
        {typeof stats.moderation_flagged_users === "number" ? (
          <StatCardButton
            value={stats.moderation_flagged_users}
            label="На модерации"
            warn
            onClick={() => onNavigateTab("moderation")}
          />
        ) : null}
        {typeof stats.users_blocked === "number" ? (
          <StatCardButton
            value={stats.users_blocked}
            label="Заблокированы"
            onClick={() => setDrillDown("blocked")}
          />
        ) : null}
        {typeof stats.violations_total === "number" ? (
          <StatCardButton
            value={stats.violations_total}
            label="Нарушения"
            onClick={() => setDrillDown("complaints")}
          />
        ) : null}
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

function ModerationTab({ initData }: { initData: string }) {
  const [queue, setQueue] = useState<ModerationQueueEntry[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [detail, setDetail] = useState<ModerationUserDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);

  const loadQueue = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const items = await listModerationQueue(initData);
      setQueue(items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось загрузить очередь модерации");
    } finally {
      setLoading(false);
    }
  }, [initData]);

  const loadDetail = useCallback(
    async (telegramId: number) => {
      setDetailLoading(true);
      setError(null);
      try {
        const data = await getModerationUserDetail(initData, telegramId);
        setDetail(data);
        setSelectedId(telegramId);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Не удалось загрузить детали");
      } finally {
        setDetailLoading(false);
      }
    },
    [initData],
  );

  useEffect(() => {
    void loadQueue();
  }, [loadQueue]);

  async function runAction(
    telegramId: number,
    action: "block" | "unblock" | "dismiss",
  ) {
    setBusyId(telegramId);
    setError(null);
    try {
      if (action === "block") {
        await blockModerationUser(initData, telegramId);
      } else if (action === "unblock") {
        await unblockModerationUser(initData, telegramId);
      } else {
        await dismissModerationUser(initData, telegramId);
      }
      triggerNotificationHaptic("success");
      setSelectedId(null);
      setDetail(null);
      await loadQueue();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось выполнить действие");
      triggerNotificationHaptic("error");
    } finally {
      setBusyId(null);
    }
  }

  if (loading) {
    return <p className="status">Загрузка модерации…</p>;
  }

  return (
    <div className="admin-moderation">
      {error ? <p className="error">{error}</p> : null}

      {selectedId !== null && detail ? (
        <section className="admin-subsection">
          <button
            type="button"
            className="btn btn-sm"
            onClick={() => {
              triggerHaptic("light");
              setSelectedId(null);
              setDetail(null);
            }}
          >
            ← К очереди
          </button>
          <h3>
            {detail.username ? `@${detail.username}` : detail.telegram_id}
            {detail.is_blocked ? " · заблокирован" : " · активен"}
          </h3>
          <p className="hint">
            Нарушений: {detail.violation_count}
            {detail.flagged_at ? ` · review ${formatDateTime(detail.flagged_at)}` : null}
          </p>
          {detailLoading ? (
            <p className="status">Загрузка…</p>
          ) : detail.violations.length === 0 ? (
            <p className="hint">Нарушений нет.</p>
          ) : (
            <ul className="admin-audit-list">
              {detail.violations.map((item) => (
                <li key={item.id}>
                  {formatDateTime(item.created_at)} · {item.source} · поле {item.field}
                  <br />
                  term: {item.matched_term}
                  {item.category ? ` (${item.category})` : null}
                  <br />
                  {item.raw_snippet.slice(0, 200)}
                </li>
              ))}
            </ul>
          )}
          <div className="admin-list-actions">
            {!detail.is_blocked ? (
              <>
                <button
                  type="button"
                  className="btn btn-sm btn-danger"
                  disabled={busyId === detail.telegram_id}
                  onClick={() => {
                    triggerHaptic("light");
                    void runAction(detail.telegram_id, "block");
                  }}
                >
                  Заблокировать
                </button>
                {detail.flagged_at ? (
                  <button
                    type="button"
                    className="btn btn-sm"
                    disabled={busyId === detail.telegram_id}
                    onClick={() => {
                      triggerHaptic("light");
                      void runAction(detail.telegram_id, "dismiss");
                    }}
                  >
                    Отклонить review
                  </button>
                ) : null}
              </>
            ) : (
              <button
                type="button"
                className="btn btn-sm"
                disabled={busyId === detail.telegram_id}
                onClick={() => {
                  triggerHaptic("light");
                  void runAction(detail.telegram_id, "unblock");
                }}
              >
                Разблокировать
              </button>
            )}
          </div>
        </section>
      ) : queue.length === 0 ? (
        <p className="hint">Очередь модерации пуста.</p>
      ) : (
        <ul className="admin-list">
          {queue.map((entry) => (
            <li key={entry.telegram_id} className="admin-list-item">
              <div className="admin-list-main">
                <strong>
                  {entry.username ? `@${entry.username}` : entry.telegram_id}
                </strong>
                <span className="hint">
                  {entry.violation_count} наруш.
                  {" · "}
                  {entry.is_blocked ? "заблокирован" : "активен"}
                  {" · "}
                  review {formatDateTime(entry.flagged_at)}
                </span>
              </div>
              <div className="admin-list-actions">
                <button
                  type="button"
                  className="btn btn-sm"
                  disabled={busyId === entry.telegram_id}
                  onClick={() => {
                    triggerHaptic("light");
                    void loadDetail(entry.telegram_id);
                  }}
                >
                  Детали
                </button>
                {!entry.is_blocked ? (
                  <>
                    <button
                      type="button"
                      className="btn btn-sm btn-danger"
                      disabled={busyId === entry.telegram_id}
                      onClick={() => {
                        triggerHaptic("light");
                        void runAction(entry.telegram_id, "block");
                      }}
                    >
                      Заблокировать
                    </button>
                    <button
                      type="button"
                      className="btn btn-sm"
                      disabled={busyId === entry.telegram_id}
                      onClick={() => {
                        triggerHaptic("light");
                        void runAction(entry.telegram_id, "dismiss");
                      }}
                    >
                      Отклонить
                    </button>
                  </>
                ) : (
                  <button
                    type="button"
                    className="btn btn-sm"
                    disabled={busyId === entry.telegram_id}
                    onClick={() => {
                      triggerHaptic("light");
                      void runAction(entry.telegram_id, "unblock");
                    }}
                  >
                    Разблокировать
                  </button>
                )}
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
          className={`nav-btn${tab === "moderation" ? " active" : ""}`}
          onClick={() => {
            triggerHaptic("light");
            setTab("moderation");
          }}
        >
          Модерация
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

      {tab === "stats" ? (
        <StatsTab initData={initData} onNavigateTab={setTab} />
      ) : null}
      {tab === "verifications" ? <VerificationsTab initData={initData} /> : null}
      {tab === "moderation" ? <ModerationTab initData={initData} /> : null}
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
