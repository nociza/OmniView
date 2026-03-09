import type { DashboardResponse, SessionStatusResponse } from '../types';

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined)?.replace(/\/$/, '') ?? '';

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function fetchDashboard(signal?: AbortSignal): Promise<DashboardResponse> {
  const response = await fetch(`${API_BASE}/api/dashboard`, {
    signal,
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    throw new ApiError(`Dashboard request failed with status ${response.status}`, response.status);
  }

  return (await response.json()) as DashboardResponse;
}

export async function fetchSessionStatus(signal?: AbortSignal): Promise<SessionStatusResponse> {
  const response = await fetch(`${API_BASE}/api/session`, {
    signal,
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
    },
  });
  if (!response.ok) {
    throw new ApiError(`Session request failed with status ${response.status}`, response.status);
  }
  return (await response.json()) as SessionStatusResponse;
}

export async function createSession(token: string): Promise<SessionStatusResponse> {
  const response = await fetch(`${API_BASE}/api/session`, {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({ token }),
  });
  if (!response.ok) {
    throw new ApiError(`Sign-in failed with status ${response.status}`, response.status);
  }
  return (await response.json()) as SessionStatusResponse;
}

export async function destroySession(): Promise<SessionStatusResponse> {
  const response = await fetch(`${API_BASE}/api/session`, {
    method: 'DELETE',
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
    },
  });
  if (!response.ok) {
    throw new ApiError(`Sign-out failed with status ${response.status}`, response.status);
  }
  return (await response.json()) as SessionStatusResponse;
}
