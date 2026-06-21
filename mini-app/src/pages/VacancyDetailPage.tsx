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
  window.Telegram?.WebApp?.HapticFeedback?.impactOccurred?.(type);
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
          const message = err instanceof Error ? err.message : "╨Э╨╡ ╤Г╨┤╨░╨╗╨╛╤Б╤М ╨╖╨░╨│╤А╤Г╨╖╨╕╤В╤М ╨▓╨░╨║╨░╨╜╤Б╨╕╤О";
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
        `╨Ю╤В╨║╨╗╨╕╨║ ╨╛╤В╨┐╤А╨░╨▓╨╗╨╡╨╜: ${result.job_title}, ${formatDate(result.shift_date)} ${formatTime(result.start_time)}тАУ${formatTime(result.end_time)}`,
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
      const message = err instanceof Error ? err.message : "╨Э╨╡ ╤Г╨┤╨░╨╗╨╛╤Б╤М ╨╛╤В╨┐╤А╨░╨▓╨╕╤В╤М ╨╛╤В╨║╨╗╨╕╨║";
      setSuccessMessage(null);
      alert(message);
    } finally {
      setApplyingSlotId(null);
    }
  }

  if (state.status === "loading") {
    return <p className="status">╨Ч╨░╨│╤А╤Г╨╖╨║╨░тАж</p>;
  }

  if (state.status === "error") {
    return (
      <section className="card">
        <p className="error">{state.message}</p>
        <button type="button" className="btn secondary" onClick={onBack}>
          ╨Э╨░╨╖╨░╨┤
        </button>
      </section>
    );
  }

  const vacancy = state.vacancy;

  if (state.status === "conflict") {
    const { conflict, slotId } = state;
    return (
      <section className="card vacancy-detail">
        <h2>╨Ъ╨╛╨╜╤Д╨╗╨╕╨║╤В ╤Б╨╝╨╡╨╜</h2>
        <p>{conflict.detail}</p>
        <p className="hint">
          ╨в╨╡╨║╤Г╤Й╨░╤П: {formatDate(conflict.conflicting.shift_date)}{" "}
          {formatTime(conflict.conflicting.start_time)}тАУ{formatTime(conflict.conflicting.end_time)} (
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
            ╨Ю╤В╨╝╨╡╨╜╨╕╤В╤М ╨┐╤А╨╡╨┤╤Л╨┤╤Г╤Й╤Г╤О ╨╕ ╨╛╤В╨║╨╗╨╕╨║╨╜╤Г╤В╤М╤Б╤П
          </button>
          <button
            type="button"
            className="btn secondary"
            onClick={() => setState({ status: "ready", vacancy })}
          >
            ╨Э╨░╨╖╨░╨┤
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="card vacancy-detail">
      <button type="button" className="link-btn back-link" onClick={onBack}>
        тЖР ╨Ъ ╤Б╨┐╨╕╤Б╨║╤Г
      </button>
      <h2>{vacancy.title}</h2>
      <p className="hint">
        {vacancy.category_name ?? "тАФ"} ┬╖ {vacancy.metro_station_name ?? "тАФ"}
      </p>
      <p>{formatHourlyRate(vacancy.hourly_rate)}</p>
      {vacancy.address ? <p className="hint">╨Р╨┤╤А╨╡╤Б: {vacancy.address}</p> : null}
      <p>{vacancy.description}</p>
      {vacancy.dress_code ? <p className="hint">╨Ф╤А╨╡╤Б╤Б-╨║╨╛╨┤: {vacancy.dress_code}</p> : null}
      {vacancy.min_experience_months ? (
        <p className="hint">╨Ь╨╕╨╜. ╨╛╨┐╤Л╤В: {vacancy.min_experience_months} ╨╝╨╡╤Б.</p>
      ) : null}

      {successMessage ? <p className="success">{successMessage}</p> : null}

      <h3>╨Ф╨╛╤Б╤В╤Г╨┐╨╜╤Л╨╡ ╤Б╨╝╨╡╨╜╤Л</h3>
      {vacancy.shift_slots.length === 0 ? (
        <p className="hint">╨б╨▓╨╛╨▒╨╛╨┤╨╜╤Л╤Е ╤Б╨╝╨╡╨╜ ╨╜╨╡╤В.</p>
      ) : (
        <ul className="job-shifts apply-shifts">
          {vacancy.shift_slots.map((slot) => (
            <li key={slot.id} className="shift-row">
              <span>
                {formatDate(slot.shift_date)} {formatTime(slot.start_time)}тАУ{formatTime(slot.end_time)} ┬╖
                ╤Б╨▓╨╛╨▒╨╛╨┤╨╜╨╛ {slot.slots_total - slot.slots_filled}/{slot.slots_total}
              </span>
              <button
                type="button"
                className="btn small-btn"
                disabled={applyingSlotId === slot.id}
                onClick={() => void handleApply(slot.id)}
              >
                {applyingSlotId === slot.id ? "тАж" : "╨Ю╤В╨║╨╗╨╕╨║╨╜╤Г╤В╤М╤Б╤П"}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
