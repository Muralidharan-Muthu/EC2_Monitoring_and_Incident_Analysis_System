/**
 * Metrics Page — Historical time-series charts with time range selection.
 */

import React, { useState } from 'react';
import { useTimeseries } from '../hooks/useMetrics';
import { MetricChart } from '../components/MetricChart';

const TIME_RANGES = [
  { label: '15 min', minutes: 15 },
  { label: '1 hour', minutes: 60 },
  { label: '6 hours', minutes: 360 },
  { label: '24 hours', minutes: 1440 },
];

export const Metrics: React.FC = () => {
  const [selectedRange, setSelectedRange] = useState(60);
  const { data, loading, error, refresh } = useTimeseries(selectedRange);

  return (
    <main className="page" id="metrics-page">
      <div className="page-header">
        <h1 className="page-title">Metrics History</h1>
        <p className="page-subtitle">Historical system performance data</p>
      </div>

      {/* Time Range Selector */}
      <div className="time-range-selector" role="group" aria-label="Time range">
        {TIME_RANGES.map(({ label, minutes }) => (
          <button
            key={minutes}
            id={`range-${minutes}`}
            className={`time-range-btn ${selectedRange === minutes ? 'active' : ''}`}
            onClick={() => setSelectedRange(minutes)}
          >
            {label}
          </button>
        ))}
        <button className="btn btn-secondary btn-sm" onClick={refresh} id="refresh-metrics">
          Refresh
        </button>
      </div>

      {error && (
        <div className="alert alert-error" role="alert">
          {error}
        </div>
      )}

      {loading ? (
        <div className="loading-state">Loading metric history...</div>
      ) : data ? (
        <div className="charts-grid" id="metrics-charts-grid">
          <MetricChart
            data={data.data}
            dataKey="cpu_usage"
            label="CPU Usage"
            color="#3b82f6"
            warningThreshold={70}
            criticalThreshold={90}
          />
          <MetricChart
            data={data.data}
            dataKey="memory_usage"
            label="Memory Usage"
            color="#8b5cf6"
            warningThreshold={75}
            criticalThreshold={90}
          />
          <MetricChart
            data={data.data}
            dataKey="disk_usage"
            label="Disk Usage"
            color="#f59e0b"
            warningThreshold={80}
            criticalThreshold={90}
          />
          <MetricChart
            data={data.data}
            dataKey="load_1m"
            label="System Load (1m avg)"
            color="#10b981"
            unit=""
            yDomain={[0, 'auto']}
          />
          <MetricChart
            data={data.data}
            dataKey="response_time_ms"
            label="Response Time"
            color="#f97316"
            unit="ms"
            yDomain={[0, 'auto']}
          />
        </div>
      ) : (
        <div className="empty-state">
          <p className="empty-title">No metric data available</p>
          <p className="empty-desc">Metrics will appear once the monitoring agent is running.</p>
        </div>
      )}
    </main>
  );
};
