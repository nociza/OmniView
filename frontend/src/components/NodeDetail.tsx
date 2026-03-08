import { useMemo, useState } from 'react';
import {
  formatMemory,
  formatPercent,
  formatRelativeAge,
  formatTemperature,
  formatThroughput,
  platformLabel,
} from '../lib/format';
import type { LaunchResponse, NodeView, ProtocolCapability, ProtocolLaunch, ProtocolKind } from '../types';
import { StatusBadge } from './StatusBadge';

interface LauncherBridge {
  connected: boolean;
  capabilityFor: (kind: ProtocolKind) => ProtocolCapability | undefined;
  launch: (node: NodeView, protocol: ProtocolLaunch) => Promise<LaunchResponse>;
}

interface NodeDetailProps {
  node: NodeView | null;
  launcher: LauncherBridge;
}

function protocolHint(protocol: ProtocolLaunch, capability: ProtocolCapability | undefined, launcherConnected: boolean): string {
  if (launcherConnected && capability?.available) {
    return `${capability.detail} Native client: ${protocol.native_client}.`;
  }
  if (launcherConnected && capability && !capability.available) {
    return capability.detail;
  }
  if (protocol.kind === 'moonlight') {
    return 'Requires the local OmniView launcher to invoke Moonlight directly on this viewing device.';
  }
  if (protocol.kind === 'guacamole') {
    return 'Browser fallback. This can still open via URL handler even when the local launcher is offline.';
  }
  return protocol.note ?? `Falls back to the OS URI handler for ${protocol.native_client}.`;
}

