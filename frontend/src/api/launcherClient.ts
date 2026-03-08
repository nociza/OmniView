import type { LaunchRequestPayload, LaunchResponse, LauncherStatusResponse } from '../types';

function normalizeBaseUrl(baseUrl: string): string {
  return baseUrl.trim().replace(/\/$/, '');
}

function launcherHeaders(token?: string): HeadersInit {
  return token?.trim()
    ? {
        'Content-Type': 'application/json',
        'X-OMV-Token': token.trim(),
      }
    : {
        'Content-Type': 'application/json',
      };
}

export async function fetchLauncherStatus(baseUrl: string, signal?: AbortSignal): Promise<LauncherStatusResponse> {
  const response = await fetch(`${normalizeBaseUrl(baseUrl)}/api/status`, {
    signal,
    headers: {
      Accept: 'application/json',
    },
  });

  if (!response.ok) {
    throw new Error(`Launcher status request failed with status ${response.status}`);
  }

  return (await response.json()) as LauncherStatusResponse;
}

export async function launchViaLocalService(
  baseUrl: string,
  payload: LaunchRequestPayload,
  token?: string,
): Promise<LaunchResponse> {
  const response = await fetch(`${normalizeBaseUrl(baseUrl)}/api/launch`, {
    method: 'POST',
    headers: launcherHeaders(token),
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let detail = `Launch request failed with status ${response.status}`;
    try {
      const data = (await response.json()) as { detail?: string };
      if (data.detail) {
        detail = data.detail;
      }
    } catch {
      // Ignore JSON parsing failures and use the generic message.
    }
    throw new Error(detail);
  }

  return (await response.json()) as LaunchResponse;
}
