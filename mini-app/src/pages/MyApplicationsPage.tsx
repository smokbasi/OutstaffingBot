import { useEffect, useState } from "react";
import {
  APPLICATION_STATUS_LABELS,
  cancelApplication,
  listMyApplications,
  type ApplicationRead,
  type ApplicationStatus,
} from "../api/client";
import { triggerHaptic } from "../lib/telegram";

type MyApplicationsPageProps = {
  initData: string;
};

type PageState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; items: ApplicationRead[] };

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

export function MyApplicationsPage({ initData }: MyApplicationsPageProps) {
  const [state, setState] = useState<PageState>({ status: "loading" });
  const [cancellingId, setCancellingId] = useState<string | null>(null);

  async function loadApplications() {
    setState({ status: "loading" });
    try {
      const data = await listMyApplications(initData);
      setState({ status: "ready", items: data.items });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Не удалось загрузить отклики";
      setState({ status: "error", message });
    }
  }

  useEffect(() => {
    void loadApplications();
  }, [initData]);

  async function handleCancel(applicationId: string) {
    setCancellingId(applicationId);
    try {
      await cancelApplication(initData, applicationId);
      triggerHaptic("light");
      await loadApplications();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Не удалось отменить отклик";
      setState({ status: "error", message });
    } finally {
      setCancellingId(null);
    }
  }

  if (state.status === "loading") {
    return <p className="status">Загрузка…</p>;
  }

  if (state.status === "error") {
    return (
      <section className="card">
        <p className="error">{state.message}</p>
        <button type="button" className="btn secondary" onClick={() => void loadApplications()}>
          Повторить
        </button>
      </section>
    );
  }

  if (state.items.length === 0) {
    return (
      <section className="card">
        <h2>Мои отклики</h2>
        <p className="hint">У вас пока нет активных откликов.</p>
      </section>
    );
  }

  return (
    <section className="card">
      <h2>Мои отклики</h2>
      <ul className="applications-list">
        {state.items.map((item) => (
          <li key={item.id} className="application-item">
            <div>
              <strong>{item.job_title}</strong>
              <p className="hint">
                {item.category_name ?? "—"} · {item.metro_station_name ?? "—"}
              </p>
              <p>
                {formatDate(item.shift_date)} {formatTime(item.start_time)}–{formatTime(item.end_time)}
              </p>
              <p className="hint">
                <span className={`status-badge status-app-${item.status}`}>
                  {APPLICATION_STATUS_LABELS[item.status as ApplicationStatus] ?? item.status}
                </span>
              </p>
            </div>
            <button
              type="button"
              className="btn secondary small-btn"
              disabled={cancellingId === item.id}
              onClick={() => void handleCancel(item.id)}
            >
              {cancellingId === item.id ? "Отмена…" : "Отменить"}
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