export function NodeDetail({ node, launcher }: NodeDetailProps) {
  const [copied, setCopied] = useState(false);
  const [launchingKind, setLaunchingKind] = useState<ProtocolKind | null>(null);
  const [launchMessage, setLaunchMessage] = useState<string | null>(null);
  const [launchError, setLaunchError] = useState<string | null>(null);

  const metrics = node?.telemetry?.metrics;
  const note = useMemo(() => {
    if (!node) {
      return 'Select a node to inspect telemetry, screenshot state, and launch options.';
    }
    return node.headless
      ? 'This node is marked headless. Verify the virtual or service-backed display from the screenshot before launching into it.'
      : 'This node reports an attached interactive desktop. Use the local launcher for the lowest-friction handoff into native tools.';
  }, [node]);

  async function copyOverlayIp() {
    if (!node) {
      return;
    }
    try {
      await navigator.clipboard.writeText(node.overlay_ip);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      setLaunchError('Unable to copy the overlay IP from this browser context.');
    }
  }

  async function triggerLaunch(protocol: ProtocolLaunch) {
    if (!node) {
      return;
    }

    const capability = launcher.capabilityFor(protocol.kind);
    setLaunchError(null);
    setLaunchMessage(null);
    setLaunchingKind(protocol.kind);

    try {
      if (launcher.connected && capability?.available) {
        const result = await launcher.launch(node, protocol);
        setLaunchMessage(result.detail);
        return;
      }

      if (protocol.launch_uri) {
        window.location.assign(protocol.launch_uri);
        setLaunchMessage(`Local launcher unavailable for ${protocol.label}. Falling back to the OS URL handler.`);
        return;
      }

      throw new Error(capability?.detail ?? `No local launcher strategy is available for ${protocol.label}.`);
    } catch (err) {
      setLaunchError(err instanceof Error ? err.message : `Unable to launch ${protocol.label}.`);
    } finally {
      setLaunchingKind(null);
    }
  }

  if (!node) {
    return (
      <aside className="detail-panel detail-panel--empty">
        <p className="eyebrow">Detail</p>
        <h2>No node selected</h2>
        <p>{note}</p>
      </aside>
    );
  }

  return (
    <aside className="detail-panel">
      <div className="detail-panel__thumbnail" style={node.telemetry?.thumbnail_data_url ? { backgroundImage: `url(${node.telemetry.thumbnail_data_url})` } : undefined}>
        <div className="detail-panel__scrim">
          <StatusBadge status={node.status} />
          <p>{node.telemetry?.render_state ?? 'No render-state annotation provided.'}</p>
        </div>
      </div>

      <div className="detail-panel__section">
        <div className="detail-panel__header-row">
          <div>
            <p className="eyebrow">Selected node</p>
            <h2>{node.name}</h2>
            <p className="detail-panel__subline">
              {platformLabel(node.platform)} · {node.hostname} · {node.location ?? 'Overlay network'}
            </p>
          </div>
          <button type="button" className="ghost-button" onClick={() => void copyOverlayIp()}>
            {copied ? 'Copied' : 'Copy overlay IP'}
          </button>
        </div>
        <p className="detail-panel__copy">{node.description ?? node.status_message}</p>
        <p className="detail-panel__note">{note}</p>
        <p className="detail-panel__launcher-note">
          {launcher.connected
            ? 'Local launcher detected on this device. Launch actions will execute native binaries when supported.'
            : 'Local launcher not detected. Launch actions will fall back to browser/OS URI handlers when possible.'}
        </p>
      </div>

      <div className="detail-panel__section detail-panel__facts">
        <article>
          <span>Heartbeat</span>
          <strong>{formatRelativeAge(node.heartbeat_age_seconds)}</strong>
        </article>
        <article>
          <span>Session</span>
          <strong>{node.telemetry?.active_session ?? '—'}</strong>
        </article>
        <article>
          <span>Agent</span>
          <strong>{node.agent_version ?? 'unknown'}</strong>
        </article>
        <article>
          <span>Tags</span>
          <strong>{node.tags.length ? node.tags.join(', ') : '—'}</strong>
        </article>
      </div>

      <div className="detail-panel__section">
        <p className="eyebrow">Telemetry</p>
        <div className="metric-grid">
          <article>
            <span>CPU</span>
            <strong>{metrics ? formatPercent(metrics.cpu_percent) : '—'}</strong>
          </article>
          <article>
            <span>Memory</span>
            <strong>{metrics ? formatMemory(metrics) : '—'}</strong>
          </article>
          <article>
            <span>Temperature</span>
            <strong>{metrics ? formatTemperature(metrics.temperature_c) : '—'}</strong>
          </article>
          <article>
            <span>GPU</span>
            <strong>{metrics ? formatPercent(metrics.gpu_percent) : '—'}</strong>
          </article>
          <article>
            <span>RX</span>
            <strong>{metrics ? formatThroughput(metrics.network_rx_mbps) : '—'}</strong>
          </article>
          <article>
            <span>TX</span>
            <strong>{metrics ? formatThroughput(metrics.network_tx_mbps) : '—'}</strong>
          </article>
        </div>
      </div>

      <div className="detail-panel__section">
        <div className="detail-panel__header-row detail-panel__header-row--tight">
          <div>
            <p className="eyebrow">Dispatch</p>
            <h3>Native client handoff</h3>
          </div>
          <span className="detail-panel__caption">{node.status_message}</span>
        </div>
        {launchMessage ? <p className="detail-panel__feedback detail-panel__feedback--success">{launchMessage}</p> : null}
        {launchError ? <p className="detail-panel__feedback detail-panel__feedback--error">{launchError}</p> : null}
        <div className="launch-list">
          {node.protocols.map((protocol) => {
            const capability = launcher.capabilityFor(protocol.kind);
            const canLaunchLocally = launcher.connected && capability?.available;
            const canFallback = Boolean(protocol.launch_uri);
            const disabled = launchingKind === protocol.kind;
            const buttonLabel = disabled
              ? 'Launching…'
              : canLaunchLocally
                ? 'Launch locally'
                : canFallback
                  ? 'Fallback URI'
                  : 'Unavailable';

            return (
              <article key={`${node.node_id}-${protocol.kind}`} className="launch-card">
                <div>
                  <div className="launch-card__title-row">
                    <strong>{protocol.label}</strong>
                    {protocol.is_primary ? <span className="launch-card__primary">Primary</span> : null}
                  </div>
                  <p>{protocolHint(protocol, capability, launcher.connected)}</p>
                  <span>{protocol.native_client}</span>
                </div>
                <button
                  type="button"
                  className={`launch-button launch-button--${protocol.kind}`}
                  onClick={() => void triggerLaunch(protocol)}
                  disabled={disabled || (!canLaunchLocally && !canFallback)}
                >
                  {buttonLabel}
                </button>
              </article>
            );
          })}
        </div>
      </div>
    </aside>
  );
}
