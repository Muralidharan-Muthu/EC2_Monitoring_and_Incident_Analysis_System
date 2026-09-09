/**
 * Incidents Page — List of all incidents with filtering.
 */

import React, { useState } from 'react';
import { useIncidents } from '../hooks/useIncidents';
import { IncidentTable } from '../components/IncidentTable';

export const Incidents: React.FC = () => {
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [severityFilter, setSeverityFilter] = useState<string>('');

  const { data, loading, error } = useIncidents({
    status: statusFilter || undefined,
    severity: severityFilter || undefined,
    page: 1,
    page_size: 50,
  });

  return (
    <main className="page" id="incidents-page">
      <div className="page-header">
        <h1 className="page-title">Incidents</h1>
        <p className="page-subtitle">
          {data ? `${data.total} incident${data.total !== 1 ? 's' : ''} found` : ''}
        </p>
      </div>

      {/* Filters */}
      <div className="filter-bar" role="search" aria-label="Incident filters">
        <div className="filter-group">
          <label htmlFor="status-filter" className="filter-label">Status</label>
          <select
            id="status-filter"
            className="filter-select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">All</option>
            <option value="OPEN">Open</option>
            <option value="INVESTIGATING">Investigating</option>
            <option value="RESOLVED">Resolved</option>
          </select>
        </div>
        <div className="filter-group">
          <label htmlFor="severity-filter" className="filter-label">Severity</label>
          <select
            id="severity-filter"
            className="filter-select"
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
          >
            <option value="">All</option>
            <option value="CRITICAL">Critical</option>
            <option value="WARNING">Warning</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      )}

      <IncidentTable
        incidents={data?.incidents || []}
        loading={loading}
      />
    </main>
  );
};
