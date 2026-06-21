import { useEffect, useState } from "react";
import {
  createJob,
  listCategories,
  searchMetroStations,
  updateJobStatus,
  type JobCategory,
  type JobRequestCreate,
  type MetroStation,
  type RequiredGender,
} from "../api/client";

type CreateJobPageProps = {
  initData: string;
  onCreated?: () => void;
  onCancel?: () => void;
};

type ShiftSlotForm = {
  shift_date: string;
  start_time: string;
  end_time: string;
};

type JobFormData = {
  category_id: string;
  title: string;
  description: string;
  metro_station_id: number | null;
  metro_label: string;
  address: string;
  hourly_rate: string;
  workers_needed: string;
  min_experience_months: string;
  required_gender: string;
  min_age: string;
  max_age: string;
  dress_code: string;
  contact_info: string;
  post_to_groups: boolean;
  notify_matching_workers: boolean;
  shift_slots: ShiftSlotForm[];
};

type FormErrors = Partial<Record<string, string>>;

/** Matches PostgreSQL NUMERIC(10, 2) — values must be < 10^8 */
const MAX_HOURLY_RATE = 99999999.99;

const GENDER_OPTIONS = [
  { value: "", label: "Не указан" },
  { value: "any", label: "Любой" },
  { value: "male", label: "Мужской" },
  { value: "female", label: "Женский" },
] as const;

const EMPTY_SHIFT: ShiftSlotForm = {
  shift_date: "",
  start_time: "10:00",
  end_time: "22:00",
};

function emptyForm(): JobFormData {
  return {
    category_id: "",
    title: "",
    description: "",
    metro_station_id: null,
    metro_label: "",
    address: "",
    hourly_rate: "",
    workers_needed: "1",
    min_experience_months: "",
    required_gender: "",
    min_age: "",
    max_age: "",
    dress_code: "",
    contact_info: "",
    post_to_groups: false,
    notify_matching_workers: true,
    shift_slots: [{ ...EMPTY_SHIFT }],
  };
}

function toApiTime(value: string): string {
  return value.length === 5 ? `${value}:00` : value;
}

function validateForm(form: JobFormData): FormErrors {
  const errors: FormErrors = {};
  if (!form.category_id) {
    errors.category_id = "Выберите категорию";
  }
  if (!form.title.trim()) {
    errors.title = "Укажите название";
  } else if (form.title.length > 200) {
    errors.title = "Не более 200 символов";
  }
  if (!form.description.trim()) {
    errors.description = "Укажите описание";
  }
  if (!form.metro_station_id) {
    errors.metro_station_id = "Выберите станцию метро";
  }
  const rate = Number(form.hourly_rate);
  if (!form.hourly_rate.trim() || Number.isNaN(rate)) {
    errors.hourly_rate = "Укажите ставку";
  } else if (rate < 0) {
    errors.hourly_rate = "Ставка должна быть ≥ 0";
  } else if (rate > MAX_HOURLY_RATE) {
    errors.hourly_rate = `Ставка не более ${MAX_HOURLY_RATE} ₽/час`;
  }
  const workers = Number(form.workers_needed);
  if (!form.workers_needed.trim() || Number.isNaN(workers)) {
    errors.workers_needed = "Укажите количество";
  } else if (workers < 1 || workers > 100) {
    errors.workers_needed = "От 1 до 100";
  }
  if (form.min_experience_months.trim()) {
    const exp = Number(form.min_experience_months);
    if (Number.isNaN(exp) || exp < 0 || exp > 600) {
      errors.min_experience_months = "От 0 до 600 мес.";
    }
  }
  if (form.min_age.trim()) {
    const minAge = Number(form.min_age);
    if (Number.isNaN(minAge) || minAge < 16 || minAge > 70) {
      errors.min_age = "Возраст от 16 до 70";
    }
  }
  if (form.max_age.trim()) {
    const maxAge = Number(form.max_age);
    if (Number.isNaN(maxAge) || maxAge < 16 || maxAge > 70) {
      errors.max_age = "Возраст от 16 до 70";
    }
  }
  if (form.min_age.trim() && form.max_age.trim()) {
    const minAge = Number(form.min_age);
    const maxAge = Number(form.max_age);
    if (!Number.isNaN(minAge) && !Number.isNaN(maxAge) && minAge > maxAge) {
      errors.max_age = "Макс. возраст ≥ мин.";
    }
  }

  if (form.shift_slots.length === 0) {
    errors.shift_slots = "Добавьте хотя бы одну смену";
  } else {
    form.shift_slots.forEach((slot, index) => {
      if (!slot.shift_date) {
        errors[`shift_date_${index}`] = "Укажите дату";
      }
      if (!slot.start_time || !slot.end_time) {
        errors[`shift_time_${index}`] = "Укажите время";
      } else if (slot.start_time >= slot.end_time) {
        errors[`shift_time_${index}`] = "Начало должно быть раньше конца";
      }
    });
  }
  return errors;
}

