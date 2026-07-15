import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  ContentRejectedError,
  createJob,
  getEmployerPhoneCountryPrefs,
  MAX_HOURLY_RATE,
  updateEmployerPhoneCountryPref,
  updateJobStatus,
  type CategorySelection,
  type CustomRoleVerifyResult,
  type JobRequestCreate,
  type MetroStation,
  type RequiredGender,
} from "../api/client";
import {
  CategoryPicker,
  categorySelectionToFormFields,
  isCategorySelectionValid,
} from "../components/CategoryPicker";
import { useMetroStationSearch } from "../hooks/useMetroStationSearch";
import {
  getTelegramUserId,
  getTelegramUsername,
  normalizeTelegramUsername,
} from "../lib/telegram";
import { preventNumberInputWheel } from "../utils/formatRate";
import {
  buildCountryCodeOptions,
  buildE164Phone,
  CUSTOM_COUNTRY_CODE,
  DEFAULT_COUNTRY_CODES,
  defaultPhoneCountryPrefs,
  extractNationalDigits,
  formatNationalPhone,
  handlePhoneKeyDown,
  isValidCountryCode,
  loadPhoneCountryPrefs,
  normalizeCountryCode,
  savePhoneCountryPrefs,
  type CountryCodeOption,
} from "../utils/phoneInput";
import type { PhoneCountryPrefs } from "../api/client";

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
  phone_country_code: string;
  contact_phone_national: string;
  telegram_username: string;
  includes_lunch: boolean;
  post_to_groups: boolean;
  notify_matching_workers: boolean;
  shift_slots: ShiftSlotForm[];
};

type FormErrors = Partial<Record<string, string>>;

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

function emptyForm(preferredCountryCode = "+7"): JobFormData {
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
    phone_country_code: preferredCountryCode,
    contact_phone_national: "",
    telegram_username: "",
    includes_lunch: false,
    post_to_groups: true,
    notify_matching_workers: true,
    shift_slots: [{ ...EMPTY_SHIFT }],
  };
}

function toApiTime(value: string): string {
  return value.length === 5 ? `${value}:00` : value;
}

function clampHourlyRateInput(value: string): string {
  if (!value.trim()) {
    return value;
  }
  const num = Number(value);
  if (Number.isNaN(num)) {
    return value;
  }
  if (num > MAX_HOURLY_RATE) {
    return String(MAX_HOURLY_RATE);
  }
  if (num < 0) {
    return "0";
  }
  return value;
}

function RequiredLabel({ children }: { children: ReactNode }) {
  return (
    <>
      {children} <span className="required-mark">*</span>
    </>
  );
}

