import { useEffect, useState, type FormEvent } from "react";
import {
  APPLICATION_STATUS_LABELS,
  COMPLAINT_VIOLATION_TYPE_LABELS,
  createWorkerComplaint,
  getWorkerComplaintContext,
  type ApplicationStatus,
  type ComplaintViolationType,
  type WorkerEligibleApplication,
} from "../api/client";
import { triggerNotificationHaptic } from "../lib/telegram";

type WorkerComplaintsPageProps = {
  initData: string;
};

type PageState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; items: WorkerEligibleApplication[] };

type View = "list" | "form" | "success";

const VIOLATION_TYPES: ComplaintViolationType[] = ["late", "no_show", "no_payment", "no_work"];
const MIN_DESCRIPTION_LENGTH = 20;

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

export function WorkerComplaintsPage({ initData }: WorkerComplaintsPageProps) {
  const [state, setState] = useState<PageState>({ status: "loading" });
  const [view, setView] = useState<View>("list");
  const [selected, setSelected] = useState<WorkerEligibleApplication | null>(null);
  const [violationType, setViolationType] = useState<ComplaintViolationType>("late");
  const [description, setDescription] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function loadContext() {
    setState({ status: "loading" });
    try {
      const data = await getWorkerComplaintContext(initData);
      setState({ status: "ready", items: data.applications });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Не удалось загрузить отклики";
      setState({ status: "error", message });
    }
  }

  useEffect(() => {
    void loadContext();
  }, [initData]);

  function handleSelectApplication(item: WorkerEligibleApplication) {
    setSelected(item);
    setViolationType("late");
    setDescription("");
    setFormError(null);
    setView("form");
  }

  function handleBackToList() {
    setSelected(null);
    setFormError(null);
    setView("list");
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!selected) {
      return;
    }
    const trimmed = description.trim();
    if (trimmed.length < MIN_DESCRIPTION_LENGTH) {
      setFormError(`Описание — минимум ${MIN_DESCRIPTION_LENGTH} символов`);
      return;
    }
    setBusy(true);
    setFormError(null);
    try {
      await createWorkerComplaint(initData, {
        application_id: selected.id,
        violation_type: violationType,
        description: trimmed,
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

  if (state.status === "loading") {
    return <p className="status">Загрузка…</p>;
  }

  if (state.status === "error") {
    return (
      <section className="card">
        <p className="error">{state.message}</p>
        <button type="button" className="btn secondary" onClick={() => void loadContext()}>
          Повторить
        </button>
      </section>
    );
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
            setView("list");
            setSelected(null);
            void loadContext();
          }}
        >
          К списку откликов
        </button>
      </section>
    );
  }

  if (view === "form" && selected) {
    return (
      <section className="card">
        <button type="button" className="link-btn back-link" onClick={handleBackToList}>
          ← Назад
        </button>
        <h2>Пожаловаться</h2>
        <p className="hint">
          {selected.job_title} · {selected.company_name}
        </p>
        <p className="hint">
          {formatDate(selected.shift_date)} {formatTime(selected.start_time)}–{formatTime(selected.end_time)}
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
            <span>Описание (обязательно)</span>
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Опишите ситуацию подробно…"
              rows={5}
              disabled={busy}
            />
            <span className="hint">Минимум {MIN_DESCRIPTION_LENGTH} символов</span>
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

  if (state.items.length === 0) {
    return (
      <section className="card">
        <h2>Пожаловаться</h2>
        <p className="hint">Нет откликов для жалобы.</p>
        <p className="hint">Жалобу можно подать только по принятому отклику.</p>
      </section>
    );
  }

  return (
    <section className="card">
      <h2>Пожаловаться</h2>
      <p className="hint">Выберите отклик, по которому хотите подать жалобу.</p>
      <ul className="applications-list">
        {state.items.map((item) => (
          <li key={item.id} className="application-item">
            <button
              type="button"
              className="complaint-select-btn"
              onClick={() => handleSelectApplication(item)}
            >
              <strong>{item.job_title}</strong>
              <p className="hint">{item.company_name}</p>
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