function formToPayload(form: JobFormData): JobRequestCreate {
  return {
    category_id: Number(form.category_id),
    title: form.title.trim(),
    description: form.description.trim(),
    metro_station_id: form.metro_station_id!,
    address: form.address.trim() || null,
    hourly_rate: Number(form.hourly_rate).toFixed(2),
    workers_needed: Number(form.workers_needed),
    min_experience_months: form.min_experience_months.trim()
      ? Number(form.min_experience_months)
      : null,
    required_gender: (form.required_gender || null) as RequiredGender | null,
    min_age: form.min_age.trim() ? Number(form.min_age) : null,
    max_age: form.max_age.trim() ? Number(form.max_age) : null,
    dress_code: form.dress_code.trim() || null,
    contact_info: form.contact_info.trim() || null,
    post_to_groups: form.post_to_groups,
    notify_matching_workers: form.notify_matching_workers,
    shift_slots: form.shift_slots.map((slot) => ({
      shift_date: slot.shift_date,
      start_time: toApiTime(slot.start_time),
      end_time: toApiTime(slot.end_time),
    })),
  };
}

export function CreateJobPage({ initData, onCreated, onCancel }: CreateJobPageProps) {
  const [categories, setCategories] = useState<JobCategory[]>([]);
  const [categoriesError, setCategoriesError] = useState<string | null>(null);
  const [form, setForm] = useState<JobFormData>(emptyForm);
  const [formErrors, setFormErrors] = useState<FormErrors>({});
  const [saveError, setSaveError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [showOptional, setShowOptional] = useState(false);
  const [metroQuery, setMetroQuery] = useState("");
  const [metroResults, setMetroResults] = useState<MetroStation[]>([]);
  const [metroLoading, setMetroLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    void listCategories()
      .then((data) => {
        if (!cancelled) {
          setCategories(data);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          const message = err instanceof Error ? err.message : "Не удалось загрузить категории";
          setCategoriesError(message);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const query = metroQuery.trim();
    if (query.length < 2) {
      setMetroResults([]);
      return;
    }

    let cancelled = false;
    const timer = setTimeout(() => {
      setMetroLoading(true);
      void searchMetroStations(query)
        .then((stations) => {
          if (!cancelled) {
            setMetroResults(stations);
          }
        })
        .catch(() => {
          if (!cancelled) {
            setMetroResults([]);
          }
        })
        .finally(() => {
          if (!cancelled) {
            setMetroLoading(false);
          }
        });
    }, 300);

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [metroQuery]);

  function updateField<K extends keyof JobFormData>(key: K, value: JobFormData[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
    setFormErrors((prev) => ({ ...prev, [key]: undefined }));
    setSaveError(null);
  }

  function updateShift(index: number, patch: Partial<ShiftSlotForm>) {
    setForm((prev) => ({
      ...prev,
      shift_slots: prev.shift_slots.map((slot, i) => (i === index ? { ...slot, ...patch } : slot)),
    }));
    setFormErrors((prev) => ({
      ...prev,
      [`shift_date_${index}`]: undefined,
      [`shift_time_${index}`]: undefined,
      shift_slots: undefined,
    }));
    setSaveError(null);
  }

  function addShift() {
    setForm((prev) => ({
      ...prev,
      shift_slots: [...prev.shift_slots, { ...EMPTY_SHIFT }],
    }));
  }

  function removeShift(index: number) {
    setForm((prev) => ({
      ...prev,
      shift_slots: prev.shift_slots.filter((_, i) => i !== index),
    }));
  }

  function selectMetro(station: MetroStation) {
    updateField("metro_station_id", station.id);
    updateField("metro_label", station.name);
    setMetroQuery(station.name);
    setMetroResults([]);
  }

  function clearMetro() {
    updateField("metro_station_id", null);
    updateField("metro_label", "");
    setMetroQuery("");
    setMetroResults([]);
  }

  async function handleSubmit(publish: boolean) {
    const errors = validateForm(form);
    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }

    setIsSaving(true);
    setSaveError(null);
    try {
      const job = await createJob(initData, formToPayload(form));
      if (publish) {
        await updateJobStatus(initData, job.id, "active");
      }
      setForm(emptyForm());
      setMetroQuery("");
      onCreated?.();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Не удалось сохранить заявку";
      setSaveError(message);
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section className="card job-form-card">
      <h2>Новая заявка</h2>

      {categoriesError ? <p className="error">{categoriesError}</p> : null}

      <form
        className="profile-form"
        onSubmit={(e) => {
          e.preventDefault();
          void handleSubmit(false);
        }}
      >
        <label className="form-field">
          <span>Категория</span>
          <select
            value={form.category_id}
            disabled={isSaving || categories.length === 0}
            onChange={(e) => updateField("category_id", e.target.value)}
          >
            <option value="">Выберите категорию…</option>
            {categories.map((cat) => (
              <option key={cat.id} value={String(cat.id)}>
                {cat.name_ru}
              </option>
            ))}
          </select>
          {formErrors.category_id ? <em className="field-error">{formErrors.category_id}</em> : null}
        </label>

        <label className="form-field">
          <span>Название</span>
          <input
            type="text"
            maxLength={200}
            value={form.title}
            disabled={isSaving}
            onChange={(e) => updateField("title", e.target.value)}
          />
          {formErrors.title ? <em className="field-error">{formErrors.title}</em> : null}
        </label>

        <label className="form-field">
          <span>Описание</span>
          <textarea
            rows={4}
            value={form.description}
            disabled={isSaving}
            onChange={(e) => updateField("description", e.target.value)}
          />
          {formErrors.description ? <em className="field-error">{formErrors.description}</em> : null}
        </label>

        <div className="form-field">
          <span>Метро</span>
          <input
            type="text"
            value={metroQuery}
            placeholder="Начните вводить станцию…"
            disabled={isSaving}
            onChange={(e) => {
              setMetroQuery(e.target.value);
              updateField("metro_station_id", null);
              updateField("metro_label", "");
            }}
          />
          {form.metro_station_id ? (
            <p className="hint">
              Выбрано: {form.metro_label}
              <button type="button" className="link-btn" onClick={clearMetro} disabled={isSaving}>
                Сбросить
              </button>
            </p>
          ) : null}
          {formErrors.metro_station_id ? (
            <em className="field-error">{formErrors.metro_station_id}</em>
          ) : null}
          {metroLoading ? <p className="hint">Поиск…</p> : null}
          {metroResults.length > 0 ? (
            <ul className="metro-results">
              {metroResults.map((station) => (
                <li key={station.id}>
                  <button
                    type="button"
                    className="metro-option"
                    disabled={isSaving}
                    onClick={() => selectMetro(station)}
                  >
                    {station.name}
                    <span className="hint"> ({station.line_name})</span>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </div>

        <label className="form-field">
          <span>Ставка (₽/час)</span>
          <input
            type="number"
            min={0}
            step="1"
            value={form.hourly_rate}
            disabled={isSaving}
            onChange={(e) => updateField("hourly_rate", e.target.value)}
          />
          {formErrors.hourly_rate ? <em className="field-error">{formErrors.hourly_rate}</em> : null}
        </label>

        <label className="form-field">
          <span>Работников на смену</span>
          <input
            type="number"
            min={1}
            max={100}
            value={form.workers_needed}
            disabled={isSaving}
            onChange={(e) => updateField("workers_needed", e.target.value)}
          />
          {formErrors.workers_needed ? (
            <em className="field-error">{formErrors.workers_needed}</em>
          ) : null}
        </label>

        <div className="form-field">
          <span>Смены</span>
          {formErrors.shift_slots ? <em className="field-error">{formErrors.shift_slots}</em> : null}
          <ul className="shift-slots-list">
            {form.shift_slots.map((slot, index) => (
              <li key={index} className="shift-slot-row">
                <label className="form-field compact">
                  <span>Дата</span>
                  <input
                    type="date"
                    value={slot.shift_date}
                    disabled={isSaving}
                    onChange={(e) => updateShift(index, { shift_date: e.target.value })}
                  />
                  {formErrors[`shift_date_${index}`] ? (
                    <em className="field-error">{formErrors[`shift_date_${index}`]}</em>
                  ) : null}
                </label>
                <label className="form-field compact">
                  <span>Начало</span>
                  <input
                    type="time"
                    value={slot.start_time}
                    disabled={isSaving}
                    onChange={(e) => updateShift(index, { start_time: e.target.value })}
                  />
                </label>
                <label className="form-field compact">
                  <span>Конец</span>
                  <input
                    type="time"
                    value={slot.end_time}
                    disabled={isSaving}
                    onChange={(e) => updateShift(index, { end_time: e.target.value })}
                  />
                </label>
                {formErrors[`shift_time_${index}`] ? (
                  <em className="field-error">{formErrors[`shift_time_${index}`]}</em>
                ) : null}
                {form.shift_slots.length > 1 ? (
                  <button
                    type="button"
                    className="link-btn shift-remove"
                    disabled={isSaving}
                    onClick={() => removeShift(index)}
                  >
                    Удалить
                  </button>
                ) : null}
              </li>
            ))}
          </ul>
          <button type="button" className="btn secondary add-shift-btn" disabled={isSaving} onClick={addShift}>
            + Добавить смену
          </button>
        </div>

        <button
          type="button"
          className="link-btn optional-toggle"
          onClick={() => setShowOptional((v) => !v)}
        >
          {showOptional ? "Скрыть доп. поля" : "Дополнительные поля"}
        </button>

        {showOptional ? (
          <div className="optional-fields">
            <label className="form-field">
              <span>Адрес</span>
              <input
                type="text"
                maxLength={300}
                value={form.address}
                disabled={isSaving}
                onChange={(e) => updateField("address", e.target.value)}
              />
            </label>

            <label className="form-field">
              <span>Мин. опыт (мес.)</span>
              <input
                type="number"
                min={0}
                max={600}
                value={form.min_experience_months}
                disabled={isSaving}
                onChange={(e) => updateField("min_experience_months", e.target.value)}
              />
              {formErrors.min_experience_months ? (
                <em className="field-error">{formErrors.min_experience_months}</em>
              ) : null}
            </label>

            <label className="form-field">
              <span>Требуемый пол</span>
              <select
                value={form.required_gender}
                disabled={isSaving}
                onChange={(e) => updateField("required_gender", e.target.value)}
              >
                {GENDER_OPTIONS.map((opt) => (
                  <option key={opt.value || "empty"} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </label>

            <div className="form-row">
              <label className="form-field">
                <span>Мин. возраст</span>
                <input
                  type="number"
                  min={16}
                  max={70}
                  value={form.min_age}
                  disabled={isSaving}
                  onChange={(e) => updateField("min_age", e.target.value)}
                />
                {formErrors.min_age ? <em className="field-error">{formErrors.min_age}</em> : null}
              </label>
              <label className="form-field">
                <span>Макс. возраст</span>
                <input
                  type="number"
                  min={16}
                  max={70}
                  value={form.max_age}
                  disabled={isSaving}
                  onChange={(e) => updateField("max_age", e.target.value)}
                />
                {formErrors.max_age ? <em className="field-error">{formErrors.max_age}</em> : null}
              </label>
            </div>

            <label className="form-field">
              <span>Дресс-код</span>
              <input
                type="text"
                maxLength={200}
                value={form.dress_code}
                disabled={isSaving}
                onChange={(e) => updateField("dress_code", e.target.value)}
              />
            </label>

            <label className="form-field">
              <span>Контакт</span>
              <textarea
                rows={2}
                value={form.contact_info}
                disabled={isSaving}
                onChange={(e) => updateField("contact_info", e.target.value)}
              />
            </label>

            <label className="form-field checkbox-field">
              <input
                type="checkbox"
                checked={form.post_to_groups}
                disabled={isSaving}
                onChange={(e) => updateField("post_to_groups", e.target.checked)}
              />
              <span>Публиковать в Telegram-группы</span>
            </label>

            <label className="form-field checkbox-field">
              <input
                type="checkbox"
                checked={form.notify_matching_workers}
                disabled={isSaving}
                onChange={(e) => updateField("notify_matching_workers", e.target.checked)}
              />
              <span>Уведомлять подходящих работников</span>
            </label>
          </div>
        ) : null}

        {saveError ? <p className="error">{saveError}</p> : null}

        <div className="form-actions">
          <button type="submit" className="btn" disabled={isSaving}>
            {isSaving ? "Сохранение…" : "Сохранить черновик"}
          </button>
          <button
            type="button"
            className="btn"
            disabled={isSaving}
            onClick={() => void handleSubmit(true)}
          >
            {isSaving ? "Публикация…" : "Опубликовать"}
          </button>
          {onCancel ? (
            <button type="button" className="btn secondary" disabled={isSaving} onClick={onCancel}>
              Отмена
            </button>
          ) : null}
        </div>
      </form>
    </section>
  );
}
