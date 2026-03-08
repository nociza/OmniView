import { formatMemory, formatPercent, formatRelativeAge, formatTemperature, platformLabel } from '../lib/format';
import type { NodeView } from '../types';
import { StatusBadge } from './StatusBadge';

interface NodeCardProps {
  node: NodeView;
  selected: boolean;
  onSelect: (nodeId: string) => void;
}

export function NodeCard({ node, selected, onSelect }: NodeCardProps) {
  const metrics = node.telemetry?.metrics;

  return (
    <button type="button" className={`node-card ${selected ? 'node-card--selected' : ''}`} onClick={() => onSelect(node.node_id)}>
      <div
        className="node-card__thumbnail"
        style={node.telemetry?.thumbnail_data_url ? { backgroundImage: `url(${node.telemetry.thumbnail_data_url})` } : undefined}
      >
        <div className="node-card__overlay">
          <StatusBadge status={node.status} />
          <span className="node-card__platform">{platformLabel(node.platform)}</span>
        </div>
      </div>
      <div className="node-card__body">
        <div className="node-card__header">
          <div>
            <h3>{node.name}</h3>
            <p>{node.overlay_ip}</p>
          </div>
          <span className="node-card__age">{formatRelativeAge(node.heartbeat_age_seconds)}</span>
        </div>
        <p className="node-card__description">{node.description ?? node.status_message}</p>
        <dl className="node-card__metrics">
          <div>
            <dt>CPU</dt>
            <dd>{metrics ? formatPercent(metrics.cpu_percent) : '—'}</dd>
          </div>
          <div>
            <dt>Memory</dt>
            <dd>{metrics ? formatMemory(metrics) : '—'}</dd>
          </div>
          <div>
            <dt>Temp</dt>
            <dd>{metrics ? formatTemperature(metrics.temperature_c) : '—'}</dd>
          </div>
        </dl>
        <div className="node-card__footer">
          <div className="tag-row">
            {node.tags.slice(0, 3).map((tag) => (
              <span key={tag} className="tag-chip">
                {tag}
              </span>
            ))}
          </div>
          <span className="node-card__protocol">{node.protocols[0]?.label ?? 'No launch target'}</span>
        </div>
      </div>
    </button>
  );
}
