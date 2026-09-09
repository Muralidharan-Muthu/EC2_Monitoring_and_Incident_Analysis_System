/**
 * Incident Detail Page — Full incident view with analysis, evidence, and processes.
 * Uses Lucide icons instead of emojis.
 */

import React from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  ArrowLeft,
  ChevronRight,
  Bot,
  Info,
  Clock,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  FileText,
} from 'lucide-react';
import { useIncidentDetail } from '../hooks/useIncidents';
import { SeverityBadge } from '../components/SeverityBadge';
import { IncidentTimeline } from '../components/IncidentTimeline';

function formatDuration(startedAt: string, endedAt?: string | null): string {
  const start = new Date(startedAt).getTime();
  const end = endedAt ? new Date(endedAt).getTime() : Date.now();
  const diffMs = end - start;
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}

function formatDateTime(ts: string): string {
  return new Date(ts).toLocaleString([], {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

const METRIC_LABELS: Record<string, string> = {
  cpu_usage: 'CPU',
  memory_usage: 'Memory',
  disk_usage: 'Disk',
  load_1m: 'System Load',
  response_time_ms: 'Response Time',
};

export const IncidentDetail: React.FC = () => {
  const { incidentId } = useParams<{ incidentId: string }>();
  const { incident, loading, error, analyzing, triggerAnalysis } = useIncidentDetail(
    incidentId || null
  );

  if (loading) {
    return (
      <main className="page" id="incident-detail-page">
        <div className="loading-state">Loading incident from database...</div>
      </main>
    );
  }

  if (error || !incident) {
    return (
      <main className="page" id="incident-detail-page">
        <div className="alert alert-error">{error || 'Incident not found'}</div>
        <Link to="/incidents" className="btn btn-secondary" id="back-to-incidents" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
          <ArrowLeft size={15} />
          <span>Back to Incidents</span>
        </Link>
      </main>
    );
  }

  const analysis = incident.analysis;
  const affectedMetrics = incident.affected_metrics || [];

  return (
    <main className="page" id="incident-detail-page">
      {/* Header */}
      <div className="page-header">
        <div className="breadcrumb" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Link to="/incidents" id="breadcrumb-incidents">Incidents</Link>
          <ChevronRight size={14} className="breadcrumb-sep" />
          <span>{incident.id.slice(0, 8)}</span>
        </div>
        <h1 className="page-title">{incident.title}</h1>
        <div className="incident-detail-meta" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <SeverityBadge severity={incident.severity} />
          <SeverityBadge status={incident.status} />
          <span className="meta-item">Host: {incident.hostname}</span>
          <span className="meta-item" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
            <Clock size={13} />
            <span>Duration: {formatDuration(incident.started_at, incident.ended_at)}</span>
          </span>
        </div>
      </div>

      <div className="detail-grid">
        {/* Left column */}
        <div className="detail-main">

          {/* Timeline */}
          <section className="detail-section" aria-label="Timeline">
            <h2 className="section-title">Timeline</h2>
            <IncidentTimeline
              startedAt={incident.started_at}
              lastSeenAt={incident.last_seen_at || incident.started_at}
              endedAt={incident.ended_at}
              status={incident.status}
              anomalies={incident.anomalies}
              analyzedAt={analysis?.generated_at}
            />
          </section>

          {/* Affected Metrics */}
          <section className="detail-section" aria-label="Affected Metrics">
            <h2 className="section-title">Affected Metrics</h2>
            <div className="metric-tags-large" id="affected-metrics">
              {affectedMetrics.map((m) => (
                <span key={m} className="metric-tag-large">
                  {METRIC_LABELS[m] || m}
                </span>
              ))}
            </div>
          </section>

          {/* Observed Anomalies */}
          <section className="detail-section" aria-label="Detected Anomalies">
            <h2 className="section-title">Detected Anomalies</h2>
            <div className="observation-note">
              <strong>Observed facts</strong> — verified by deterministic rule evaluation
            </div>
            <div className="anomaly-list" id="anomaly-list">
              {incident.anomalies.map((a) => (
                <div key={a.id} className={`anomaly-item anomaly-${a.severity.toLowerCase()}`}>
                  <div className="anomaly-item-header">
                    <SeverityBadge severity={a.severity} size="sm" />
                    <span className="anomaly-metric">
                      {METRIC_LABELS[a.metric_name] || a.metric_name}
                    </span>
                    {a.is_persistent && (
                      <span className="persistent-badge">Persistent</span>
                    )}
                  </div>
                  <div className="anomaly-description">{a.description}</div>
                  <div className="anomaly-values">
                    Observed: <strong>{a.observed_value.toFixed(1)}</strong>
                    {' '}· Threshold: <strong>{a.threshold.toFixed(1)}</strong>
                    {' '}· Detected: {new Date(a.detected_at).toLocaleTimeString()}
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* Analysis Section */}
          <section className="detail-section" aria-label="Analysis">
            <div className="section-header-row">
              <h2 className="section-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {(analysis?.analysis_source === 'llm' || analysis?.analysis_source === 'groq') ? (
                  <>
                    <Bot size={20} color="var(--color-brand)" />
                    <span>LangGraph + Groq AI Analysis</span>
                  </>
                ) : (
                  <>
                    <FileText size={18} />
                    <span>Deterministic Rule Analysis</span>
                  </>
                )}
              </h2>
              <button
                id="trigger-analysis-btn"
                className={`btn btn-primary btn-sm ${analyzing ? 'loading' : ''}`}
                onClick={triggerAnalysis}
                disabled={analyzing}
                style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
              >
                <Sparkles size={14} />
                <span>{analyzing ? 'Analyzing with LangGraph...' : incident.llm_analyzed ? 'Re-run AI Analysis' : 'Run LangGraph AI Analysis'}</span>
              </button>
            </div>

            {(analysis?.analysis_source === 'llm' || analysis?.analysis_source === 'groq') && (
              <div className="ai-badge-full">
                LangGraph + Groq · Model: {analysis.model_name || 'qwen/qwen3.8-27b'}
                {analysis.confidence != null && (
                  <span className="confidence">
                    · Confidence: {(analysis.confidence * 100).toFixed(0)}%
                  </span>
                )}
              </div>
            )}

            {/* Probable Cause */}
            {incident.probable_cause && (
              <div className="analysis-block" id="probable-cause">
                <h3 className="analysis-label">Probable Cause</h3>
                <p className="analysis-text analysis-inferred">{incident.probable_cause}</p>
                <div className="inference-note" style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                  <Info size={13} />
                  <span>Probabilistic assessment derived by AI workflow based on telemetry evidence.</span>
                </div>
              </div>
            )}

            {/* Evidence */}
            {analysis?.evidence && analysis.evidence.length > 0 && (
              <div className="analysis-block" id="evidence-list">
                <h3 className="analysis-label">Evidence</h3>
                <ul className="evidence-list">
                  {analysis.evidence.map((e, i) => (
                    <li key={i} className="evidence-item">{e}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Reasoning Summary */}
            {analysis?.reasoning_summary && (
              <div className="analysis-block" id="reasoning-summary">
                <h3 className="analysis-label">Reasoning</h3>
                <p className="analysis-text">{analysis.reasoning_summary}</p>
              </div>
            )}

            {/* Recommended Actions */}
            {(analysis?.recommended_actions || incident.recommended_action) && (
              <div className="analysis-block" id="recommended-actions">
                <h3 className="analysis-label">Recommended Actions</h3>
                {analysis?.recommended_actions && analysis.recommended_actions.length > 0 ? (
                  <ol className="action-list">
                    {analysis.recommended_actions.map((action, i) => (
                      <li key={i} className="action-item">{action}</li>
                    ))}
                  </ol>
                ) : (
                  <p className="analysis-text">{incident.recommended_action}</p>
                )}
              </div>
            )}
          </section>
        </div>

        {/* Right column — Summary */}
        <aside className="detail-sidebar">
          <div className="sidebar-card">
            <h3 className="sidebar-title">Summary</h3>
            <p className="sidebar-text">{incident.summary}</p>
          </div>

          {incident.llm_analyzed && (
            <div className="sidebar-card sidebar-ai">
              <h3 className="sidebar-title">AI Confidence</h3>
              <div className="confidence-display">
                {((incident.llm_confidence || 0) * 100).toFixed(0)}%
              </div>
            </div>
          )}

          <div className="sidebar-card">
            <h3 className="sidebar-title">Incident Details</h3>
            <dl className="detail-list">
              <dt>ID</dt>
              <dd className="mono">{incident.id.slice(0, 16)}...</dd>
              <dt>Key</dt>
              <dd className="mono">{incident.incident_key.slice(0, 16)}...</dd>
              <dt>Created</dt>
              <dd>{new Date(incident.created_at).toLocaleDateString()}</dd>
            </dl>
          </div>
        </aside>
      </div>
    </main>
  );
};
