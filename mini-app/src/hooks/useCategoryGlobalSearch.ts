import { useEffect, useState } from "react";
import { searchCategories } from "../api/client";
import { filterCategorySearchResults } from "../utils/categorySearch";
import type { CategorySearchResult } from "../api/client";

type UseCategoryGlobalSearchOptions = {
  enabled?: boolean;
};

export function useCategoryGlobalSearch({ enabled = true }: UseCategoryGlobalSearchOptions = {}) {
  const [categoryQuery, setCategoryQuery] = useState("");
  const [categoryResults, setCategoryResults] = useState<CategorySearchResult[]>([]);
  const [categoryLoading, setCategoryLoading] = useState(false);
  const [categoryFocused, setCategoryFocused] = useState(false);

  useEffect(() => {
    if (!enabled) {
      setCategoryResults([]);
      setCategoryLoading(false);
      return;
    }

    const query = categoryQuery.trim();
    if (query.length < 1) {
      setCategoryLoading(false);
      setCategoryResults([]);
      return;
    }

    let cancelled = false;
    const timer = window.setTimeout(() => {
      setCategoryLoading(true);
      void searchCategories(query)
        .then((results) => {
          if (!cancelled) {
            setCategoryResults(filterCategorySearchResults(results, query));
          }
        })
        .catch(() => {
          if (!cancelled) {
            setCategoryResults([]);
          }
        })
        .finally(() => {
          if (!cancelled) {
            setCategoryLoading(false);
          }
        });
    }, 300);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [categoryFocused, categoryQuery, enabled]);

  function handleCategoryFocus() {
    setCategoryFocused(true);
  }

  function handleCategoryBlur() {
    window.setTimeout(() => setCategoryFocused(false), 150);
  }

  function resetCategorySearch() {
    setCategoryQuery("");
    setCategoryResults([]);
    setCategoryFocused(false);
    setCategoryLoading(false);
  }

  return {
    categoryQuery,
    setCategoryQuery,
    categoryResults,
    categoryLoading,
    categoryFocused,
    handleCategoryFocus,
    handleCategoryBlur,
    resetCategorySearch,
  };
}
