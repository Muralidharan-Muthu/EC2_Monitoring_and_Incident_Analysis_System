/**
 * MetricChart — time-series line chart for a single metric using Recharts.
 */

import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import type { TimeSeriesPoint } from '../types/metric';

interface MetricChartProps {
  data: TimeSeriesPoint[];
  dataKey: keyof TimeSeriesPoint;
  label: string;
  color?: string;
  unit?: string;
  warningThreshold?: number;
  criticalThreshold?: number;
  yDomain?: [number | 'auto', number | 'auto'];
}

function formatTimestamp(ts: string): string {
  const d = new Date(ts);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export const MetricChart: React.FC<MetricChartProps> = ({
  data,
  dataKey,
  label,
  color = '#3b82f6',
  unit = '%',
  warningThreshold,
  criticalThreshold,
  yDomain = [0, 100],
}) => {
  if (!data || data.length === 0) {
    return (
      <div className="chart-container chart-empty">
        <p className="empty-text">No data available</p>
      </div>
    );
  }

  const chartData = data.map((point) => ({
    timestamp: formatTimestamp(point.timestamp),
    value: point[dataKey] as number | null,
  }));

  return (
    <div className="chart-container">
      <h4 className="chart-title">{label}</h4>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={chartData} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="timestamp"
            tick={{ fontSize: 11, fill: '#6b7280' }}
            interval="preserveStartEnd"
          />
          <YAxis
            domain={yDomain}
            tick={{ fontSize: 11, fill: '#6b7280' }}
            tickFormatter={(v) => `${v}${unit}`}
          />
          <Tooltip
            formatter={(value: number) => [`${value?.toFixed(1)}${unit}`, label]}
            labelStyle={{ color: '#374151' }}
            contentStyle={{
              background: '#fff',
              border: '1px solid #e5e7eb',
              borderRadius: 6,
              fontSize: 12,
            }}
          />
          {warningThreshold && (
            <ReferenceLine
              y={warningThreshold}
              stroke="#f59e0b"
              strokeDasharray="4 4"
              label={{ value: 'Warn', position: 'right', fontSize: 10, fill: '#f59e0b' }}
            />
          )}
          {criticalThreshold && (
            <ReferenceLine
              y={criticalThreshold}
              stroke="#ef4444"
              strokeDasharray="4 4"
              label={{ value: 'Crit', position: 'right', fontSize: 10, fill: '#ef4444' }}
            />
          )}
          <Line
            type="monotone"
            dataKey="value"
            stroke={color}
            strokeWidth={2}
            dot={false}
            connectNulls={false}
            activeDot={{ r: 4, fill: color }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};
