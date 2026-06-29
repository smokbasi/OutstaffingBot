import { useEffect, useState } from "react";
import {
  addWorkerExperience,
  deleteWorkerExperience,
  getWorkerProfile,
  listCategories,
  searchMetroStations,
  updateWorkerProfile,
  type JobCategory,
  type MetroStation,
  type WorkerProfile,
} from "../api/client";

const GENDER_LABELS: Record<string, string> = {
  male: "Мужской",
  female: "Женский",
  other: "Другое",
  prefer_not_say: "Не указан",
};

const GENDER_OPTIONS = [
  { value: "", label: "Не указан" },
  { value: "male", label: "Мужской" },
  { value: "female", label: "Женский" },
  { value: "other", label: "Другое" },
  { value: "prefer_not_say", label: "Предпочитаю не говорить" },
] as const;

type ProfilePageProps = {
  initData: string;
};

type ProfileState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; profile: WorkerProfile };

type ProfileFormData = {
  first_name: string;
  last_name: string;
  age: string;
  gender: string;
  min_hourly_rate: string;
  metro_station_id: number | null;
  metro_label: string;
  show_all_vacancies: boolean;
};

type FormErrors = Partial<Record<keyof ProfileFormData, string>>;

type ExperienceFormData = {
  category_id: string;
  role_title: string;
  duration_months: string;
};

type ExperienceFormErrors = Partial<Record<keyof ExperienceFormData, string>>;

function emptyExperienceForm(): ExperienceFormData {
  return {
    category_id: "",
    role_title: "",
    duration_months: "",
  };
}

function validateExperienceForm(form: ExperienceFormData): ExperienceFormErrors {
  const errors: ExperienceFormErrors = {};
  if (!form.category_id) {
    errors.category_id = "Выберите категорию";
  }
  if (!form.role_title.trim()) {
    errors.role_title = "Укажите должность";
  } else if (form.role_title.length > 200) {
    errors.role_title = "Не более 200 символов";
  }
  const duration = Number(form.duration_months);
  if (!form.duration_months.trim() || Number.isNaN(duration)) {
    errors.duration_months = "Укажите срок в месяцах";
  } else if (duration < 0 || duration > 600) {
    errors.duration_months = "От 0 до 600 мес.";
  }
  return errors;
}

function profileToForm(profile: WorkerProfile): ProfileFormData {
  return {
    first_name: profile.first_name,
    last_name: profile.last_name,
    age: String(profile.age),
    gender: profile.gender ?? "",
    min_hourly_rate: profile.min_hourly_rate ?? "",
    metro_station_id: profile.metro_station_id,
    metro_label: profile.metro_station_name ?? "",
    show_all_vacancies: profile.show_all_vacancies,
  };
}

function validateForm(form: ProfileFormData): FormErrors {
  const errors: FormErrors = {};
  if (!form.first_name.trim()) {
    errors.first_name = "Укажите имя";
  }
  if (!form.last_name.trim()) {
    errors.last_name = "Укажите фамилию";
  }
  const age = Number(form.age);
  if (!form.age.trim() || Number.isNaN(age)) {
    errors.age = "Укажите возраст";
  } else if (age < 16 || age > 70) {
    errors.age = "Возраст от 16 до 70";
  }
  if (form.min_hourly_rate.trim()) {
    const rate = Number(form.min_hourly_rate);
    if (Number.isNaN(rate) || rate < 0) {
      errors.min_hourly_rate = "Ставка должна быть ≥ 0";
    }
  }
  return errors;
}

