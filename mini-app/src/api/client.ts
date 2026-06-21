const API_BASE =
  import.meta.env.VITE_API_BASE_URL ??
  (import.meta.env.PROD ? "" : "http://localhost:8000");

const REQUEST_TIMEOUT_MS = 10_000;

async function fetchWithTimeout(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    return await fetch(input, {
      ...init,
      signal: init?.signal ?? controller.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error("Сервер не отвечает. Проверьте интернет и попробуйте снова.");
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}

export type WorkerExperience = {
  id: string;
  category_id: number;
  category_name: string;
  role_title: string;
  duration_months: number;
  description: string | null;
};

export type WorkerProfile = {
  id: string;
  first_name: string;
  last_name: string;
  age: number;
  gender: string | null;
  metro_station_id: number | null;
  metro_station_name: string | null;
  min_hourly_rate: string | null;
  resume_completed: boolean;
  experiences: WorkerExperience[];
};

export type MeResponse = {
  id: string;
  telegram_id: number;
  username: string | null;
  role: "worker" | "employer" | "both" | "admin";
  has_worker_profile: boolean;
  has_employer_profile: boolean;
};

export type EmployerProfile = {
  id: string;
  company_name: string;
  contact_phone: string | null;
  contact_person: string | null;
  verified: boolean;
};

export type EmployerProfileUpdate = {
  company_name: string;
  contact_phone?: string | null;
  contact_person?: string | null;
};

export type JobCategory = {
  id: number;
  slug: string;
  name_ru: string;
};

export type JobRequestStatus = "draft" | "active" | "filled" | "cancelled" | "expired";

export const JOB_REQUEST_STATUS_LABELS: Record<JobRequestStatus, string> = {
  draft: "Черновик",
  active: "Активна",
  filled: "Закрыта",
  cancelled: "Отменена",
  expired: "Истекла",
};

export function formatJobRequestStatus(status: JobRequestStatus): string {
  return JOB_REQUEST_STATUS_LABELS[status] ?? status;
}

export type RequiredGender = "any" | "male" | "female";

export type ShiftSlotCreate = {
  shift_date: string;
  start_time: string;
  end_time: string;
  slots_total?: number | null;
};

export type ShiftSlot = {
  id: string;
  shift_date: string;
  start_time: string;
  end_time: string;
  slots_total: number;
  slots_filled: number;
};

export type VacancyListItem = {
  id: string;
  category_id: number;
  category_name: string | null;
  title: string;
  metro_station_id: number;
  metro_station_name: string | null;
  hourly_rate: string;
  workers_needed: number;
  next_shift_date: string | null;
  next_shift_start: string | null;
  next_shift_end: string | null;
  available_slots: number;
  includes_lunch: boolean;
};

export type VacancyListResponse = {
  items: VacancyListItem[];
  total: number;
  page: number;
  limit: number;
};

export type VacancyDetail = {
  id: string;
  category_id: number;
  category_name: string | null;
  title: string;
  description: string;
  metro_station_id: number;
  metro_station_name: string | null;
  address: string | null;
  hourly_rate: string;
  workers_needed: number;
  min_experience_months: number | null;
  dress_code: string | null;
  includes_lunch: boolean;
  shift_slots: ShiftSlot[];
  created_at: string;
};

export type VacancyListParams = {
  category_id?: number;
  metro_station_id?: number;
  min_hourly_rate?: string;
  page?: number;
  limit?: number;
};

export type ApplicationStatus =
  | "pending"
  | "accepted"
  | "rejected"
  | "cancelled_by_worker"
  | "cancelled_by_employer";

export const APPLICATION_STATUS_LABELS: Record<ApplicationStatus, string> = {
  pending: "На рассмотрении",
  accepted: "Принят",
  rejected: "Отклонён",
  cancelled_by_worker: "Отменён вами",
  cancelled_by_employer: "Отменён работодателем",
};

export type ApplicationRead = {
  id: string;
  job_request_id: string;
  shift_slot_id: string;
  status: ApplicationStatus;
  applied_at: string;
  cancelled_at: string | null;
  job_title: string;
  category_name: string | null;
  metro_station_name: string | null;
  hourly_rate: string;
  shift_date: string;
  start_time: string;
  end_time: string;
};

export type ApplicationListResponse = {
  items: ApplicationRead[];
  total: number;
};

export type ShiftConflictBody = {
  detail: string;
  conflicting: {
    application_id: string;
    shift_date: string;
    start_time: string;
    end_time: string;
    job_title: string;
  };
};

export class ShiftConflictError extends Error {
  conflict: ShiftConflictBody;

  constructor(conflict: ShiftConflictBody) {
    super(conflict.detail);
    this.name = "ShiftConflictError";
    this.conflict = conflict;
  }
}

export type JobRequest = {
  id: string;
  category_id: number;
  category_name: string | null;
  title: string;
  description: string;
  metro_station_id: number;
  metro_station_name: string | null;
  address: string | null;
  hourly_rate: string;
  workers_needed: number;
  min_experience_months: number | null;
  required_gender: RequiredGender | null;
  min_age: number | null;
  max_age: number | null;
  dress_code: string | null;
  contact_info: string | null;
  includes_lunch: boolean;
  status: JobRequestStatus;
  post_to_groups: boolean;
  notify_matching_workers: boolean;
  shift_slots: ShiftSlot[];
  created_at: string;
  updated_at: string;
};

export type JobRequestCreate = {
  category_id: number;
  title: string;
  description: string;
  metro_station_id: number;
  address?: string | null;
  hourly_rate: string;
  workers_needed: number;
  min_experience_months?: number | null;
  required_gender?: RequiredGender | null;
  min_age?: number | null;
  max_age?: number | null;
  dress_code?: string | null;
  contact_info?: string | null;
  includes_lunch?: boolean;
  post_to_groups?: boolean;
  notify_matching_workers?: boolean;
  shift_slots: ShiftSlotCreate[];
};

export type MetroStation = {
  id: number;
  name: string;
  line_name: string;
};

export type WorkerProfileUpdate = Pick<
  WorkerProfile,
  "first_name" | "last_name" | "age" | "gender" | "metro_station_id" | "min_hourly_rate"
>;

export type WorkerExperienceCreate = {
  category_id: number;
  role_title: string;
  duration_months: number;
  description?: string | null;
};

/** Matches backend MAX_HOURLY_RATE (PostgreSQL NUMERIC(10, 2)) */
export const MAX_HOURLY_RATE = 99999999.99;

type ValidationDetail = {
  type?: string;
  loc?: (string | number)[];
  msg?: string;
  ctx?: Record<string, unknown>;
};

type ApiErrorBody = {
  detail?: string | ValidationDetail[];
};

const FIELD_LABELS: Record<string, string> = {
  hourly_rate: "Ставка",
  workers_needed: "Количество работников",
  title: "Название",
  description: "Описание",
  category_id: "Категория",
  metro_station_id: "Метро",
  address: "Адрес",
  min_experience_months: "Мин. опыт",
  min_age: "Мин. возраст",
  max_age: "Макс. возраст",
  dress_code: "Дресс-код",
  contact_info: "Контакт",
  shift_date: "Дата смены",
  start_time: "Начало смены",
  end_time: "Конец смены",
  company_name: "Название компании",
  min_hourly_rate: "Мин. ставка",
  role_title: "Должность",
  duration_months: "Срок (мес.)",
};

function fieldLabel(loc: (string | number)[] | undefined): string {
  const name = loc?.[loc.length - 1];
  if (typeof name === "string" && FIELD_LABELS[name]) {
    return FIELD_LABELS[name];
  }
  return typeof name === "string" ? name : "Поле";
}

function formatValidationDetail(item: ValidationDetail): string {
  const label = fieldLabel(item.loc);
  const fieldName = item.loc?.[item.loc.length - 1];

  switch (item.type) {
    case "less_than_equal":
      if (fieldName === "hourly_rate") {
        return `Ставка не более ${MAX_HOURLY_RATE} ₽/час`;
      }
      return `${label}: значение слишком большое`;
    case "greater_than_equal":
      return `${label}: значение слишком маленькое`;
    case "string_too_long":
      return `${label}: слишком длинное значение`;
    case "string_too_short":
      return `${label}: слишком короткое значение`;
    case "missing":
      return `${label}: обязательное поле`;
    case "value_error":
      return `${label}: ${item.msg ?? "некорректное значение"}`;
    default:
      return item.msg ? `${label}: ${item.msg}` : `${label}: некорректное значение`;
  }
}

export function parseApiError(body: string, status: number): string {
  if (!body.trim()) {
    if (status === 401) {
      return "Требуется авторизация";
    }
    if (status === 403) {
      return "Доступ запрещён";
    }
    if (status === 404) {
      return "Не найдено";
    }
    if (status >= 500) {
      return "Ошибка сервера. Попробуйте позже.";
    }
    return `Ошибка запроса (${status})`;
  }

  try {
    const parsed = JSON.parse(body) as ApiErrorBody;
    if (typeof parsed.detail === "string") {
      return parsed.detail;
    }
    if (Array.isArray(parsed.detail) && parsed.detail.length > 0) {
      return parsed.detail.map(formatValidationDetail).join("\n");
    }
  } catch {
    // not JSON — fall through
  }

  if (body.trimStart().startsWith("{")) {
    return "Ошибка сервера. Проверьте введённые данные.";
  }
  return body;
}

export type WorkerPreferences = {
  category_ids: number[];
  metro_station_ids: number[];
  min_hourly_rate: string | null;
  notifications_enabled: boolean;
};

export type WorkerPreferencesUpdate = {
  category_ids?: number[];
  metro_station_ids?: number[];
  min_hourly_rate?: string | null;
  notifications_enabled?: boolean;
};

function authHeaders(initData: string): HeadersInit {
  return {
    Authorization: `tma ${initData}`,
    "Content-Type": "application/json",
  };
}

async function apiFetch<T>(path: string, initData: string, init?: RequestInit): Promise<T> {
  const response = await fetchWithTimeout(`${API_BASE}/api/v1${path}`, {
    ...init,
    headers: {
      ...authHeaders(initData),
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(parseApiError(body, response.status));
  }
  return response.json() as Promise<T>;
}

async function publicFetch<T>(path: string): Promise<T> {
  const response = await fetchWithTimeout(`${API_BASE}/api/v1${path}`);
  if (!response.ok) {
    const body = await response.text();
    throw new Error(parseApiError(body, response.status));
  }
  return response.json() as Promise<T>;
}

export function getMe(initData: string): Promise<MeResponse> {
  return apiFetch<MeResponse>("/me", initData);
}

export function getWorkerProfile(initData: string): Promise<WorkerProfile> {
  return apiFetch<WorkerProfile>("/worker/profile", initData);
}

export function updateWorkerProfile(
  initData: string,
  data: WorkerProfileUpdate,
): Promise<WorkerProfile> {
  return apiFetch<WorkerProfile>("/worker/profile", initData, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function addWorkerExperience(
  initData: string,
  data: WorkerExperienceCreate,
): Promise<WorkerProfile> {
  return apiFetch<WorkerProfile>("/worker/experiences", initData, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function getWorkerPreferences(initData: string): Promise<WorkerPreferences> {
  return apiFetch<WorkerPreferences>("/worker/preferences", initData);
}

export function updateWorkerPreferences(
  initData: string,
  data: WorkerPreferencesUpdate,
): Promise<WorkerPreferences> {
  return apiFetch<WorkerPreferences>("/worker/preferences", initData, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function deleteWorkerExperience(initData: string, experienceId: string): Promise<WorkerProfile> {
  return apiFetch<WorkerProfile>(`/worker/experiences/${experienceId}`, initData, {
    method: "DELETE",
  });
}

export function toggleWorkerNotifications(
  initData: string,
  notifications_enabled: boolean,
): Promise<WorkerPreferences> {
  return apiFetch<WorkerPreferences>("/worker/notifications", initData, {
    method: "PATCH",
    body: JSON.stringify({ notifications_enabled }),
  });
}

export function getEmployerProfile(initData: string): Promise<EmployerProfile> {
  return apiFetch<EmployerProfile>("/employer/profile", initData);
}

export function upsertEmployerProfile(
  initData: string,
  data: EmployerProfileUpdate,
): Promise<EmployerProfile> {
  return apiFetch<EmployerProfile>("/employer/profile", initData, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export function listCategories(): Promise<JobCategory[]> {
  return publicFetch<JobCategory[]>("/reference/categories");
}

export function createJob(initData: string, data: JobRequestCreate): Promise<JobRequest> {
  return apiFetch<JobRequest>("/employer/jobs", initData, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function listEmployerJobs(initData: string): Promise<JobRequest[]> {
  return apiFetch<JobRequest[]>("/employer/jobs", initData);
}

export function getJob(initData: string, id: string): Promise<JobRequest> {
  return apiFetch<JobRequest>(`/employer/jobs/${id}`, initData);
}

export function updateJobStatus(
  initData: string,
  id: string,
  status: JobRequestStatus,
): Promise<JobRequest> {
  return apiFetch<JobRequest>(`/employer/jobs/${id}`, initData, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export function listWorkerVacancies(
  initData: string,
  params: VacancyListParams = {},
): Promise<VacancyListResponse> {
  const search = new URLSearchParams();
  if (params.category_id !== undefined) {
    search.set("category_id", String(params.category_id));
  }
  if (params.metro_station_id !== undefined) {
    search.set("metro_station_id", String(params.metro_station_id));
  }
  if (params.min_hourly_rate) {
    search.set("min_hourly_rate", params.min_hourly_rate);
  }
  if (params.page !== undefined) {
    search.set("page", String(params.page));
  }
  if (params.limit !== undefined) {
    search.set("limit", String(params.limit));
  }
  const query = search.toString();
  return apiFetch<VacancyListResponse>(`/worker/vacancies${query ? `?${query}` : ""}`, initData);
}

export function getWorkerVacancy(initData: string, id: string): Promise<VacancyDetail> {
  return apiFetch<VacancyDetail>(`/worker/vacancies/${id}`, initData);
}

export async function applyToShift(
  initData: string,
  shiftSlotId: string,
  cancelConflictingId?: string,
): Promise<ApplicationRead> {
  const response = await fetch(`${API_BASE}/api/v1/applications`, {
    method: "POST",
    headers: authHeaders(initData),
    body: JSON.stringify({
      shift_slot_id: shiftSlotId,
      cancel_conflicting_id: cancelConflictingId ?? null,
    }),
  });
  if (response.status === 409) {
    const body = (await response.json()) as ShiftConflictBody;
    if (body.conflicting) {
      throw new ShiftConflictError(body);
    }
    const text = body.detail ?? (await response.text());
    throw new Error(text || "Конфликт смен");
  }
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `HTTP ${response.status}`);
  }
  return response.json() as Promise<ApplicationRead>;
}

export function cancelApplication(initData: string, applicationId: string): Promise<ApplicationRead> {
  return apiFetch<ApplicationRead>(`/applications/${applicationId}`, initData, {
    method: "DELETE",
  });
}

export function listMyApplications(initData: string): Promise<ApplicationListResponse> {
  return apiFetch<ApplicationListResponse>("/applications/mine", initData);
}

export async function searchMetroStations(q: string): Promise<MetroStation[]> {
  const params = new URLSearchParams();
  if (q.trim()) {
    params.set("q", q.trim());
  }
  const query = params.toString();
  const response = await fetchWithTimeout(`${API_BASE}/api/v1/reference/metro${query ? `?${query}` : ""}`);
  if (!response.ok) {
    const body = await response.text();
    throw new Error(parseApiError(body, response.status));
  }
  return response.json() as Promise<MetroStation[]>;
}
