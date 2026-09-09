/**
 * TypeScript type definitions for anomaly data.
 */

export interface Anomaly {
  id: string;
  metric_id: string;
  metric_name: string;
  observed_value: number;
  threshold: number;
  anomaly_type: string;
  severity: 'WARNING' | 'CRITICAL';
  description: string;
  is_persistent: boolean;
  consecutive_count: number;
  detected_at: string;
  created_at: string;
}

export interface AnomalyListResponse {
  anomalies: Anomaly[];
  total: number;
  page: number;
  page_size: number;
}
