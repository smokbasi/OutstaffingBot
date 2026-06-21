import { useEffect, useState } from "react";
import { getWorkerVacancy, type VacancyDetail } from "../api/client";

type VacancyDetailPageProps = {
  initData: string;
  vacancyId: string;
  onBack: () => void;
};

type DetailState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; vacancy: VacancyDetail };

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

function formatRate(rate: string): string {
  const num = Number(rate);
  return Number.isNaN(num) ? rate : `${num.toLocaleString("ru-RU")} ₽/час`;
}

export function VacancyDetailPage({ initData, vacancyId, onBack }: VacancyDetailPageProps) {
  const [state, setState] = useState<DetailState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;

    async function loadVacancy() {
      setState({ status: "loading" });
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

  const { vacancy } = state;

  return (
    <section className="card vacancy-detail">
      <button type="button" className="link-btn back-link" onClick={onBack}>
        ← К списку
      </button>
      <h2>{vacancy.title}</h2>
      <p className="hint">
        {vacancy.category_name ?? "—"} · {vacancy.metro_station_name ?? "—"}
      </p>
      <p>{formatRate(vacancy.hourly_rate)}</p>
      {vacancy.address ? <p className="hint">Адрес: {vacancy.address}</p> : null}
      <p>{vacancy.description}</p>
      {vacancy.dress_code ? <p className="hint">Дресс-код: {vacancy.dress_code}</p> : null}
      {vacancy.min_experience_months ? (
        <p className="hint">Мин. опыт: {vacancy.min_experience_months} мес.</p>
      ) : null}

      <h3>Доступные смены</h3>
      {vacancy.shift_slots.length === 0 ? (
        <p className="hint">Свободных смен нет.</p>
      ) : (
        <ul className="job-shifts">
          {vacancy.shift_slots.map((slot) => (
            <li key={slot.id}>
              {formatDate(slot.shift_date)} {formatTime(slot.start_time)}–{formatTime(slot.end_time)} ·
              свободно {slot.slots_total - slot.slots_filled}/{slot.slots_total}
            </li>
          ))}
        </ul>
      )}

      <p className="hint">Отклик на смену будет доступен в следующей версии.</p>
    </section>
  );
}
