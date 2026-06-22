const API_BASE =
  import.meta.env.VITE_API_BASE_URL ??
  (import.meta.env.PROD ? "" : "http://localhost:8000");

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
  verification_status: "pending" | "verified" | "rejected";
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

export type EmployerApplicationRead = {
  id: string;
  job_request_id: string;
  shift_slot_id: string;
  status: ApplicationStatus;
  applied_at: string;
  shift_date: string;
  start_time: string;
  end_time: string;
  worker_id: string;
  worker_first_name: string;
  worker_last_name: string;
  worker_age: number;
  worker_experience_months: number | null;
};

export type EmployerApplicationListResponse = {
  items: EmployerApplicationRead[];
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
  const response = await fetch(`${API_BASE}/api/v1${path}`, {
    ...init,
    headers: {
      ...authHeaders(initData),
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

async function publicFetch<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}/api/v1${path}`);
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `HTTP ${response.status}`);
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

export function listJobApplications(
  initData: string,
  jobId: string,
): Promise<EmployerApplicationListResponse> {
  return apiFetch<EmployerApplicationListResponse>(`/employer/jobs/${jobId}/applications`, initData);
}

export function updateEmployerApplication(
  initData: string,
  applicationId: string,
  status: "accepted" | "rejected",
): Promise<EmployerApplicationRead> {
  return apiFetch<EmployerApplicationRead>(`/employer/applications/${applicationId}`, initData, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
}

export type ReviewCreate = {
  application_id: string;
  reviewer_role: "worker" | "employer";
  rating: number;
  comment?: string | null;
};

export type ReviewRead = {
  id: string;
  application_id: string;
  reviewer_user_id: string;
  reviewed_user_id: string;
  reviewer_role: "worker" | "employer";
  rating: number;
  comment: string | null;
  created_at: string;
};

export function createReview(initData: string, data: ReviewCreate): Promise<ReviewRead> {
  return apiFetch<ReviewRead>("/reviews", initData, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function searchMetroStations(q: string): Promise<MetroStation[]> {
  const params = new URLSearchParams();
  if (q.trim()) {
    params.set("q", q.trim());
  }
  const query = params.toString();
  const response = await fetch(`${API_BASE}/api/v1/reference/metro${query ? `?${query}` : ""}`);
  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || `HTTP ${response.status}`);
  }
  return response.json() as Promise<MetroStation[]>;
}
