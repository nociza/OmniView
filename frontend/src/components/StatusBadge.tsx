import { statusLabel } from '../lib/format';
import type { NodeStatus } from '../types';

interface StatusBadgeProps {
  status: NodeStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  return <span className={`status-badge status-badge--${status}`}>{statusLabel(status)}</span>;
}
