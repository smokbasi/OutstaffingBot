import { useState, type FormEvent } from "react";
import {
  COMPLAINT_VIOLATION_TYPE_LABELS,
  type ComplaintViolationType,
} from "../api/client";
import { triggerNotificationHaptic } from "../lib/telegram";

const VIOLATION_TYPES: ComplaintViolationType[] = ["late", "no_show", "no_payment", "no_work"];
export const WORKER_MIN_DESCRIPTION_LENGTH = 20;

type ComplaintFormProps = {
  title: string;
  hints: string[];
  descriptionRequired: boolean;
  minDescriptionLength?: number;
  onBack: () => void;
  onSubmit: (data: { violationType: ComplaintViolationType; description: string }) => Promise<void>;
};

export function ComplaintForm({
  title,
  hints,
  descriptionRequired,
  minDescriptionLength = WORKER_MIN_DESCRIPTION_LENGTH,
  onBack,
  onSubmit,
}: ComplaintFormProps) {
  const [violationType, setViolationType] = useState<ComplaintViolationType>("late");
  const [description, setDescription] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const trimmed = description.trim();
    if (descriptionRequired && trimmed.length < minDescriptionLength) {
      setFormError(`Описание — минимум ${minDescriptionLength} символов`);
      return;
    }
    setBusy(true);
    setFormError(null);
    try {
      await onSubmit({ violationType, description: trimmed });
      triggerNotificationHaptic("success");
    } catch (err) {
      triggerNotificationHaptic("error");
      const message = err instanceof Error ? err.message : "Не удалось отправить жалобу";
      setFormError(message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card">
      <button type="button" className="link-btn back-link" onClick={onBack}>
        ← Назад
      </button>
      <h2>{title}</h2>
      {hints.map((hint) => (
        <p key={hint} className="hint">
          {hint}
        </p>
      ))}
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
          <span>{descriptionRequired ? "Описание (обязательно)" : "Описание (необязательно)"}</span>
          <textarea
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder={descriptionRequired ? "Опишите ситуацию подробно…" : "Дополнительные детали…"}
            rows={5}
            disabled={busy}
          />
          {descriptionRequired ? (
            <span className="hint">Минимум {minDescriptionLength} символов</span>
          ) : null}
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

export function ComplaintSuccess({ onDone, doneLabel }: { onDone: () => void; doneLabel: string }) {
  return (
    <section className="card">
      <h2>Жалоба отправлена</h2>
      <p className="success">Мы получили вашу жалобу. Администратор рассмотрит её в ближайшее время.</p>
      <button type="button" className="btn" onClick={onDone}>
        {doneLabel}
      </button>
    </section>
  );
}
