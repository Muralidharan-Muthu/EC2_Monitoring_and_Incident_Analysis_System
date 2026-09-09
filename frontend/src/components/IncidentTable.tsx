/**
 * IncidentTable — full incident list with filter support.
 */

import React from 'react';
import { Link } from 'react-router-dom';
import type { Incident } from '../types/incident';
import { SeverityBadge } from './SeverityBadge';

interface IncidentTableProps {
  incidents: Incident[];
  loading?: boolean;
}

function formatTime(ts: string): string {
  return new Date(ts).toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatDuration(startedAt: string, endedAt?: string | null): string {
  const start = new Date(startedAt).getTime();
  const end = endedAt ? new Date(endedAt).getTime() : Date.now();
  const diffMs = end - start;
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}

export const IncidentTable: React.FC<IncidentTableProps> = ({ incidents, loading }) => {
  if (loading) {
    return <div className="loading-state">Loading incidents...</div>;
  }

  if (incidents.length === 0) {
    return (
      <div className="empty-state">
        <div className="empty-icon">✓</div>
        <p className="empty-title">No incidents found</p>
        <p className="empty-desc">The system is operating normally.</p>
      </div>
    );
  }

  return (
    <div className="table-container">
      <table className="data-table" id="incidents-table">
        <thead>
          <tr>
            <th>Severity</th>
            <th>Status</th>
            <th>Title</th>
            <th>Host</th>
            <th>Started</th>
            <th>Duration</th>
            <th>Observations</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {incidents.map((incident) => (
            <tr key={incident.id} className={`table-row severity-row-${incident.severity.toLowerCase()}`}>
              <td>
                <SeverityBadge severity={incident.severity} size="sm" />
              </td>
              <td>
                <SeverityBadge status={incident.status} size="sm" />
              </td>
              <td className="table-title-cell">
                <Link to={`/incidents/${incident.id}`} className="table-link">
                  {incident.title}
                </Link>
              </td>
              <td className="table-mono">{incident.hostname}</td>
              <td>{formatTime(incident.started_at)}</td>
              <td>{formatDuration(incident.started_at, incident.ended_at)}</td>
              <td className="text-center">{incident.observation_count}</td>
              <td>
                <Link
                  to={`/incidents/${incident.id}`}
                  className="btn btn-sm btn-secondary"
                  id={`view-incident-${incident.id}`}
                >
                  View
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
