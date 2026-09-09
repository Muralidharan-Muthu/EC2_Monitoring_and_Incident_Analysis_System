/**
 * TypeScript type definitions for metric-related data.
 */

export interface Metric {
  id: string;
  hostname: string;
  timestamp: string;
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  load_1m: number;
  load_5m: number;
  load_15m: number;
  cpu_count: number;
  memory_available_mb: number | null;
  disk_free_gb: number | null;
  network_rx_bytes: number | null;
  network_tx_bytes: number | null;
  response_time_ms: number | null;
  http_status: number | null;
  os_name: string | null;
  kernel_version: string | null;
  created_at: string;
}

export interface TimeSeriesPoint {
  timestamp: string;
  cpu_usage: number | null;
  memory_usage: number | null;
  disk_usage: number | null;
  load_1m: number | null;
  response_time_ms: number | null;
}

export interface TimeSeriesResponse {
  data: TimeSeriesPoint[];
  hostname: string | null;
  range_minutes: number;
}

export interface DashboardSummary {
  system_status: 'HEALTHY' | 'DEGRADED' | 'CRITICAL';
  active_incident_count: number;
  highest_severity: 'WARNING' | 'CRITICAL' | null;
  latest_cpu: number | null;
  latest_memory: number | null;
  latest_disk: number | null;
  latest_load_1m: number | null;
  hostname: string | null;
  last_metric_at: string | null;
}

export interface SystemStatus {
  service: string;
  version: string;
  database: string;
  total_metrics: number;
  active_incidents: number;
  latest_metric_age_seconds: number | null;
  monitoring_agent_active: boolean;
  timestamp: string;
}
