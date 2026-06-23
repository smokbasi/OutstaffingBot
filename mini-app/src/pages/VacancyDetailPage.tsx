import { useEffect, useState } from "react";
import {
  applyToShift,
  getWorkerVacancy,
  ShiftConflictError,
  type ShiftConflictBody,
  type VacancyDetail,
} from "../api/client";
import { formatHourlyRate } from "../utils/formatRate";

type VacancyDetailPageProps = {
  initData: string;
  vacancyId: string;
  onBack: () => void;
};

type DetailState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; vacancy: VacancyDetail }
  | { status: "conflict"; vacancy: VacancyDetail; conflict: ShiftConflictBody; slotId: string };

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

function triggerHaptic(type: "light" | "medium" | "heavy" = "medium") {
  const haptic = (
    window.Telegram?.WebApp as { HapticFeedback?: { impactOccurred?: (t: string) => void } } | undefined
  )?.HapticFeedback;
  haptic?.impactOccurred?.(type);
}

export function VacancyDetailPage({ initData, vacancyId, onBack }: VacancyDetailPageProps) {
  const [state, setState] = useState<DetailState>({ status: "loading" });
  const [applyingSlotId, setApplyingSlotId] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadVacancy() {
      setState({ status: "loading" });
      setSuccessMessage(null);
      try {
        const vacancy = await getWorkerVacancy(initData, vacancyId);
        if (!cancelled) {
          setState({ status: "ready", vacancy });
        }
      } catch (err) {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : "Не удалось загрузить вакансию";
          setState({ status: "error", message });
        }
      }
    }

    void loadVacancy();
    return () => {
      cancelled = true;
    };
  }, [initData, vacancyId]);

  async function handleApply(slotId: string, cancelConflictingId?: string) {
    setApplyingSlotId(slotId);
    setSuccessMessage(null);
    try {
      const result = await applyToShift(initData, slotId, cancelConflictingId);
      triggerHaptic("medium");
      setSuccessMessage(
        `Отклик отправлен: ${result.job_title}, ${formatDate(result.shift_date)} ${formatTime(result.start_time)}–${formatTime(result.end_time)}`,
      );
      if (state.status === "ready" || state.status === "conflict") {
        setState({ status: "ready", vacancy: state.vacancy });
      }
    } catch (err) {
      if (err instanceof ShiftConflictError && (state.status === "ready" || state.status === "conflict")) {
        setState({
          status: "conflict",
          vacancy: state.vacancy,
          conflict: err.conflict,
          slotId,
        });
        return;
      }
      const message = err instanceof Error ? err.message : "Не удалось отправить отклик";
      setSuccessMessage(null);
      alert(message);
    } finally {
      setApplyingSlotId(null);
    }
  }

  if (state.status === "loading") {
    return <p className="status">Загрузка…</p>;
  }

  if (state.status === "error") {
    return (
      <section className="card">
        <p className="error">{state.message}</p>
        <button type="button" className="btn secondary" onClick={onBack}>
          Назад
        </button>
      </section>
    );
  }

  const vacancy = state.vacancy;

  if (state.status === "conflict") {
    const { conflict, slotId } = state;
    return (
      <section className="card vacancy-detail">
        <h2>Конфликт смен</h2>
        <p>{conflict.detail}</p>
        <p className="hint">
          Текущая: {formatDate(conflict.conflicting.shift_date)}{" "}
          {formatTime(conflict.conflicting.start_time)}–{formatTime(conflict.conflicting.end_time)} (
          {conflict.conflicting.job_title})
        </p>
        <div className="form-actions">
          <button
            type="button"
            className="btn"
            disabled={applyingSlotId !== null}
            onClick={() =>
              void handleApply(slotId, conflict.conflicting.application_id)
            }
          >
            Отменить предыдущую и откликнуться
          </button>
          <button
            type="button"
            className="btn secondary"
            onClick={() => setState({ status: "ready", vacancy })}
          >
            Назад
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="card vacancy-detail">
      <button type="button" className="link-btn back-link" onClick={onBack}>
        ← К списку
      </button>
      <h2>{vacancy.title}</h2>
      <p className="hint">
        {vacancy.category_name ?? "—"} · {vacancy.metro_station_name ?? "—"}
      </p>
      <p>{formatHourlyRate(vacancy.hourly_rate)}</p>
      {vacancy.address ? <p className="hint">Адрес: {vacancy.address}</p> : null}
      <p>{vacancy.description}</p>
      {vacancy.dress_code ? <p className="hint">Дресс-код: {vacancy.dress_code}</p> : null}
      {vacancy.min_experience_months ? (
        <p className="hint">Мин. опыт: {vacancy.min_experience_months} мес.</p>
      ) : null}

      {successMessage ? <p className="success">{successMessage}</p> : null}

      <h3>Доступные смены</h3>
      {vacancy.shift_slots.length === 0 ? (
        <p className="hint">Свободных смен нет.</p>
      ) : (
        <ul className="job-shifts apply-shifts">
          {vacancy.shift_slots.map((slot) => (
            <li key={slot.id} className="shift-row">
              <span>
                {formatDate(slot.shift_date)} {formatTime(slot.start_time)}–{formatTime(slot.end_time)} ·
                свободно {slot.slots_total - slot.slots_filled}/{slot.slots_total}
              </span>
              <button
                type="button"
                className="btn small-btn"
                disabled={applyingSlotId === slot.id}
                onClick={() => void handleApply(slot.id)}
              >
                {applyingSlotId === slot.id ? "…" : "Откликнуться"}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
