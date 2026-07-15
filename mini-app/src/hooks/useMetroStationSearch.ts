import { useEffect, useState } from "react";
import { searchMetroStations, type MetroStation } from "../api/client";
import { filterMetroStations, loadRecentMetroStations, saveRecentMetroStation } from "../utils/metroSearch";

type UseMetroStationSearchOptions = {
  telegramUserId: number | null;
  enabled?: boolean;
};

export function useMetroStationSearch({
  telegramUserId,
  enabled = true,
}: UseMetroStationSearchOptions) {
  const [metroQuery, setMetroQuery] = useState("");
  const [metroResults, setMetroResults] = useState<MetroStation[]>([]);
  const [metroLoading, setMetroLoading] = useState(false);
  const [metroFocused, setMetroFocused] = useState(false);

  useEffect(() => {
    if (!enabled) {
      setMetroResults([]);
      setMetroLoading(false);
      return;
    }

    const query = metroQuery.trim();
    if (query.length < 1) {
      setMetroLoading(false);
      setMetroResults(metroFocused ? loadRecentMetroStations(telegramUserId) : []);
      return;
    }

    let cancelled = false;
    const timer = window.setTimeout(() => {
      setMetroLoading(true);
      void searchMetroStations(query)
        .then((stations) => {
          if (!cancelled) {
            setMetroResults(filterMetroStations(stations, query));
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
      window.clearTimeout(timer);
    };
  }, [enabled, metroFocused, metroQuery, telegramUserId]);

  function handleMetroFocus() {
    setMetroFocused(true);
  }

  function handleMetroBlur() {
    window.setTimeout(() => setMetroFocused(false), 150);
  }

  function recordMetroSelection(station: MetroStation) {
    saveRecentMetroStation(telegramUserId, station);
    setMetroResults([]);
    setMetroFocused(false);
  }

  function resetMetroSearch() {
    setMetroQuery("");
    setMetroResults([]);
    setMetroFocused(false);
    setMetroLoading(false);
  }

  return {
    metroQuery,
    setMetroQuery,
    metroResults,
    metroLoading,
    handleMetroFocus,
    handleMetroBlur,
    recordMetroSelection,
    resetMetroSearch,
    setMetroResults,
  };
}
