/**
 * TypeScript type definitions for incident data.
 */

export type IncidentStatus = 'OPEN' | 'INVESTIGATING' | 'RESOLVED';
export type IncidentSeverity = 'WARNING' | 'CRITICAL';

export interface AnomalySummary {
  id: string;
  metric_name: string;
  observed_value: number;
  threshold: number;
  severity: IncidentSeverity;
  description: string;
  is_persistent: boolean;
  detected_at: string;
}

export interface IncidentAnalysis {
  affected_metrics: string[];
  probable_causes: string[];
  evidence: string[];
  recommended_actions: string[];
  reasoning_summary: string;
  analysis_source: 'llm' | 'rule_based';
  model_name: string | null;
  confidence: number | null;
  generated_at: string | null;
}

export interface Incident {
  id: string;
  incident_key: string;
  title: string;
  status: IncidentStatus;
  severity: IncidentSeverity;
  hostname: string;
  started_at: string;
  ended_at: string | null;
  created_at: string;
  updated_at: string;
  probable_cause: string | null;
  recommended_action: string | null;
  summary: string | null;
  correlation_score: number;
  affected_metrics: string[] | null;
  llm_confidence: number | null;
  llm_analyzed: boolean;
  observation_count: number;
  anomalies: AnomalySummary[];
  analysis: IncidentAnalysis | null;
}

export interface IncidentListResponse {
  incidents: Incident[];
  total: number;
  page: number;
  page_size: number;
}
