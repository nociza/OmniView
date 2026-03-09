import { formatLatency, formatPercent, formatRelativeAge, formatWatts, platformLabel } from '../lib/format';
import type { ClientView } from '../types';
import { StatusBadge } from './StatusBadge';

interface ClientCardProps {
  client: ClientView;
  selected: boolean;
  onSelect: (clientId: string) => void;
}

export function ClientCard({ client, selected, onSelect }: ClientCardProps) {
  const metrics = client.telemetry?.metrics;

  return (
    <button type="button" className={`node-card client-card ${selected ? 'node-card--selected' : ''}`} onClick={() => onSelect(client.client_id)}>
      <div className="client-card__header">
        <div>
          <StatusBadge status={client.status} />
          <h3>{client.name}</h3>
          <p>{platformLabel(client.platform)} · {client.overlay_ip}</p>
        </div>
        <span className="node-card__age">{formatRelativeAge(client.heartbeat_age_seconds)}</span>
      </div>
      <p className="node-card__description">{client.status_message}</p>
      <dl className="node-card__metrics">
        <div>
          <dt>CPU</dt>
          <dd>{metrics ? formatPercent(metrics.cpu_percent) : '—'}</dd>
        </div>
        <div>
          <dt>Latency</dt>
          <dd>{metrics ? formatLatency(metrics.network_latency_ms) : '—'}</dd>
        </div>
        <div>
          <dt>Power</dt>
          <dd>{metrics ? formatWatts(metrics.power_watts ?? metrics.gpu_power_watts) : '—'}</dd>
        </div>
      </dl>
      <div className="client-card__caps">
        {client.capabilities.slice(0, 4).map((capability) => (
          <span
            key={`${client.client_id}-${capability.kind}`}
            className={`launcher-capability launcher-capability--${capability.available ? 'available' : 'missing'}`}
          >
            {capability.kind}
          </span>
        ))}
      </div>
    </button>
  );
}