function validateForm(
  form: JobFormData,
  categorySelection: CategorySelection | null,
  customVerifyResult: CustomRoleVerifyResult | null,
): FormErrors {
  const errors: FormErrors = {};

  if (!isCategorySelectionValid(categorySelection, customVerifyResult)) {
    if (categorySelection?.is_custom) {
      errors.category_id = "Проверьте название должности перед отправкой";
    } else {
      errors.category_id = "Выберите группу и должность";
    }
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

  if (!form.address.trim()) {
    errors.address = "Укажите адрес";
  } else if (form.address.length > 300) {
    errors.address = "Не более 300 символов";
  }

  const e164 = buildE164Phone(form.phone_country_code, form.contact_phone_national);
  const normalizedUsername = normalizeTelegramUsername(form.telegram_username);
  const hasPhone = e164 !== null;
  const hasTelegram = normalizedUsername.length > 0;

  if (!hasPhone && !hasTelegram) {
    errors.contact = "Укажите телефон или Telegram";
  } else if (form.contact_phone_national.trim() && !hasPhone) {
    errors.contact_phone = "Некорректный номер телефона";
  } else if (
    hasTelegram &&
    !/^[a-zA-Z][a-zA-Z0-9_]{4,31}$/.test(normalizedUsername)
  ) {
    errors.telegram_username = "Некорректное имя в Telegram";
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

  if (form.dress_code.trim() && form.dress_code.length > 200) {
    errors.dress_code = "Не более 200 символов";
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

function validationSummary(errors: FormErrors): string | null {
  const messages = [...new Set(Object.values(errors).filter(Boolean))];
  if (messages.length === 0) {
    return null;
  }
  if (messages.length === 1) {
    return messages[0]!;
  }
  return `Исправьте ${messages.length} ошибок в форме (см. поля выше)`;
}

function scrollToFirstError() {
  requestAnimationFrame(() => {
    const card = document.querySelector(".job-form-card");
    const target =
      card?.querySelector(".validation-summary") ??
      card?.querySelector(".field-error") ??
      card?.querySelector(".error");
    target?.scrollIntoView({ behavior: "smooth", block: "center" });
  });
}

function formToPayload(form: JobFormData): JobRequestCreate {
  const username = normalizeTelegramUsername(form.telegram_username);
  return {
    category_id: Number(form.category_id),
    title: form.title.trim(),
    description: form.description.trim(),
    metro_station_id: form.metro_station_id!,
    address: form.address.trim(),
    hourly_rate: Math.min(Number(form.hourly_rate), MAX_HOURLY_RATE).toFixed(2),
    workers_needed: Number(form.workers_needed),
    min_experience_months: form.min_experience_months.trim()
      ? Number(form.min_experience_months)
      : null,
    required_gender: (form.required_gender || null) as RequiredGender | null,
    min_age: form.min_age.trim() ? Number(form.min_age) : null,
    max_age: form.max_age.trim() ? Number(form.max_age) : null,
    dress_code: form.dress_code.trim() || null,
    contact_phone: buildE164Phone(form.phone_country_code, form.contact_phone_national),
    telegram_username: username || null,
    includes_lunch: form.includes_lunch,
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
  const [categorySelection, setCategorySelection] = useState<CategorySelection | null>(null);
  const [customVerifyResult, setCustomVerifyResult] = useState<CustomRoleVerifyResult | null>(null);
  const [preferredCountryCode, setPreferredCountryCode] = useState("+7");
  const [customCountryCodes, setCustomCountryCodes] = useState<string[]>([]);
  const [countryCodeOptions, setCountryCodeOptions] = useState<CountryCodeOption[]>(() =>
    buildCountryCodeOptions(),
  );
  const [showCustomCodeInput, setShowCustomCodeInput] = useState(false);
  const [customCodeDraft, setCustomCodeDraft] = useState("");
  const [customCodeError, setCustomCodeError] = useState<string | null>(null);
  const [form, setForm] = useState<JobFormData>(() => emptyForm());
  const [formErrors, setFormErrors] = useState<FormErrors>({});
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [showOptional, setShowOptional] = useState(false);
  const [telegramFillError, setTelegramFillError] = useState<string | null>(null);

  const phoneInputRef = useRef<HTMLInputElement>(null);
  const phoneCaretRef = useRef<number | null>(null);

  const telegramUsername = getTelegramUsername();
  const telegramUserId = getTelegramUserId();

  const {
    metroQuery,
    setMetroQuery,
    metroResults,
    metroLoading,
    handleMetroFocus,
    handleMetroBlur,
    recordMetroSelection,
    resetMetroSearch,
  } = useMetroStationSearch({ telegramUserId });

  function applyPhonePrefs(prefs: PhoneCountryPrefs) {
    setPreferredCountryCode(prefs.preferred);
    setCustomCountryCodes(prefs.customCodes);
    setCountryCodeOptions(buildCountryCodeOptions(prefs.customCodes));
    setForm((prev) => ({ ...prev, phone_country_code: prefs.preferred }));
  }

  async function persistPhoneCountryPref(preferred: string, customCodes: string[]) {
    const localPrefs: PhoneCountryPrefs = { preferred, customCodes };
    savePhoneCountryPrefs(telegramUserId, localPrefs);
    try {
      const profile = await updateEmployerPhoneCountryPref(initData, preferred);
      applyPhonePrefs({
        preferred: profile.preferred_phone_country_code,
        customCodes: profile.custom_phone_country_codes,
      });
    } catch {
      applyPhonePrefs(localPrefs);
    }
  }

  useEffect(() => {
    let cancelled = false;
    void getEmployerPhoneCountryPrefs(initData)
      .then((profile) => {
        if (!cancelled) {
          applyPhonePrefs({
            preferred: profile.preferred_phone_country_code || "+7",
            customCodes: profile.custom_phone_country_codes ?? [],
          });
        }
      })
      .catch(() => {
        if (cancelled) {
          return;
        }
        const cached = loadPhoneCountryPrefs(telegramUserId);
        if (cached) {
          applyPhonePrefs(cached);
          return;
        }
        applyPhonePrefs(defaultPhoneCountryPrefs());
      });
    return () => {
      cancelled = true;
    };
  }, [initData, telegramUserId]);

  useEffect(() => {
    const { category_id, title } = categorySelectionToFormFields(categorySelection);
    setForm((prev) => ({ ...prev, category_id, title }));
    setFormErrors((prev) => ({ ...prev, category_id: undefined, title: undefined }));
  }, [categorySelection]);

  useEffect(() => {
    if (phoneCaretRef.current === null || !phoneInputRef.current) {
      return;
    }
    const caret = phoneCaretRef.current;
    phoneCaretRef.current = null;
    phoneInputRef.current.setSelectionRange(caret, caret);
  }, [form.contact_phone_national, form.phone_country_code]);

  function updateField<K extends keyof JobFormData>(key: K, value: JobFormData[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
    setFormErrors((prev) => ({
      ...prev,
      [key]: undefined,
      ...(key === "phone_country_code" ||
      key === "contact_phone_national" ||
      key === "telegram_username"
        ? { contact: undefined }
        : {}),
    }));
    setSaveError(null);
    setValidationMessage(null);
  }

  function updateNationalPhone(value: string) {
    updateField("contact_phone_national", value);
  }

  function handleCountryCodeChange(value: string) {
    setCustomCodeError(null);
    if (value === CUSTOM_COUNTRY_CODE) {
      setShowCustomCodeInput(true);
      setCustomCodeDraft("");
      return;
    }
    setShowCustomCodeInput(false);
    updateField("phone_country_code", value);
  }

  function confirmCustomCountryCode() {
    const normalized = normalizeCountryCode(customCodeDraft);
    if (!isValidCountryCode(normalized)) {
      setCustomCodeError("Введите код в формате + и цифры (например +49)");
      return;
    }
    setCustomCodeError(null);
    setShowCustomCodeInput(false);
    updateField("phone_country_code", normalized);
    const nextCustomCodes =
      DEFAULT_COUNTRY_CODES.some((item) => item.value === normalized) ||
      customCountryCodes.includes(normalized)
        ? customCountryCodes
        : [...customCountryCodes, normalized];
    void persistPhoneCountryPref(normalized, nextCustomCodes);
  }

  const selectCountryValue =
    showCustomCodeInput ||
    !countryCodeOptions.some(
      (option) => option.value !== CUSTOM_COUNTRY_CODE && option.value === form.phone_country_code,
    )
      ? CUSTOM_COUNTRY_CODE
      : form.phone_country_code;

  function fillTelegramUsername() {
    const username = getTelegramUsername();
    if (!username) {
      setTelegramFillError("У аккаунта Telegram не задан @username");
      return;
    }
    setTelegramFillError(null);
    updateField("telegram_username", username);
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
    setValidationMessage(null);
  }

  function addShift() {
    setForm((prev) => ({ ...prev, shift_slots: [...prev.shift_slots, { ...EMPTY_SHIFT }] }));
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
    recordMetroSelection(station);
  }

  function clearMetro() {
    updateField("metro_station_id", null);
    updateField("metro_label", "");
    resetMetroSearch();
  }

  async function handleSubmit(publish: boolean) {
    const errors = validateForm(form, categorySelection, customVerifyResult);
    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      setValidationMessage(validationSummary(errors));
      setSaveError(null);
      scrollToFirstError();
      return;
    }

    setIsSaving(true);
    setSaveError(null);
    setValidationMessage(null);

    try {
      const job = await createJob(initData, formToPayload(form));
      if (publish) {
        await updateJobStatus(initData, job.id, "active");
      }
      setForm(emptyForm(preferredCountryCode));
      setCategorySelection(null);
      setCustomVerifyResult(null);
      resetMetroSearch();
      setShowCustomCodeInput(false);
      onCreated?.();
    } catch (err) {
      if (err instanceof ContentRejectedError && err.field) {
        setFormErrors((prev) => ({ ...prev, [err.field!]: err.message }));
        setValidationMessage(err.message);
        scrollToFirstError();
        return;
      }
      setSaveError(
        err instanceof ContentRejectedError || err instanceof Error
          ? err.message
          : "Не удалось сохранить заявку",
      );
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <section className="card job-form-card">
      <h2>Новая заявка</h2>

      <form
        className="profile-form"
        onSubmit={(e) => {
          e.preventDefault();
          void handleSubmit(false);
        }}
      >
        <CategoryPicker
          initData={initData}
          context="employer"
          value={categorySelection}
          onChange={setCategorySelection}
          disabled={isSaving}
          error={formErrors.category_id ?? null}
          allowCustomRole
          customVerifyResult={customVerifyResult}
          onCustomVerifyResultChange={setCustomVerifyResult}
        />

        {categorySelection && !categorySelection.is_custom ? (
          <p className="hint">Название заявки: {form.title}</p>
        ) : null}
        {formErrors.title ? <em className="field-error">{formErrors.title}</em> : null}

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
            onFocus={handleMetroFocus}
            onBlur={handleMetroBlur}
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
            max={MAX_HOURLY_RATE}
            step="0.01"
            inputMode="decimal"
            value={form.hourly_rate}
            disabled={isSaving}
            onWheel={preventNumberInputWheel}
            onChange={(e) => updateField("hourly_rate", clampHourlyRateInput(e.target.value))}
            onBlur={(e) => updateField("hourly_rate", clampHourlyRateInput(e.target.value))}
          />
          {formErrors.hourly_rate ? <em className="field-error">{formErrors.hourly_rate}</em> : null}
        </label>

        <label className="form-field">
          <span>Работников на смену</span>
          <input
            type="number"
            min={1}
            max={100}
            inputMode="numeric"
            value={form.workers_needed}
            disabled={isSaving}
            onWheel={preventNumberInputWheel}
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

        <label className="form-field">
          <span>
            <RequiredLabel>Адрес</RequiredLabel>
          </span>
          <input
            type="text"
            maxLength={300}
            value={form.address}
            disabled={isSaving}
            onChange={(e) => updateField("address", e.target.value)}
          />
          {formErrors.address ? <em className="field-error">{formErrors.address}</em> : null}
        </label>

        <div className="form-field">
          <span>Контакты для связи</span>
          <p className="hint">Укажите телефон или Telegram (хотя бы одно поле)</p>
          {formErrors.contact ? <em className="field-error">{formErrors.contact}</em> : null}

          <label className="form-field compact">
            <span>Телефон</span>
            <div className={`phone-input-row${showCustomCodeInput ? " phone-input-row--custom" : ""}`}>
              <select
                className="phone-country-code"
                value={selectCountryValue}
                disabled={isSaving}
                aria-label="Код страны"
                onChange={(e) => handleCountryCodeChange(e.target.value)}
              >
                {countryCodeOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
              {showCustomCodeInput ? (
                <div className="phone-custom-code">
                  <input
                    type="tel"
                    inputMode="tel"
                    className="phone-custom-code-input"
                    placeholder="+49"
                    value={customCodeDraft}
                    disabled={isSaving}
                    aria-label="Другой код страны"
                    onChange={(e) => {
                      setCustomCodeError(null);
                      setCustomCodeDraft(e.target.value);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        confirmCustomCountryCode();
                      }
                    }}
                  />
                  <button
                    type="button"
                    className="btn telegram-fill-btn phone-custom-code-btn"
                    disabled={isSaving}
                    onClick={confirmCustomCountryCode}
                  >
                    OK
                  </button>
                </div>
              ) : (
                <input
                  ref={phoneInputRef}
                  type="tel"
                  inputMode="tel"
                  autoComplete="tel-national"
                  placeholder="(999) 000-00-00"
                  value={formatNationalPhone(form.contact_phone_national, form.phone_country_code)}
                  disabled={isSaving}
                  onChange={(e) =>
                    updateNationalPhone(extractNationalDigits(e.target.value, form.phone_country_code))
                  }
                  onKeyDown={(e) =>
                    handlePhoneKeyDown(
                      e,
                      form.contact_phone_national,
                      form.phone_country_code,
                      updateNationalPhone,
                      (index) => {
                        phoneCaretRef.current = index;
                      },
                    )
                  }
                />
              )}
            </div>
            {customCodeError ? <em className="field-error">{customCodeError}</em> : null}
            {formErrors.contact_phone ? (
              <em className="field-error">{formErrors.contact_phone}</em>
            ) : null}
          </label>

          <div className="form-field compact">
            <span>ТГ имя</span>
            <div className="telegram-input-row">
              <div className="telegram-input-field">
                <span className="telegram-at-prefix" aria-hidden="true">
                  @
                </span>
                <input
                  type="text"
                  autoComplete="off"
                  spellCheck={false}
                  placeholder="username"
                  value={normalizeTelegramUsername(form.telegram_username)}
                  disabled={isSaving}
                  onChange={(e) => {
                    setTelegramFillError(null);
                    updateField("telegram_username", normalizeTelegramUsername(e.target.value));
                  }}
                />
              </div>
              <button
                type="button"
                className="btn secondary telegram-fill-btn"
                disabled={isSaving || !telegramUsername}
                title={
                  telegramUsername
                    ? `Подставить @${telegramUsername}`
                    : "У аккаунта Telegram не задан @username"
                }
                onClick={fillTelegramUsername}
              >
                Свой ник
              </button>
            </div>
            {telegramFillError ? <em className="field-error">{telegramFillError}</em> : null}
            {!telegramUsername && !telegramFillError ? (
              <p className="hint">@username не задан в Telegram — кнопка «Свой ник» недоступна</p>
            ) : null}
            {formErrors.telegram_username ? (
              <em className="field-error">{formErrors.telegram_username}</em>
            ) : null}
          </div>
        </div>

        <label className="form-field checkbox-field">
          <input
            type="checkbox"
            checked={form.includes_lunch}
            disabled={isSaving}
            onChange={(e) => updateField("includes_lunch", e.target.checked)}
          />
          <span>Входит обед</span>
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

        <button
          type="button"
          className="link-btn optional-toggle"
          onClick={() => setShowOptional((value) => !value)}
        >
          {showOptional ? "Скрыть доп. поля" : "Дополнительные поля"}
        </button>

        {showOptional ? (
          <div className="optional-fields">
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
              {formErrors.dress_code ? <em className="field-error">{formErrors.dress_code}</em> : null}
            </label>
          </div>
        ) : null}

        {validationMessage ? <p className="validation-summary">{validationMessage}</p> : null}
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
