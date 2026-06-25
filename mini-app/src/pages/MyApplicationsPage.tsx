import { useEffect, useState } from "react";
import {
  APPLICATION_STATUS_LABELS,
  cancelApplication,
  createWorkerComplaint,
  listMyApplications,
  type ApplicationRead,
  type ApplicationStatus,
  type ComplaintViolationType,
} from "../api/client";
import { ComplaintForm, ComplaintSuccess } from "../components/ComplaintForm";
import { ContactBlock } from "../lib/contacts";

type MyApplicationsPageProps = {
  initData: string;
};

type PageState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; items: ApplicationRead[] };

type View = "list" | "detail" | "complaint" | "complaint-success";

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
  const [view, setView] = useState<View>("list");
  const [selected, setSelected] = useState<ApplicationRead | null>(null);
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

  function handleOpenDetail(item: ApplicationRead) {
    setSelected(item);
    setView("detail");
  }

  function handleBackToList() {
    setSelected(null);
    setView("list");
  }

  async function handleCancel(applicationId: string) {
    setCancellingId(applicationId);
    try {
      await cancelApplication(initData, applicationId);
      await loadApplications();
      setSelected(null);
      setView("list");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Не удалось отменить отклик";
      setState({ status: "error", message });
    } finally {
      setCancellingId(null);
    }
  }

  async function handleSubmitComplaint(data: {
    violationType: ComplaintViolationType;
    description: string;
  }) {
    if (!selected) {
      return;
    }
    await createWorkerComplaint(initData, {
      application_id: selected.id,
      violation_type: data.violationType,
      description: data.description,
    });
    setView("complaint-success");
  }

  if (state.status === "loading" && view === "list") {
    return <p className="status">Загрузка…</p>;
  }

  if (state.status === "error" && view === "list") {
    return (
      <section className="card">
        <p className="error">{state.message}</p>
        <button type="button" className="btn secondary" onClick={() => void loadApplications()}>
          Повторить
        </button>
      </section>
    );
  }

  if (view === "complaint-success") {
    return (
      <ComplaintSuccess
        doneLabel="К отклику"
        onDone={() => {
          setView("detail");
        }}
      />
    );
  }

  if (view === "complaint" && selected) {
    return (
      <ComplaintForm
        title="Пожаловаться"
        hints={[
          `${selected.job_title} · ${selected.employer_company_name ?? "Работодатель"}`,
          `${formatDate(selected.shift_date)} ${formatTime(selected.start_time)}–${formatTime(selected.end_time)}`,
        ]}
        descriptionRequired
        onBack={() => setView("detail")}
        onSubmit={handleSubmitComplaint}
      />
    );
  }

  if (view === "detail" && selected) {
    return (
      <section className="card">
        <button type="button" className="link-btn back-link" onClick={handleBackToList}>
          ← Назад
        </button>
        <h2>{selected.job_title}</h2>
        <p className="hint">
          {selected.category_name ?? "—"} · {selected.metro_station_name ?? "—"}
        </p>
        <p>
          {formatDate(selected.shift_date)} {formatTime(selected.start_time)}–{formatTime(selected.end_time)}
        </p>
        <p className="hint">
          {APPLICATION_STATUS_LABELS[selected.status as ApplicationStatus] ?? selected.status}
        </p>
        {selected.status === "accepted" ? (
          <>
            <ContactBlock
              title="Контакты работодателя"
              phone={selected.employer_contact_phone}
              telegramUsername={selected.employer_telegram_username}
              telegramId={selected.employer_telegram_id}
              companyName={selected.employer_company_name}
            />
            <div className="form-actions">
              <button type="button" className="btn" onClick={() => setView("complaint")}>
                Пожаловаться
              </button>
            </div>
          </>
        ) : (
          <button
            type="button"
            className="btn secondary"
            disabled={cancellingId === selected.id}
            onClick={() => void handleCancel(selected.id)}
          >
            {cancellingId === selected.id ? "Отмена…" : "Отменить отклик"}
          </button>
        )}
      </section>
    );
  }

  if (state.status !== "ready") {
    return <p className="status">Загрузка…</p>;
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
            <button
              type="button"
              className="complaint-select-btn"
              onClick={() => handleOpenDetail(item)}
            >
              <strong>{item.job_title}</strong>
              <p className="hint">
                {item.category_name ?? "—"} · {item.metro_station_name ?? "—"}
              </p>
              <p>
                {formatDate(item.shift_date)} {formatTime(item.start_time)}–{formatTime(item.end_time)}
              </p>
              <p className="hint">
                {APPLICATION_STATUS_LABELS[item.status as ApplicationStatus] ?? item.status}
              </p>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