export function ProfilePage({ initData }: ProfilePageProps) {
  const [state, setState] = useState<ProfileState>({ status: "loading" });
  const [reloadKey, setReloadKey] = useState(0);
  const [isEditing, setIsEditing] = useState(false);
  const [form, setForm] = useState<ProfileFormData | null>(null);
  const [formErrors, setFormErrors] = useState<FormErrors>({});
  const [saveError, setSaveError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [metroQuery, setMetroQuery] = useState("");
  const [metroResults, setMetroResults] = useState<MetroStation[]>([]);
  const [metroLoading, setMetroLoading] = useState(false);
  const [isAddingExperience, setIsAddingExperience] = useState(false);
  const [categories, setCategories] = useState<JobCategory[]>([]);
  const [categoriesLoading, setCategoriesLoading] = useState(false);
  const [expForm, setExpForm] = useState<ExperienceFormData>(emptyExperienceForm);
  const [expFormErrors, setExpFormErrors] = useState<ExperienceFormErrors>({});
  const [expSaveError, setExpSaveError] = useState<string | null>(null);
  const [isExpSaving, setIsExpSaving] = useState(false);
  const [deletingExpId, setDeletingExpId] = useState<string | null>(null);
  const [isToggleSaving, setIsToggleSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadProfile() {
      try {
        const data = await getWorkerProfile(initData);
        if (!cancelled) {
          setState({ status: "ready", profile: data });
        }
      } catch (err) {
        if (cancelled) {
          return;
        }
        const message = err instanceof Error ? err.message : "Не удалось загрузить профиль";
        if (message.includes("404") || message.includes("not found")) {
          setState({
            status: "error",
            message: "Профиль не найден. Заполните его в боте: «📝 Заполнить профиль».",
          });
        } else {
          setState({ status: "error", message });
        }
      }
    }

    void loadProfile();
    return () => {
      cancelled = true;
    };
  }, [initData, reloadKey]);

  useEffect(() => {
    if (!isEditing) {
      return;
    }
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
  }, [isEditing, metroQuery]);

  useEffect(() => {
    if (!isAddingExperience) {
      return;
    }

    let cancelled = false;
    setCategoriesLoading(true);
    void listCategories()
      .then((data) => {
        if (!cancelled) {
          setCategories(data);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setCategories([]);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setCategoriesLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [isAddingExperience]);

  function startEditing(profile: WorkerProfile) {
    setForm(profileToForm(profile));
    setFormErrors({});
    setSaveError(null);
    setMetroQuery(profile.metro_station_name ?? "");
    setMetroResults([]);
    setIsEditing(true);
  }

  function cancelEditing() {
    setIsEditing(false);
    setForm(null);
    setFormErrors({});
    setSaveError(null);
    setMetroQuery("");
    setMetroResults([]);
  }

  function updateField<K extends keyof ProfileFormData>(key: K, value: ProfileFormData[K]) {
    setForm((prev) => (prev ? { ...prev, [key]: value } : prev));
    setFormErrors((prev) => ({ ...prev, [key]: undefined }));
    setSaveError(null);
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

  async function handleSave() {
    if (!form) {
      return;
    }
    const errors = validateForm(form);
    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      return;
    }

    setIsSaving(true);
    setSaveError(null);
    try {
      const updated = await updateWorkerProfile(initData, {
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        age: Number(form.age),
        gender: form.gender || null,
        metro_station_id: form.metro_station_id,
        min_hourly_rate: form.min_hourly_rate.trim() || null,
        show_all_vacancies: form.show_all_vacancies,
      });
      setState({ status: "ready", profile: updated });
      cancelEditing();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Не удалось сохранить профиль";
      setSaveError(message);
    } finally {
      setIsSaving(false);
    }
  }

  function startAddingExperience() {
    setExpForm(emptyExperienceForm());
    setExpFormErrors({});
    setExpSaveError(null);
    setIsAddingExperience(true);
  }

  function cancelAddingExperience() {
    setIsAddingExperience(false);
    setExpForm(emptyExperienceForm());
    setExpFormErrors({});
    setExpSaveError(null);
  }

  function updateExpField<K extends keyof ExperienceFormData>(key: K, value: ExperienceFormData[K]) {
    setExpForm((prev) => ({ ...prev, [key]: value }));
    setExpFormErrors((prev) => ({ ...prev, [key]: undefined }));
    setExpSaveError(null);
  }

  async function handleAddExperience() {
    const errors = validateExperienceForm(expForm);
    if (Object.keys(errors).length > 0) {
      setExpFormErrors(errors);
      return;
    }

    setIsExpSaving(true);
    setExpSaveError(null);
    try {
      await addWorkerExperience(initData, {
        category_id: Number(expForm.category_id),
        role_title: expForm.role_title.trim(),
        duration_months: Number(expForm.duration_months),
      });
      cancelAddingExperience();
      setReloadKey((k) => k + 1);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Не удалось добавить опыт";
      setExpSaveError(message);
    } finally {
      setIsExpSaving(false);
    }
  }

  async function handleToggleShowAll(checked: boolean) {
    if (state.status !== "ready") {
      return;
    }
    setIsToggleSaving(true);
    setSaveError(null);
    try {
      const updated = await updateWorkerProfile(initData, {
        first_name: state.profile.first_name,
        last_name: state.profile.last_name,
        age: state.profile.age,
        gender: state.profile.gender,
        metro_station_id: state.profile.metro_station_id,
        min_hourly_rate: state.profile.min_hourly_rate,
        show_all_vacancies: checked,
      });
      setState({ status: "ready", profile: updated });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Не удалось сохранить настройку";
      setSaveError(message);
    } finally {
      setIsToggleSaving(false);
    }
  }

  async function handleDeleteExperience(experienceId: string) {
    if (!window.confirm("Удалить эту запись об опыте?")) {
      return;
    }

    setDeletingExpId(experienceId);
    try {
      await deleteWorkerExperience(initData, experienceId);
      setReloadKey((k) => k + 1);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Не удалось удалить опыт";
      setExpSaveError(message);
    } finally {
      setDeletingExpId(null);
    }
  }

  if (state.status === "loading") {
    return <p className="status">Загрузка профиля…</p>;
  }

  if (state.status === "error") {
    return (
      <section className="card">
        <p className="error">{state.message}</p>
        <button type="button" className="btn" onClick={() => setReloadKey((k) => k + 1)}>
          Обновить
        </button>
      </section>
    );
  }

  const { profile } = state;

  if (isEditing && form) {
    return (
      <section className="card profile">
        <h2>Редактирование профиля</h2>
        <form
          className="profile-form"
          onSubmit={(e) => {
            e.preventDefault();
            void handleSave();
          }}
        >
          <label className="form-field">
            <span>Имя</span>
            <input
              type="text"
              value={form.first_name}
              maxLength={100}
              disabled={isSaving}
              onChange={(e) => updateField("first_name", e.target.value)}
            />
            {formErrors.first_name ? <em className="field-error">{formErrors.first_name}</em> : null}
          </label>

          <label className="form-field">
            <span>Фамилия</span>
            <input
              type="text"
              value={form.last_name}
              maxLength={100}
              disabled={isSaving}
              onChange={(e) => updateField("last_name", e.target.value)}
            />
            {formErrors.last_name ? <em className="field-error">{formErrors.last_name}</em> : null}
          </label>

          <label className="form-field">
            <span>Возраст</span>
            <input
              type="number"
              min={16}
              max={70}
              value={form.age}
              disabled={isSaving}
              onChange={(e) => updateField("age", e.target.value)}
            />
            {formErrors.age ? <em className="field-error">{formErrors.age}</em> : null}
          </label>

          <label className="form-field">
            <span>Пол</span>
            <select
              value={form.gender}
              disabled={isSaving}
              onChange={(e) => updateField("gender", e.target.value)}
            >
              {GENDER_OPTIONS.map((opt) => (
                <option key={opt.value || "empty"} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>

          <label className="form-field">
            <span>Мин. ставка (₽/час)</span>
            <input
              type="number"
              min={0}
              step="1"
              value={form.min_hourly_rate}
              disabled={isSaving}
              onChange={(e) => updateField("min_hourly_rate", e.target.value)}
            />
            {formErrors.min_hourly_rate ? (
              <em className="field-error">{formErrors.min_hourly_rate}</em>
            ) : null}
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

          <label className="form-field checkbox-field">
            <input
              type="checkbox"
              checked={form.show_all_vacancies}
              disabled={isSaving}
              onChange={(e) => updateField("show_all_vacancies", e.target.checked)}
            />
            <span>Показывать все вакансии</span>
          </label>

          {saveError ? <p className="error">{saveError}</p> : null}

          <div className="form-actions">
            <button type="submit" className="btn" disabled={isSaving}>
              {isSaving ? "Сохранение…" : "Сохранить"}
            </button>
            <button type="button" className="btn secondary" disabled={isSaving} onClick={cancelEditing}>
              Отмена
            </button>
          </div>
        </form>
      </section>
    );
  }

  return (
    <section className="card profile">
      <div className="profile-header">
        <h2>Профиль работника</h2>
        <button type="button" className="btn" onClick={() => startEditing(profile)}>
          Редактировать
        </button>
      </div>
      <dl className="profile-fields">
        <div>
          <dt>Имя</dt>
          <dd>
            {profile.first_name} {profile.last_name}
          </dd>
        </div>
        <div>
          <dt>Возраст</dt>
          <dd>{profile.age}</dd>
        </div>
        <div>
          <dt>Пол</dt>
          <dd>{profile.gender ? (GENDER_LABELS[profile.gender] ?? profile.gender) : "—"}</dd>
        </div>
        <div>
          <dt>Метро</dt>
          <dd>{profile.metro_station_name ?? "—"}</dd>
        </div>
        <div>
          <dt>Мин. ставка</dt>
          <dd>{profile.min_hourly_rate ? `${profile.min_hourly_rate} ₽/час` : "—"}</dd>
        </div>
      </dl>

      <label className="form-field checkbox-field profile-setting">
        <input
          type="checkbox"
          checked={profile.show_all_vacancies}
          disabled={isToggleSaving}
          onChange={(e) => void handleToggleShowAll(e.target.checked)}
        />
        <span>Показывать все вакансии</span>
      </label>
      <p className="hint">
        {profile.show_all_vacancies
          ? "В списке показываются все активные вакансии; подходящие по опыту — сверху."
          : "В списке только вакансии в категориях из вашего опыта."}
      </p>
      {saveError ? <p className="error">{saveError}</p> : null}

      <div className="experience-header">
        <h3>Опыт</h3>
        {!isAddingExperience ? (
          <button type="button" className="btn secondary experience-add-btn" onClick={startAddingExperience}>
            Добавить опыт
          </button>
        ) : null}
      </div>

      {isAddingExperience ? (
        <form
          className="profile-form experience-form"
          onSubmit={(e) => {
            e.preventDefault();
            void handleAddExperience();
          }}
        >
          <label className="form-field">
            <span>Категория</span>
            <select
              value={expForm.category_id}
              disabled={isExpSaving || categoriesLoading || categories.length === 0}
              onChange={(e) => updateExpField("category_id", e.target.value)}
            >
              <option value="">Выберите категорию…</option>
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>
                  {cat.name_ru}
                </option>
              ))}
            </select>
            {categoriesLoading ? <p className="hint">Загрузка категорий…</p> : null}
            {expFormErrors.category_id ? (
              <em className="field-error">{expFormErrors.category_id}</em>
            ) : null}
          </label>

          <label className="form-field">
            <span>Должность</span>
            <input
              type="text"
              value={expForm.role_title}
              maxLength={200}
              placeholder="Например: Старший производственной линии"
              disabled={isExpSaving}
              onChange={(e) => updateExpField("role_title", e.target.value)}
            />
            {expFormErrors.role_title ? (
              <em className="field-error">{expFormErrors.role_title}</em>
            ) : null}
          </label>

          <label className="form-field">
            <span>Срок (мес.)</span>
            <input
              type="number"
              min={0}
              max={600}
              value={expForm.duration_months}
              placeholder="10"
              disabled={isExpSaving}
              onChange={(e) => updateExpField("duration_months", e.target.value)}
            />
            {expFormErrors.duration_months ? (
              <em className="field-error">{expFormErrors.duration_months}</em>
            ) : null}
          </label>

          {expSaveError ? <p className="error">{expSaveError}</p> : null}

          <div className="form-actions">
            <button type="submit" className="btn" disabled={isExpSaving}>
              {isExpSaving ? "Сохранение…" : "Сохранить"}
            </button>
            <button
              type="button"
              className="btn secondary"
              disabled={isExpSaving}
              onClick={cancelAddingExperience}
            >
              Отмена
            </button>
          </div>
        </form>
      ) : null}

      {!isAddingExperience && expSaveError ? <p className="error">{expSaveError}</p> : null}

      {profile.experiences.length === 0 && !isAddingExperience ? (
        <p className="hint">Опыт не указан. Нажмите «Добавить опыт», чтобы указать категории для поиска вакансий.</p>
      ) : (
        <ul className="experience-list">
          {profile.experiences.map((exp) => (
            <li key={exp.id} className="experience-item">
              <div>
                <strong>{exp.category_name}</strong> — {exp.role_title}
                <span className="hint"> ({exp.duration_months} мес.)</span>
              </div>
              <button
                type="button"
                className="link-btn"
                disabled={deletingExpId === exp.id || isAddingExperience}
                onClick={() => void handleDeleteExperience(exp.id)}
              >
                {deletingExpId === exp.id ? "Удаление…" : "Удалить"}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
