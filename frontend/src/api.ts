import type { MarketsResponse, StatsResponse, TimelineResponse } from "./types";

const API_BASE = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    throw new Error(`${path} failed: ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export interface MarketsQuery {
  platform?: string;
  search?: string;
  limit?: number;
  offset?: number;
}

export const api = {
  stats: () => get<StatsResponse>("/api/stats"),

  markets: ({ platform, search, limit = 50, offset = 0 }: MarketsQuery) => {
    const qs = new URLSearchParams();
    if (platform) qs.set("platform", platform);
    if (search) qs.set("search", search);
    qs.set("limit", String(limit));
    qs.set("offset", String(offset));
    return get<MarketsResponse>(`/api/markets?${qs.toString()}`);
  },

  ingestionTimeline: (hours = 24) =>
    get<TimelineResponse>(`/api/ingestion-timeline?hours=${hours}`),
};
