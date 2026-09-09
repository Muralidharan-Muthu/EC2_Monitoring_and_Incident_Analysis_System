/**
 * Dashboard Page — System overview with live metrics and recent incidents.
 */

import React from 'react';
import { Link } from 'react-router-dom';
import { useDashboardSummary, useTimeseries } from '../hooks/useMetrics';
import { useIncidents } from '../hooks/useIncidents';
import { MetricCard } from '../components/MetricCard';
import { MetricChart } from '../components/MetricChart';
import { IncidentCard } from '../components/IncidentCard';

const STATUS_CLASSES: Record<string, string> = {
  HEALTHY: 'status-healthy',
  DEGRADED: 'status-degraded',
  CRITICAL: 'status-critical',
};

const STATUS_ICONS: Record<string, string> = {
  HEALTHY: '✓',
  DEGRADED: '⚠',
  CRITICAL: '✕',
};

export const Dashboard: React.FC = () => {
  const { summary, loading: summaryLoading, error: summaryError } = useDashboardSummary();
  const { data: timeseries, loading: tsLoading } = useTimeseries(60);
  const { data: incidents, loading: incidentsLoading } = useIncidents({
    status: undefined,
    page: 1,
    page_size: 5,
  });

  const systemStatus = summary?.system_status || 'HEALTHY';
  const statusClass = STATUS_CLASSES[systemStatus] || 'status-healthy';

  return (
    <main className="page" id="dashboard-page">
      <div className="page-header">
        <h1 className="page-title">System Dashboard</h1>
        {summary?.last_metric_at && (
          <p className="page-subtitle">
            Last updated: {new Date(summary.last_metric_at).toLocaleTimeString()}
            {summary.hostname && ` · ${summary.hostname}`}
          </p>
        )}
      </div>

      {/* System Status Banner */}
      <section className={`status-banner ${statusClass}`} aria-label="System Status">
        <div className="status-banner-content">
          <span className="status-icon">{STATUS_ICONS[systemStatus]}</span>
          <div>
            <div className="status-label">SYSTEM STATUS</div>
            <div className="status-value">{systemStatus}</div>
          </div>
          {summary && (
            <div className="status-incidents">
              <span className="status-incident-count">
                {summary.active_incident_count}
              </span>
              <span className="status-incident-label">Active Incident{summary.active_incident_count !== 1 ? 's' : ''}</span>
            </div>
          )}
        </div>
      </section>

      {summaryError && (
        <div className="alert alert-error" role="alert">
          Failed to load metrics: {summaryError}
        </div>
      )}

      {/* Metric Cards */}
      <section className="section" aria-label="Current Metrics">
        <h2 className="section-title">Current Metrics</h2>
        {summaryLoading ? (
          <div className="loading-state">Loading...</div>
        ) : (
          <div className="metrics-grid" id="metrics-grid">
            <MetricCard
              label="CPU Usage"
              value={summary?.latest_cpu}
              unit="%"
              warningThreshold={70}
              criticalThreshold={90}
            />
            <MetricCard
              label="Memory Usage"
              value={summary?.latest_memory}
              unit="%"
              warningThreshold={75}
              criticalThreshold={90}
            />
            <MetricCard
              label="Disk Usage"
              value={summary?.latest_disk}
              unit="%"
              warningThreshold={80}
              criticalThreshold={90}
            />
            <MetricCard
              label="Load (1m)"
              value={summary?.latest_load_1m}
              unit=""
              precision={2}
              description="System load average"
            />
          </div>
        )}
      </section>

      {/* Time-series Charts */}
      <section className="section" aria-label="Metric Trends">
        <h2 className="section-title">Last 60 Minutes</h2>
        {tsLoading ? (
          <div className="loading-state">Loading charts...</div>
        ) : timeseries ? (
          <div className="charts-grid" id="charts-grid">
            <MetricChart
              data={timeseries.data}
              dataKey="cpu_usage"
              label="CPU Usage"
              color="#3b82f6"
              warningThreshold={70}
              criticalThreshold={90}
            />
            <MetricChart
              data={timeseries.data}
              dataKey="memory_usage"
              label="Memory Usage"
              color="#8b5cf6"
              warningThreshold={75}
              criticalThreshold={90}
            />
            <MetricChart
              data={timeseries.data}
              dataKey="disk_usage"
              label="Disk Usage"
              color="#f59e0b"
              warningThreshold={80}
              criticalThreshold={90}
            />
            <MetricChart
              data={timeseries.data}
              dataKey="load_1m"
              label="System Load (1m)"
              color="#10b981"
              unit=""
              yDomain={[0, 'auto']}
            />
          </div>
        ) : null}
      </section>

      {/* Recent Incidents */}
      <section className="section" aria-label="Recent Incidents">
        <div className="section-header-row">
          <h2 className="section-title">Recent Incidents</h2>
          <Link to="/incidents" className="btn btn-secondary btn-sm" id="view-all-incidents">
            View All
          </Link>
        </div>
        {incidentsLoading ? (
          <div className="loading-state">Loading incidents...</div>
        ) : incidents && incidents.incidents.length > 0 ? (
          <div className="incidents-list" id="recent-incidents-list">
            {incidents.incidents.map((incident) => (
              <IncidentCard key={incident.id} incident={incident} />
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <div className="empty-icon">✓</div>
            <p className="empty-title">No active incidents</p>
            <p className="empty-desc">All systems are operating normally.</p>
          </div>
        )}
      </section>
    </main>
  );
};
