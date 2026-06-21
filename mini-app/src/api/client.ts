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
