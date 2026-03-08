import { useCallback, useEffect, useMemo, useState } from 'react';
import { fetchLauncherStatus, launchViaLocalService } from '../api/launcherClient';
import type { LaunchRequestPayload, LaunchResponse, LauncherStatusResponse, NodeView, ProtocolCapability, ProtocolLaunch, ProtocolKind } from '../types';

const STORAGE_KEYS = {
  baseUrl: 'omniview.launcher.baseUrl',
  token: 'omniview.launcher.token',
} as const;

const DEFAULT_BASE_URL = 'http://127.0.0.1:32145';

interface LauncherSettingsState {
  baseUrl: string;
  token: string;
}

interface UseLauncherResult {
  settings: LauncherSettingsState;
  connected: boolean;
  probing: boolean;
  error: string | null;
  status: LauncherStatusResponse | null;
  capabilityFor: (kind: ProtocolKind) => ProtocolCapability | undefined;
  saveSettings: (baseUrl: string, token: string) => Promise<void>;
  probe: () => Promise<void>;
  launch: (node: NodeView, protocol: ProtocolLaunch) => Promise<LaunchResponse>;
}

function readStorage(key: string, fallback: string): string {
  if (typeof window === 'undefined') {
    return fallback;
  }
  return window.localStorage.getItem(key) ?? fallback;
}

function writeStorage(key: string, value: string): void {
  if (typeof window === 'undefined') {
    return;
  }
  window.localStorage.setItem(key, value);
}

function buildLaunchPayload(node: NodeView, protocol: ProtocolLaunch): LaunchRequestPayload {
  return {
    node_id: node.node_id,
    node_name: node.name,
    overlay_ip: node.overlay_ip,
    platform: node.platform,
    protocol: protocol.kind,
    label: protocol.label,
    host: protocol.host,
    port: protocol.port,
    username: protocol.username,
    path: protocol.path,
    app_name: protocol.app_name,
    launch_uri: protocol.launch_uri,
  };
}

export function useLauncher(): UseLauncherResult {
  const [settings, setSettings] = useState<LauncherSettingsState>(() => ({
    baseUrl: readStorage(STORAGE_KEYS.baseUrl, DEFAULT_BASE_URL),
    token: readStorage(STORAGE_KEYS.token, ''),
  }));
  const [status, setStatus] = useState<LauncherStatusResponse | null>(null);
  const [probing, setProbing] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const capabilityMap = useMemo(
    () => new Map<ProtocolKind, ProtocolCapability>((status?.protocols ?? []).map((capability) => [capability.kind, capability])),
    [status],
  );

  const probe = useCallback(async () => {
    setProbing(true);
    try {
      const next = await fetchLauncherStatus(settings.baseUrl);
      setStatus(next);
      setError(null);
    } catch (err) {
      setStatus(null);
      setError(err instanceof Error ? err.message : 'Unable to reach the local launcher');
    } finally {
      setProbing(false);
    }
  }, [settings.baseUrl]);

  const saveSettings = useCallback(async (baseUrl: string, token: string) => {
    writeStorage(STORAGE_KEYS.baseUrl, baseUrl);
    writeStorage(STORAGE_KEYS.token, token);
    setSettings({ baseUrl, token });
    setProbing(true);
    try {
      const next = await fetchLauncherStatus(baseUrl);
      setStatus(next);
      setError(null);
    } catch (err) {
      setStatus(null);
      setError(err instanceof Error ? err.message : 'Unable to reach the local launcher');
    } finally {
      setProbing(false);
    }
  }, []);

  useEffect(() => {
    void probe();
  }, [probe]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      void probe();
    }, 30000);
    return () => window.clearInterval(timer);
  }, [probe]);

  const launch = useCallback(
    async (node: NodeView, protocol: ProtocolLaunch) => {
      return launchViaLocalService(settings.baseUrl, buildLaunchPayload(node, protocol), settings.token || undefined);
    },
    [settings.baseUrl, settings.token],
  );

  return {
    settings,
    connected: Boolean(status),
    probing,
    error,
    status,
    capabilityFor: (kind) => capabilityMap.get(kind),
    saveSettings,
    probe,
    launch,
  };
}
