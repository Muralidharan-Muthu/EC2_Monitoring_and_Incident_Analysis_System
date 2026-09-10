/**
 * TypeScript type definitions for metric-related data.
 * Strictly supports nullable metrics.
 */

export interface Metric {
  id: string;
  hostname: string;
  timestamp: string;
  cpu_usage: number | null;
  cpu_count: number | null;
  memory_usage: number | null;
  memory_total_mb: number | null;
  memory_used_mb: number | null;
  memory_available_mb: number | null;
  disk_usage: number | null;
  disk_total_gb: number | null;
  disk_used_gb: number | null;
  disk_free_gb: number | null;
  load_1m: number | null;
  load_5m: number | null;
  load_15m: number | null;
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
  system_status: 'HEALTHY' | 'DEGRADED' | 'CRITICAL' | 'CONNECTED' | 'UNAVAILABLE' | string;
  active_incident_count: number;
  highest_severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'WARNING' | 'CRITICAL' | string | null;
  latest_cpu: number | null;
  latest_memory: number | null;
  latest_disk: number | null;
  latest_load_1m: number | null;
  latest_response_time_ms?: number | null;
  hostname: string | null;
  last_metric_at: string | null;
  ssh_status?: 'CONNECTED' | 'DEGRADED' | 'UNAVAILABLE' | string;
  ec2_host_configured?: boolean;  // true = host is known; false = no instance discovered yet
  aws_region?: string;             // e.g. "ap-south-1" — used to build AWS Console deep-link
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
