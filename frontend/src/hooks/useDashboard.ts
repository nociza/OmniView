import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError, fetchDashboard } from '../api/client';
import type { DashboardResponse } from '../types';

interface UseDashboardResult {
  data: DashboardResponse | null;
  loading: boolean;
  refreshing: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useDashboard(enabled: boolean, onUnauthorized: () => void): UseDashboardResult {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inflightRef = useRef(false);

  const load = useCallback(async (background = false) => {
    if (!enabled) {
      setData(null);
      setLoading(false);
      setRefreshing(false);
      return;
    }
    if (inflightRef.current) {
      return;
    }

    inflightRef.current = true;
    if (background) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    const controller = new AbortController();

    try {
      const next = await fetchDashboard(controller.signal);
      setData(next);
      setError(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setData(null);
        onUnauthorized();
      }
      if ((err as Error).name !== 'AbortError') {
        setError(err instanceof Error ? err.message : 'Unable to load dashboard');
      }
    } finally {
      inflightRef.current = false;
      setLoading(false);
      setRefreshing(false);
    }
  }, [enabled, onUnauthorized]);

  useEffect(() => {
    void load(false);
  }, [load]);

  useEffect(() => {
    const intervalMs = (data?.poll_interval_seconds ?? 15) * 1000;
    const timer = window.setInterval(() => {
      void load(true);
    }, intervalMs);

    return () => window.clearInterval(timer);
  }, [data?.poll_interval_seconds, load]);

  return {
    data,
    loading,
    refreshing,
    error,
    refresh: async () => load(true),
  };
}
