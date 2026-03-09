export type NodeStatus = 'online' | 'stale' | 'offline';
export type NodePlatform = 'linux' | 'macos' | 'windows';
export type ProtocolKind = 'moonlight' | 'vnc' | 'ssh' | 'guacamole';

export interface TelemetryMetrics {
  cpu_percent: number;
  memory_percent: number;
  memory_used_gb?: number | null;
  memory_total_gb?: number | null;
  temperature_c?: number | null;
  gpu_percent?: number | null;
  gpu_power_watts?: number | null;
  network_rx_mbps?: number | null;
  network_tx_mbps?: number | null;
  load_average_1?: number | null;
  load_average_5?: number | null;
  load_average_15?: number | null;
  network_latency_ms?: number | null;
  power_watts?: number | null;
  uptime_seconds?: number | null;
}

export interface TelemetryPayload {
  reported_at: string;
  metrics: TelemetryMetrics;
  thumbnail_data_url?: string | null;
  render_state?: string | null;
  active_session?: string | null;
  collector_notes: string[];
  recent_logs: string[];
  recent_errors: string[];
}

export interface ProtocolLaunch {
  kind: ProtocolKind;
  label: string;
  priority: number;
  host: string;
  port?: number | null;
  username?: string | null;
  path?: string | null;
  app_name?: string | null;
  launch_uri?: string | null;
  native_client: string;
  requires_native_client: boolean;
  note?: string | null;
  is_primary: boolean;
}

export interface NodeView {
  node_id: string;
  name: string;
  hostname: string;
  overlay_ip: string;
  platform: NodePlatform;
  description?: string | null;
  location?: string | null;
  tags: string[];
  headless: boolean;
  agent_version?: string | null;
  status: NodeStatus;
  status_message: string;
  last_seen_at: string;
  heartbeat_age_seconds: number;
  preferred_protocol?: ProtocolKind | null;
  protocols: ProtocolLaunch[];
  telemetry?: TelemetryPayload | null;
}

export interface DashboardCounts {
  total: number;
  online: number;
  stale: number;
  offline: number;
}

export interface DashboardSummary {
  counts: DashboardCounts;
  average_cpu_percent?: number | null;
  hottest_node_name?: string | null;
  last_updated_at: string;
}

export interface DashboardResponse {
  summary: DashboardSummary;
  nodes: NodeView[];
  clients: ClientView[];
  poll_interval_seconds: number;
}

export interface ProtocolCapability {
  kind: ProtocolKind;
  available: boolean;
  strategy?: string | null;
  detail: string;
}

export interface LauncherStatusResponse {
  service: string;
  viewer_platform: string;
  auth_required: boolean;
  config_path: string;
  protocols: ProtocolCapability[];
}

export interface ClientProfileCapability extends ProtocolCapability {}

export interface ClientView {
  client_id: string;
  name: string;
  hostname: string;
  overlay_ip: string;
  platform: NodePlatform;
  hub_url: string;
  launcher_url: string;
  app_version?: string | null;
  status: NodeStatus;
  status_message: string;
  last_seen_at: string;
  heartbeat_age_seconds: number;
  capabilities: ClientProfileCapability[];
  telemetry?: TelemetryPayload | null;
}

export interface LaunchRequestPayload {
  node_id?: string | null;
  node_name: string;
  overlay_ip: string;
  platform?: NodePlatform | null;
  protocol: ProtocolKind;
  label?: string | null;
  host?: string | null;
  port?: number | null;
  username?: string | null;
  path?: string | null;
  app_name?: string | null;
  launch_uri?: string | null;
  dry_run?: boolean;
}

export interface LaunchResponse {
  ok: boolean;
  launched: boolean;
  protocol: ProtocolKind;
  strategy: string;
  detail: string;
  command: string[];
}
