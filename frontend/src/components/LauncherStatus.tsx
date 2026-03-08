import { useEffect, useState } from 'react';
import type { LauncherStatusResponse } from '../types';

interface LauncherStatusProps {
  baseUrl: string;
  token: string;
  status: LauncherStatusResponse | null;
  connected: boolean;
  probing: boolean;
  error: string | null;
  onSave: (baseUrl: string, token: string) => Promise<void>;
  onProbe: () => Promise<void>;
}

export function LauncherStatus({
  baseUrl,
  token,
  status,
  connected,
  probing,
  error,
  onSave,
  onProbe,
}: LauncherStatusProps) {
  const [draftBaseUrl, setDraftBaseUrl] = useState(baseUrl);
  const [draftToken, setDraftToken] = useState(token);

  useEffect(() => {
    setDraftBaseUrl(baseUrl);
  }, [baseUrl]);

  useEffect(() => {
    setDraftToken(token);
  }, [token]);

  return (
    <section className="launcher-panel">
      <div>
        <p className="eyebrow">Viewer launcher</p>
        <h2>Native binaries on this device</h2>
        <p className="launcher-panel__copy">
          Run <code>omv client start</code> on the machine you are browsing from. The dashboard will use that local service to start Moonlight, VNC, SSH, or browser fallback tools directly.
        </p>
      </div>
      <div className="launcher-panel__status-row">
        <span className={`launcher-state launcher-state--${connected ? 'ready' : 'offline'}`}>
          {connected ? 'Launcher connected' : 'Launcher unavailable'}
        </span>
        <button type="button" className="ghost-button" onClick={() => void onProbe()} disabled={probing}>
          {probing ? 'Checking…' : 'Recheck'}
        </button>
      </div>
      <div className="launcher-panel__form">
        <label>
          <span>Base URL</span>
          <input value={draftBaseUrl} onChange={(event) => setDraftBaseUrl(event.target.value)} placeholder="http://127.0.0.1:32145" />
        </label>
        <label>
          <span>Token</span>
          <input value={draftToken} onChange={(event) => setDraftToken(event.target.value)} placeholder="Optional launcher token" />
        </label>
        <button type="button" className="launcher-panel__save" onClick={() => void onSave(draftBaseUrl, draftToken)}>
          Save and probe
        </button>
      </div>
      <p className="launcher-panel__meta">
        {status
          ? `Platform: ${status.viewer_platform}. Auth ${status.auth_required ? 'required' : 'not required'}. Config: ${status.config_path}`
          : error ?? 'No local launcher status available yet.'}
      </p>
      {status ? (
        <div className="launcher-panel__caps">
          {status.protocols.map((capability) => (
            <span
              key={capability.kind}
              className={`launcher-capability launcher-capability--${capability.available ? 'available' : 'missing'}`}
              title={capability.detail}
            >
              {capability.kind}
            </span>
          ))}
        </div>
      ) : null}
    </section>
  );
}
