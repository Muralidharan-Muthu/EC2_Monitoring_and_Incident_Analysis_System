/**
 * IncidentCard — compact incident summary card for lists and dashboard.
 */

import React from 'react';
import { Link } from 'react-router-dom';
import type { Incident } from '../types/incident';
import { SeverityBadge } from './SeverityBadge';

interface IncidentCardProps {
  incident: Incident;
}

function formatDuration(startedAt: string, endedAt?: string | null): string {
  const start = new Date(startedAt).getTime();
  const end = endedAt ? new Date(endedAt).getTime() : Date.now();
  const diffMs = end - start;
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  const remainingMin = minutes % 60;
  return `${hours}h ${remainingMin}m`;
}

function formatTime(ts: string): string {
  return new Date(ts).toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export const IncidentCard: React.FC<IncidentCardProps> = ({ incident }) => {
  const metrics = incident.affected_metrics || [];

  return (
    <Link to={`/incidents/${incident.id}`} className="incident-card" id={`incident-${incident.id}`}>
      <div className="incident-card-header">
        <SeverityBadge severity={incident.severity} />
        <SeverityBadge status={incident.status} />
        <span className="incident-card-id">
          {incident.id.slice(0, 8)}
        </span>
      </div>

      <div className="incident-card-title">{incident.title}</div>

      <div className="incident-card-meta">
        <span className="incident-card-host">{incident.hostname}</span>
        <span className="incident-card-time">{formatTime(incident.started_at)}</span>
        <span className="incident-card-duration">
          ⏱ {formatDuration(incident.started_at, incident.ended_at)}
        </span>
      </div>

      {metrics.length > 0 && (
        <div className="incident-card-metrics">
          {metrics.map((m) => (
            <span key={m} className="metric-tag">
              {m.replace('_usage', '').replace('_1m', ' load').replace('_ms', '').toUpperCase()}
            </span>
          ))}
        </div>
      )}

      <div className="incident-card-score">
        Correlation score: <strong>{incident.correlation_score.toFixed(1)}</strong>
        {incident.llm_analyzed && (
          <span className="ai-badge">AI analyzed</span>
        )}
      </div>
    </Link>
  );
};
