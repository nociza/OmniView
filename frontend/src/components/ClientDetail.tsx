import {
  formatLatency,
  formatLoad,
  formatMemory,
  formatPercent,
  formatRelativeAge,
  formatTemperature,
  formatThroughput,
  formatUptime,
  formatWatts,
  platformLabel,
} from '../lib/format';
import type { ClientView } from '../types';
import { StatusBadge } from './StatusBadge';

interface ClientDetailProps {
  client: ClientView | null;
}

export function ClientDetail({ client }: ClientDetailProps) {
  const metrics = client?.telemetry?.metrics;

  if (!client) {
    return (
      <aside className="detail-panel detail-panel--empty">
        <p className="eyebrow">Viewer detail</p>
        <h2>No client selected</h2>
        <p>Select a native client to inspect launcher capability, machine health, and recent errors.</p>
      </aside>
    );
  }

  return (
    <aside className="detail-panel">
      <div className="detail-panel__section">
        <div className="detail-panel__header-row">
          <div>
            <p className="eyebrow">Native client</p>
            <h2>{client.name}</h2>
            <p className="detail-panel__subline">
              {platformLabel(client.platform)} · {client.hostname} · {client.overlay_ip}
            </p>
          </div>
          <StatusBadge status={client.status} />
        </div>
        <p className="detail-panel__copy">{client.status_message}</p>
        <p className="detail-panel__note">Launcher URL: {client.launcher_url} · Hub: {client.hub_url}</p>
      </div>

      <div className="detail-panel__section detail-panel__facts">
        <article>
          <span>Heartbeat</span>
          <strong>{formatRelativeAge(client.heartbeat_age_seconds)}</strong>
        </article>
        <article>
          <span>Session</span>
          <strong>{client.telemetry?.active_session ?? '—'}</strong>
        </article>
        <article>
          <span>Version</span>
          <strong>{client.app_version ?? 'unknown'}</strong>
        </article>
        <article>
          <span>Uptime</span>
          <strong>{metrics ? formatUptime(metrics.uptime_seconds) : '—'}</strong>
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
            <span>Load</span>
            <strong>{metrics ? formatLoad(metrics) : '—'}</strong>
          </article>
          <article>
            <span>Latency</span>
            <strong>{metrics ? formatLatency(metrics.network_latency_ms) : '—'}</strong>
          </article>
          <article>
            <span>Power</span>
            <strong>{metrics ? formatWatts(metrics.power_watts) : '—'}</strong>
          </article>
          <article>
            <span>GPU Power</span>
            <strong>{metrics ? formatWatts(metrics.gpu_power_watts) : '—'}</strong>
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
            <p className="eyebrow">Capabilities</p>
            <h3>Launcher support</h3>
          </div>
          <span className="detail-panel__caption">{client.capabilities.filter((item) => item.available).length} protocols available</span>
        </div>
        <div className="launch-list">
          {client.capabilities.map((capability) => (
            <article key={`${client.client_id}-${capability.kind}`} className="launch-card">
              <div>
                <div className="launch-card__title-row">
                  <strong>{capability.kind}</strong>
                </div>
                <p>{capability.detail}</p>
                <span>{capability.strategy ?? 'unavailable'}</span>
              </div>
            </article>
          ))}
        </div>
      </div>

      <div className="detail-panel__section detail-panel__logs">
        <div className="detail-panel__header-row detail-panel__header-row--tight">
          <div>
            <p className="eyebrow">Diagnostics</p>
            <h3>Recent logs and errors</h3>
          </div>
          <span className="detail-panel__caption">{client.telemetry?.collector_notes.length ?? 0} collector notes</span>
        </div>
        {client.telemetry?.recent_errors.length ? (
          <div className="diagnostic-list diagnostic-list--error">
            {client.telemetry.recent_errors.map((line) => (
              <p key={line}>{line}</p>
            ))}
          </div>
        ) : (
          <p className="detail-panel__copy">No recent launcher errors recorded.</p>
        )}
        {client.telemetry?.recent_logs.length ? (
          <div className="diagnostic-list">
            {client.telemetry.recent_logs.map((line) => (
              <p key={line}>{line}</p>
            ))}
          </div>
        ) : null}
        {client.telemetry?.collector_notes.length ? (
          <div className="diagnostic-list diagnostic-list--note">
            {client.telemetry.collector_notes.map((line) => (
              <p key={line}>{line}</p>
            ))}
          </div>
        ) : null}
      </div>
    </aside>
  );
}
