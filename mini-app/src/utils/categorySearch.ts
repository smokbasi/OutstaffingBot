import type { CategoryRole, CategorySearchResult } from "../api/client";

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

/** Filter and rank roles within a group by search query. */
export function filterRoles(roles: CategoryRole[], query: string): CategoryRole[] {
  const trimmed = query.trim();
  if (!trimmed) {
    return [...roles].sort((a, b) => a.name_ru.localeCompare(b.name_ru, "ru"));
  }

  const ranked = roles
    .map((role) => ({ role, rank: rankMatch(role.name_ru, trimmed) }))
    .filter((entry) => entry.rank !== null);

  ranked.sort((a, b) =>
    a.rank === b.rank
      ? a.role.name_ru.localeCompare(b.role.name_ru, "ru")
      : a.rank! - b.rank!,
  );

  return ranked.map((entry) => entry.role);
}

/** Filter and rank global category search results. */
export function filterCategorySearchResults(
  results: CategorySearchResult[],
  query: string,
): CategorySearchResult[] {
  const normalizedQuery = normalizeSearchText(query.trim());
  if (!normalizedQuery) {
    return [...results];
  }

  const ranked = results
    .map((item) => {
      const name = normalizeSearchText(item.name_ru);
      if (name.startsWith(normalizedQuery)) {
        return { item, rank: 0 };
      }
      if (name.includes(normalizedQuery)) {
        return { item, rank: 1 };
      }
      return null;
    })
    .filter((entry): entry is { item: CategorySearchResult; rank: number } => entry !== null);

  ranked.sort((a, b) => {
    if (a.rank !== b.rank) {
      return a.rank - b.rank;
    }
    const groupCmp = a.item.group_name_ru.localeCompare(b.item.group_name_ru, "ru");
    return groupCmp === 0 ? a.item.name_ru.localeCompare(b.item.name_ru, "ru") : groupCmp;
  });

  return ranked.map((entry) => entry.item);
}
