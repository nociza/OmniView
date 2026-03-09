import { useCallback, useEffect, useState } from 'react';
import { createSession, destroySession, fetchSessionStatus } from '../api/client';

interface UseHubSessionResult {
  authenticated: boolean;
  checking: boolean;
  error: string | null;
  login: (token: string) => Promise<void>;
  logout: () => Promise<void>;
  invalidate: () => void;
}

export function useHubSession(): UseHubSessionResult {
  const [authenticated, setAuthenticated] = useState(false);
  const [checking, setChecking] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setChecking(true);
    try {
      const next = await fetchSessionStatus();
      setAuthenticated(next.authenticated);
      setError(null);
    } catch (err) {
      setAuthenticated(false);
      setError(err instanceof Error ? err.message : 'Unable to check hub session');
    } finally {
      setChecking(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const login = useCallback(async (token: string) => {
    setChecking(true);
    try {
      const next = await createSession(token);
      setAuthenticated(next.authenticated);
      setError(null);
    } catch (err) {
      setAuthenticated(false);
      setError(err instanceof Error ? err.message : 'Unable to sign in');
    } finally {
      setChecking(false);
    }
  }, []);

  const logout = useCallback(async () => {
    setChecking(true);
    try {
      await destroySession();
      setAuthenticated(false);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to sign out');
    } finally {
      setChecking(false);
    }
  }, []);

  return {
    authenticated,
    checking,
    error,
    login,
    logout,
    invalidate: () => setAuthenticated(false),
  };
}
