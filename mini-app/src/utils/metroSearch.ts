import type { MetroStation } from "../api/client";

const RECENT_KEY_PREFIX = "metro_recent_stations_";
const RECENT_KEY_ANONYMOUS = "metro_recent_stations";

function recentStorageKey(telegramUserId: number | null): string {
  return telegramUserId === null ? RECENT_KEY_ANONYMOUS : `${RECENT_KEY_PREFIX}${telegramUserId}`;
}

function isMetroStation(value: unknown): value is MetroStation {
  if (!value || typeof value !== "object") {
    return false;
  }
  const station = value as Record<string, unknown>;
  return (
    typeof station.id === "number" &&
    typeof station.name === "string" &&
    typeof station.line_name === "string"
  );
}

export function loadRecentMetroStations(telegramUserId: number | null): MetroStation[] {
  if (typeof localStorage === "undefined") {
    return [];
  }
  try {
    const raw = localStorage.getItem(recentStorageKey(telegramUserId));
    if (!raw) {
      return [];
    }
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter(isMetroStation).slice(0, 8) : [];
  } catch {
    return [];
  }
}

export function saveRecentMetroStation(
  telegramUserId: number | null,
  station: MetroStation,
): MetroStation[] {
  if (typeof localStorage === "undefined") {
    return [station];
  }
  const updated = [station, ...loadRecentMetroStations(telegramUserId).filter((s) => s.id !== station.id)].slice(
    0,
    8,
  );
  localStorage.setItem(recentStorageKey(telegramUserId), JSON.stringify(updated));
  return updated;
}

function tokenize(text: string): string[] {
  return text.split(/[\s\-–—,.]+/).filter((token) => token.length > 0);
}

function normalizeSearchText(text: string): string {
  return text.toLocaleLowerCase("ru");
}

function rankMatch(text: string, query: string): number | null {
  const normalizedQuery = normalizeSearchText(query.trim());
  if (!normalizedQuery) {
    return null;
  }
  for (const token of tokenize(text)) {
    if (normalizeSearchText(token).startsWith(normalizedQuery)) {
      return 0;
    }
  }
  return normalizeSearchText(text).includes(normalizedQuery) ? 1 : null;
}

/** Filter and rank metro stations by search query. */
export function filterMetroStations(stations: MetroStation[], query: string): MetroStation[] {
  const trimmed = query.trim();
  if (!trimmed) {
    return [...stations].sort((a, b) => a.name.localeCompare(b.name, "ru"));
  }

  const ranked = stations
    .map((station) => ({ station, rank: rankMatch(station.name, trimmed) }))
    .filter((entry) => entry.rank !== null);

  ranked.sort((a, b) =>
    a.rank === b.rank
      ? a.station.name.localeCompare(b.station.name, "ru")
      : a.rank! - b.rank!,
  );

  return ranked.map((entry) => entry.station);
}
