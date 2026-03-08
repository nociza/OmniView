import type { NodePlatform, NodeStatus, TelemetryMetrics } from '../types';

export function formatRelativeAge(seconds: number): string {
  if (seconds < 60) {
    return `${seconds}s ago`;
  }
  if (seconds < 3600) {
    return `${Math.round(seconds / 60)}m ago`;
  }
  return `${Math.round(seconds / 3600)}h ago`;
}

export function formatPercent(value?: number | null): string {
  return value == null ? '—' : `${Math.round(value)}%`;
}

export function formatTemperature(value?: number | null): string {
  return value == null ? '—' : `${value.toFixed(1)}°C`;
}

export function formatMemory(metrics: TelemetryMetrics): string {
  if (metrics.memory_used_gb != null && metrics.memory_total_gb != null) {
    return `${metrics.memory_used_gb.toFixed(1)} / ${metrics.memory_total_gb.toFixed(0)} GB`;
  }
  return formatPercent(metrics.memory_percent);
}

export function formatThroughput(value?: number | null): string {
  return value == null ? '—' : `${value.toFixed(1)} Mb/s`;
}

export function platformLabel(platform: NodePlatform): string {
  return {
    linux: 'Linux',
    macos: 'macOS',
    windows: 'Windows',
  }[platform];
}

export function statusLabel(status: NodeStatus): string {
  return {
    online: 'Online',
    stale: 'Stale',
    offline: 'Offline',
  }[status];
}
