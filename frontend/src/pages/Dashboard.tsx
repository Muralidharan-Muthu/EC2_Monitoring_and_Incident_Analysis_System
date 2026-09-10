/**
 * Dashboard Page — Professional EC2 Monitoring and Incident Analysis.
 * Adheres strictly to zero fake metrics rule (null displays as '-').
 * Replaces emojis with Lucide React icons.
 * Provides live SSH collect, Database Reset, and EC2 Host configuration controls.
 */

import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  RefreshCw,
  Trash2,
  CheckCircle2,
  ArrowRight,
  Server,
  AlertTriangle,
  X,
  Check,
  Zap,
  ChevronDown,
  Wifi,
} from 'lucide-react';
import type { EC2Instance } from '../services/monitoringApi';
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
  const [resetting, setResetting] = useState(false);
  const [collectMessage, setCollectMessage] = useState<string | null>(null);

  // Host configuration state
  const [showHostModal, setShowHostModal] = useState(false);
  const [hostInput, setHostInput] = useState('');
  const [configuringHost, setConfiguringHost] = useState(false);
  const [hostFeedback, setHostFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // EC2 Auto-Discover state
  const [discovering, setDiscovering] = useState(false);
  const [discoveredInstances, setDiscoveredInstances] = useState<EC2Instance[]>([]);
  const [autoConnecting, setAutoConnecting] = useState(false);

  // Auto-refresh every 20 seconds
  useEffect(() => {
    const timer = setInterval(() => {
      refreshSummary();
      refreshTimeseries();
      refreshIncidents();
    }, 20000);
    return () => clearInterval(timer);
  }, [refreshSummary, refreshTimeseries, refreshIncidents]);

  const handleCollectNow = async () => {
    setCollecting(true);
    setCollectMessage(null);
    try {
      const res = await monitoringApi.collectNow();
      if (res.success) {
        setCollectMessage('Live telemetry collected via SSH, persisted to Supabase, and updated.');
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
      setTimeout(() => setCollectMessage(null), 5000);
    }
  };

  const handleResetDatabase = async () => {
    if (!window.confirm('Are you sure you want to delete all monitoring data from the database? This action cannot be undone.')) {
      return;
    }
    setResetting(true);
    setCollectMessage(null);
    try {
      const res = await monitoringApi.resetDatabase();
      if (res.success) {
        setCollectMessage('Database cleared. All metrics, anomalies, and incidents deleted.');
        refreshSummary();
        refreshTimeseries();
        refreshIncidents();
      } else {
        setCollectMessage(res.error?.message || 'Failed to reset database.');
      }
    } catch (err: any) {
      setCollectMessage(err?.message || 'Database reset request failed.');
    } finally {
      setResetting(false);
      setTimeout(() => setCollectMessage(null), 4000);
    }
  };

  const handleConfigureHost = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!hostInput.trim()) return;
    setConfiguringHost(true);
    setHostFeedback(null);
    try {
      const res = await monitoringApi.configureHost({ host: hostInput.trim() });
      if (res.success && res.connected) {
        setHostFeedback({
          type: 'success',
          message: `Connected successfully to ${res.host}! Telemetry ingested.`,
        });
        refreshSummary();
        refreshTimeseries();
        refreshIncidents();
        setTimeout(() => {
          setShowHostModal(false);
          setHostFeedback(null);
          setDiscoveredInstances([]);
        }, 2000);
      } else {
        setHostFeedback({
          type: 'error',
          message: res.error?.message || 'Could not establish SSH connection to this host. Check IP and port 22.',
        });
      }
    } catch (err: any) {
      setHostFeedback({
        type: 'error',
        message: err?.message || 'Host update request failed.',
      });
    } finally {
      setConfiguringHost(false);
    }
  };

  /** Fetch running instances from AWS via boto3 */
  const handleDiscoverInstances = async () => {
    setDiscovering(true);
    setHostFeedback(null);
    try {
      const res = await monitoringApi.discoverInstances();
      if (res.success && res.instances.length > 0) {
        setDiscoveredInstances(res.instances);
        // Auto-select first instance
        const first = res.instances[0];
        setHostInput(first.public_dns || first.public_ip);
        setHostFeedback({
          type: 'success',
          message: `Found ${res.count} running instance${res.count > 1 ? 's' : ''} in ${res.region}. Select one below or click Connect.`,
        });
      } else if (res.success && res.instances.length === 0) {
        setDiscoveredInstances([]);
        setHostFeedback({ type: 'error', message: 'No running EC2 instances found in your AWS account.' });
      } else {
        setHostFeedback({
          type: 'error',
          message: res.error?.message || 'AWS discovery failed. Check AWS credentials in .env.',
        });
      }
    } catch (err: any) {
      setHostFeedback({ type: 'error', message: err?.message || 'Discovery request failed.' });
    } finally {
      setDiscovering(false);
    }
  };

  /** One-click: discover + SSH connect + ingest */
  const handleAutoConnect = async () => {
    setAutoConnecting(true);
    setHostFeedback(null);
    try {
      const res = await monitoringApi.autoConnect();
      if (res.success && res.connected) {
        setHostInput(res.host);
        setHostFeedback({ type: 'success', message: `Auto-connected to ${res.host}! Metrics ingested.` });
        refreshSummary();
        refreshTimeseries();
        refreshIncidents();
        setTimeout(() => {
          setShowHostModal(false);
          setHostFeedback(null);
          setDiscoveredInstances([]);
        }, 2500);
      } else {
        setHostFeedback({
          type: 'error',
          message: res.error?.message || 'Auto-connect failed. Check AWS credentials and Security Group.',
        });
      }
    } catch (err: any) {
      setHostFeedback({ type: 'error', message: err?.message || 'Auto-connect request failed.' });
    } finally {
      setAutoConnecting(false);
    }
  };

  const sshStatus = summary?.ssh_status || 'CONNECTED';
  const systemStatus = summary?.system_status || 'HEALTHY';

  return (
    <main className="page" id="dashboard-page">
      {/* Top Header with SSH Status & Action Buttons */}
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1 className="page-title">EC2 Monitoring & Incident Analysis</h1>
          <p className="page-subtitle">
            Remote agentless telemetry via SSH
            {summary?.hostname && ` · Host: ${summary.hostname}`}
            {summary?.last_metric_at && (
              <> · Last persisted: {new Date(summary.last_metric_at).toLocaleTimeString()}</>
            )}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            id="configure-host-btn"
            className="btn btn-secondary btn-sm"
            onClick={() => {
              setHostInput(summary?.hostname || '');
              setShowHostModal(!showHostModal);
            }}
            title="Configure remote EC2 IP or Public DNS"
          >
            <Server size={14} />
            Configure Host
          </button>
          <button
            id="reset-db-btn"
            className="btn btn-danger btn-sm"
            onClick={handleResetDatabase}
            disabled={resetting || collecting}
            title="Wipe all database records"
          >
            <Trash2 size={14} />
            {resetting ? 'Wiping DB...' : 'Reset DB'}
          </button>
          <button
            id="collect-now-btn"
            className="btn btn-primary"
            onClick={handleCollectNow}
            disabled={collecting || resetting}
          >
            <RefreshCw size={15} className={collecting ? 'spin' : ''} />
            {collecting ? 'Collecting via SSH...' : 'Collect Now'}
          </button>
        </div>
      </div>

      {/* ── Banner: No running EC2 instances found ── */}
      {sshStatus === 'UNAVAILABLE' && !summary?.ec2_host_configured && (
        <div
          className="alert"
          style={{
            background: 'rgba(251, 146, 60, 0.10)',
            border: '1px solid rgba(251, 146, 60, 0.40)',
            color: 'var(--color-warning, #fb923c)',
            marginBottom: '16px',
            borderRadius: '10px',
            padding: '14px 18px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
            <Server size={20} style={{ flexShrink: 0, marginTop: '2px' }} />
            <div style={{ flex: 1 }}>
              <p style={{ margin: '0 0 4px', fontWeight: 700, fontSize: '14px' }}>
                No Running EC2 Instances Found
              </p>
              <p style={{ margin: '0 0 12px', fontSize: '13px', opacity: 0.85 }}>
                Your AWS account has no running instances in <strong>{summary?.aws_region || 'ap-south-1'}</strong>.
                Start your EC2 instance from the AWS Console, then come back — the backend will auto-discover it within seconds.
              </p>
              <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                <a
                  href={`https://${summary?.aws_region || 'ap-south-1'}.console.aws.amazon.com/ec2/home?region=${summary?.aws_region || 'ap-south-1'}#Instances:`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn btn-sm btn-primary"
                  style={{ textDecoration: 'none' }}
                >
                  <Server size={13} />
                  Open EC2 Instances in AWS Console ↗
                </a>
                <button
                  className="btn btn-sm btn-secondary"
                  onClick={handleAutoConnect}
                  disabled={autoConnecting}
                >
                  {autoConnecting
                    ? <><RefreshCw size={13} className="spin" /> Checking...</>
                    : <><RefreshCw size={13} /> Refresh / Retry</>}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Banner: Instance known but SSH unreachable ── */}
      {sshStatus === 'UNAVAILABLE' && summary?.ec2_host_configured && (
        <div
          className="alert"
          style={{
            background: 'rgba(239, 68, 68, 0.12)',
            border: '1px solid rgba(239, 68, 68, 0.35)',
            color: '#f87171',
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertTriangle size={18} />
            <span>
              <strong>EC2 Instance Unreachable via SSH.</strong> If you recently restarted your instance in AWS,
              a new Public IP was assigned. Click <strong>Configure Host</strong> to re-connect,
              or use <strong>Auto-Connect</strong> to discover the new address automatically.
            </span>
          </div>
          <button
            className="btn btn-sm btn-primary"
            style={{ whiteSpace: 'nowrap' }}
            onClick={() => setShowHostModal(true)}
          >
            Configure Host
          </button>
        </div>
      )}

      {/* Host Configuration Panel / Modal */}
      {showHostModal && (
        <div
          className="detail-section"
          style={{
            marginBottom: '20px',
            border: '1px solid var(--color-brand)',
            boxShadow: 'var(--shadow-md)',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h3 className="section-title" style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Server size={16} color="var(--color-brand)" />
              Configure Target AWS EC2 Instance
            </h3>
            <button
              onClick={() => { setShowHostModal(false); setDiscoveredInstances([]); setHostFeedback(null); }}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-secondary)' }}
            >
              <X size={16} />
            </button>
          </div>

          {/* One-click auto-connect row */}
          <div style={{ display: 'flex', gap: '8px', marginBottom: '14px', padding: '10px 14px', background: 'var(--color-surface-2)', borderRadius: '8px', border: '1px solid var(--color-border)', alignItems: 'center', flexWrap: 'wrap' }}>
            <Wifi size={16} color="var(--color-brand)" style={{ flexShrink: 0 }} />
            <span style={{ fontSize: '13px', color: 'var(--color-text-secondary)', flex: 1 }}>
              <strong>Auto-Discover:</strong> Fetch your running instances from AWS automatically — no manual copy-paste needed.
            </span>
            <button
              type="button"
              className="btn btn-sm btn-secondary"
              onClick={handleDiscoverInstances}
              disabled={discovering || autoConnecting || configuringHost}
            >
              {discovering ? <><RefreshCw size={13} className="spin" /> Scanning AWS...</> : <><ChevronDown size={13} /> Discover Instances</>}
            </button>
            <button
              type="button"
              className="btn btn-sm btn-primary"
              onClick={handleAutoConnect}
              disabled={autoConnecting || discovering || configuringHost}
              title="Auto-find first running EC2 instance, SSH connect, and start ingesting"
            >
              {autoConnecting ? <><RefreshCw size={13} className="spin" /> Connecting...</> : <><Zap size={13} /> Auto-Connect</>}
            </button>
          </div>

          {/* Discovered instances dropdown */}
          {discoveredInstances.length > 1 && (
            <div style={{ marginBottom: '12px' }}>
              <label style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginBottom: '4px', display: 'block' }}>Select Instance:</label>
              <select
                className="filter-select"
                style={{ width: '100%', padding: '8px 12px' }}
                value={hostInput}
                onChange={(e) => setHostInput(e.target.value)}
              >
                {discoveredInstances.map((inst) => (
                  <option key={inst.instance_id} value={inst.public_dns || inst.public_ip}>
                    {inst.name} ({inst.instance_id}) — {inst.instance_type} — {inst.public_dns || inst.public_ip}
                  </option>
                ))}
              </select>
            </div>
          )}

          <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginBottom: '10px' }}>
            Or enter your EC2 Public DNS / IP manually (or paste an SSH command):
          </p>
          <form onSubmit={handleConfigureHost} style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            <input
              type="text"
              className="filter-select"
              style={{ flex: 1, minWidth: '280px', padding: '8px 12px' }}
              placeholder="e.g. ec2-13-233-xxx-xxx.ap-south-1.compute.amazonaws.com or 13.233.xxx.xxx"
              value={hostInput}
              onChange={(e) => setHostInput(e.target.value)}
              disabled={configuringHost || autoConnecting}
            />
            <button
              type="submit"
              className="btn btn-primary"
              disabled={configuringHost || autoConnecting || !hostInput.trim()}
            >
              {configuringHost ? (
                <>
                  <RefreshCw size={14} className="spin" />
                  Testing & Connecting...
                </>
              ) : (
                <>
                  <Check size={14} />
                  Connect & Ingest
                </>
              )}
            </button>
          </form>

          {hostFeedback && (
            <div
              style={{
                marginTop: '12px',
                padding: '8px 12px',
                borderRadius: '4px',
                fontSize: '13px',
                background: hostFeedback.type === 'success' ? 'rgba(16, 185, 129, 0.12)' : 'rgba(239, 68, 68, 0.12)',
                color: hostFeedback.type === 'success' ? 'var(--color-healthy)' : 'var(--color-critical)',
                border: `1px solid ${hostFeedback.type === 'success' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
              }}
            >
              {hostFeedback.message}
            </div>
          )}
        </div>
      )}

      {collectMessage && (
        <div className="alert alert-info" role="status" style={{ marginBottom: '16px' }}>
          {collectMessage}
        </div>
      )}

      {/* EC2 Health Banner */}
      <section className="status-banner" style={{ marginBottom: '24px' }}>
        <div className="status-banner-content" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', flexWrap: 'wrap', gap: '16px' }}>
          <div style={{ display: 'flex', gap: '20px', alignItems: 'center', flexWrap: 'wrap' }}>
            <div>
              <div className="status-label">EC2 CONNECTION</div>
              <StatusBadge status={sshStatus} size="lg" />
            </div>
            <div style={{ borderLeft: '1px solid var(--color-border)', paddingLeft: '20px' }}>
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
          Failed to load metrics from database: {summaryError}
        </div>
      )}

      {/* Metric Cards — CPU, Memory, Disk, Load, Response Time */}
      <section className="section" aria-label="Current Metrics">
        <h2 className="section-title">Current System Telemetry (Read from Database)</h2>
        {summaryLoading && !summary ? (
          <div className="loading-state">Querying database...</div>
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
          <Link to="/metrics" className="btn btn-secondary btn-sm" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
            <span>Detailed History</span>
            <ArrowRight size={14} />
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
            <div className="empty-icon" style={{ display: 'flex', justifyContent: 'center' }}>
              <CheckCircle2 size={40} color="var(--color-healthy)" />
            </div>
            <p className="empty-title" style={{ marginTop: '8px' }}>All Systems Healthy</p>
            <p className="empty-desc">No abnormal metric correlations detected on remote EC2 instance.</p>
          </div>
        )}
      </section>
    </main>
  );
};
