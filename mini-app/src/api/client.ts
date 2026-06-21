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

export function getWorkerProfile(initData: string): Promise<WorkerProfile> {
  return apiFetch<WorkerProfile>("/worker/profile", initData);
}

export type MetroStation = {
  id: number;
  name: string;
  line_name: string;
};

export type WorkerProfileUpdate = Pick<
  WorkerProfile,
  "first_name" | "last_name" | "age" | "gender" | "metro_station_id" | "min_hourly_rate"
>;

export function updateWorkerProfile(
  initData: string,
  data: WorkerProfileUpdate,
): Promise<WorkerProfile> {
  return apiFetch<WorkerProfile>("/worker/profile", initData, {
    method: "PUT",
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
