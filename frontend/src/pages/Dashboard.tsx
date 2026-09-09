/**
 * Dashboard Page — Professional EC2 Monitoring and Incident Analysis.
 * Adheres strictly to zero fake metrics rule (null displays as '-').
 */

import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useDashboardSummary, useTimeseries } from '../hooks/useMetrics';
import { useIncidents } from '../hooks/useIncidents';
import { MetricCard } from '../components/MetricCard';
import { MetricChart } from '../components/MetricChart';
import { IncidentCard } from '../components/IncidentCard';
import { StatusBadge } from '../components/StatusBadge';
import monitoringApi from '../services/monitoringApi';

export const Dashboard: React.FC = () => {
  const { summary, loading: summaryLoading, error: summaryError, refresh: refreshSummary } = useDashboardSummary();
  const { data: timeseries, loading: tsLoading, refresh: refreshTimeseries } = useTimeseries(60);
  const { data: incidents, loading: incidentsLoading, refresh: refreshIncidents } = useIncidents({
    status: undefined,
    page: 1,
    page_size: 5,
  });

  const [collecting, setCollecting] = useState(false);
  const [collectMessage, setCollectMessage] = useState<string | null>(null);

  // Auto-refresh every 10 seconds per Section 42
  useEffect(() => {
    const timer = setInterval(() => {
      refreshSummary();
      refreshTimeseries();
      refreshIncidents();
    }, 10000);
    return () => clearInterval(timer);
  }, [refreshSummary, refreshTimeseries, refreshIncidents]);

  const handleCollectNow = async () => {
    setCollecting(true);
    setCollectMessage(null);
    try {
      const res = await monitoringApi.collectNow();
      if (res.success) {
        setCollectMessage('Live telemetry collected successfully via SSH.');
        refreshSummary();
        refreshTimeseries();
        refreshIncidents();
      } else {
        setCollectMessage(res.error?.message || 'Collection encountered an error.');
      }
    } catch (err: any) {
      setCollectMessage(err?.message || 'Failed to trigger collection.');
    } finally {
      setCollecting(false);
      setTimeout(() => setCollectMessage(null), 4000);
    }
  };

  const sshStatus = summary?.ssh_status || 'CONNECTED';
  const systemStatus = summary?.system_status || 'HEALTHY';

  return (
    <main className="page" id="dashboard-page">
      {/* Top Header with SSH Status & Manual Action */}
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 className="page-title">EC2 Monitoring & Incident Analysis</h1>
          <p className="page-subtitle">
            Remote agentless telemetry via SSH
            {summary?.hostname && ` · Host: ${summary.hostname}`}
            {summary?.last_metric_at && (
              <> · Last updated: {new Date(summary.last_metric_at).toLocaleTimeString()}</>
            )}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <button
            id="collect-now-btn"
            className="btn btn-primary"
            onClick={handleCollectNow}
            disabled={collecting}
          >
            {collecting ? 'Collecting via SSH...' : 'Collect Now'}
          </button>
        </div>
      </div>

      {collectMessage && (
        <div className="alert alert-info" role="status" style={{ marginBottom: '16px' }}>
          {collectMessage}
        </div>
      )}

      {/* EC2 Health Banner */}
      <section className="status-banner" style={{ marginBottom: '24px' }}>
        <div className="status-banner-content" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
          <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
            <div>
              <div className="status-label">EC2 CONNECTION</div>
              <StatusBadge status={sshStatus} size="lg" />
            </div>
            <div style={{ borderLeft: '1px solid #e5e7eb', paddingLeft: '16px' }}>
              <div className="status-label">OVERALL HEALTH</div>
              <StatusBadge status={systemStatus} size="lg" />
            </div>
          </div>

          <div className="status-incidents">
            <span className="status-incident-count">{summary?.active_incident_count ?? 0}</span>
            <span className="status-incident-label">
              Active Incident{summary?.active_incident_count !== 1 ? 's' : ''}
            </span>
          </div>
        </div>
      </section>

      {summaryError && (
        <div className="alert alert-error" role="alert">
          Failed to load metrics: {summaryError}
        </div>
      )}

      {/* Metric Cards — CPU, Memory, Disk, Load, Response Time */}
      <section className="section" aria-label="Current Metrics">
        <h2 className="section-title">Current System Telemetry</h2>
        {summaryLoading && !summary ? (
          <div className="loading-state">Connecting to EC2...</div>
        ) : (
          <div className="metrics-grid" id="metrics-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
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
              label="System Load (1m)"
              value={summary?.latest_load_1m}
              unit=""
              precision={2}
              description="CPU run queue average"
            />
            <MetricCard
              label="Response Time"
              value={summary?.latest_response_time_ms}
              unit="ms"
              precision={0}
              warningThreshold={1000}
              criticalThreshold={2000}
              description="Application HTTP latency"
            />
          </div>
        )}
      </section>

      {/* Historical Charts */}
      <section className="section" aria-label="Metric Trends">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h2 className="section-title" style={{ margin: 0 }}>Telemetry Trends (Past 60 Minutes)</h2>
          <Link to="/metrics" className="btn btn-secondary btn-sm">
            Detailed History & Process Telemetry &rarr;
          </Link>
        </div>
        {tsLoading && !timeseries ? (
          <div className="loading-state">Loading charts...</div>
        ) : timeseries ? (
          <div className="charts-grid" id="charts-grid">
            <MetricChart
              data={timeseries.data}
              dataKey="cpu_usage"
              label="CPU Usage"
              color="#2563eb"
              warningThreshold={70}
              criticalThreshold={90}
            />
            <MetricChart
              data={timeseries.data}
              dataKey="memory_usage"
              label="Memory Usage"
              color="#7c3aed"
              warningThreshold={75}
              criticalThreshold={90}
            />
            <MetricChart
              data={timeseries.data}
              dataKey="disk_usage"
              label="Disk Usage"
              color="#d97706"
              warningThreshold={80}
              criticalThreshold={90}
            />
            <MetricChart
              data={timeseries.data}
              dataKey="load_1m"
              label="System Load (1m)"
              color="#059669"
              unit=""
              yDomain={[0, 'auto']}
            />
          </div>
        ) : null}
      </section>

      {/* Recent Incidents Section */}
      <section className="section" aria-label="Recent Incidents">
        <div className="section-header-row">
          <h2 className="section-title">Correlated Incidents</h2>
          <Link to="/incidents" className="btn btn-secondary btn-sm" id="view-all-incidents">
            All Incidents ({incidents?.total ?? 0})
          </Link>
        </div>
        {incidentsLoading && !incidents ? (
          <div className="loading-state">Checking incidents...</div>
        ) : incidents && incidents.incidents.length > 0 ? (
          <div className="incidents-list" id="recent-incidents-list">
            {incidents.incidents.map((incident) => (
              <IncidentCard key={incident.id} incident={incident} />
            ))}
          </div>
        ) : (
          <div className="empty-state">
            <div className="empty-icon" style={{ color: '#10b981' }}>✓</div>
            <p className="empty-title">All Systems Healthy</p>
            <p className="empty-desc">No abnormal metric correlations detected on remote EC2 instance.</p>
          </div>
        )}
      </section>
    </main>
  );
};
