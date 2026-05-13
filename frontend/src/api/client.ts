import type {
  Match,
  Prediction,
  SimulationResponse,
  Team,
} from "../types";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

function authHeaders(): HeadersInit {
  const t = localStorage.getItem("token");
  return t ? { Authorization: `Bearer ${t}` } : {};
}

async function http<T>(path: string, init: RequestInit = {}): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(init.headers ?? {}),
    },
  });
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(`HTTP ${resp.status}: ${text}`);
  }
  return resp.json();
}

export const api = {
  teamsByGroup: () => http<Record<string, Team[]>>("/teams/by-group"),
  matches: (params: { stage?: string; group?: string } = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v) as [string, string][],
    ).toString();
    return http<Match[]>(`/matches${qs ? "?" + qs : ""}`);
  },
  predictMatch: (id: number) =>
    http<Prediction>(`/predictions/match/${id}`, { method: "POST" }),
  predictGroup: (group: string) =>
    http<Prediction[]>(`/predictions/group/${group}`, { method: "POST" }),
  predictAllGroups: () =>
    http<Prediction[]>(`/predictions/groups/all`, { method: "POST" }),
  predictStage: (stage: string) =>
    http<Prediction[]>(`/predictions/stage/${stage}`, { method: "POST" }),
  runSimulation: (n_runs?: number) =>
    http<SimulationResponse>(`/simulation/run${n_runs ? `?n_runs=${n_runs}` : ""}`, {
      method: "POST",
    }),
  seedR32: () =>
    http<{ stage: string; created: number }>("/bracket/seed-r32", { method: "POST" }),
  seedNext: (stage: string) =>
    http<{ stage: string; created: number }>(`/bracket/seed-next/${stage}`, {
      method: "POST",
    }),
  autoFillBracket: () =>
    http<{
      stages_seeded: string[];
      champion_team_id: number | null;
      predictions: Prediction[];
    }>("/bracket/auto-fill", { method: "POST" }),
  register: (username: string, email: string, password: string) =>
    http<{ access_token: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ username, email, password }),
    }),
  login: async (username: string, password: string) => {
    const body = new URLSearchParams({ username, password });
    const resp = await fetch(`${BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    if (!resp.ok) throw new Error("Login failed");
    return (await resp.json()) as { access_token: string };
  },
};
