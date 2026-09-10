/**
 * MetricChart — Professional, smooth time-series Area chart using Recharts.
 * Features:
 *  - Smooth monotone gradient area fill (Vercel / Datadog aesthetic)
 *  - High-precision telemetry visualization with strict null safety
 *  - Top status header with live metric value, status badge, and peak stats
 *  - Theme-adaptive colors (pristine light & sleek dark mode)
 *  - Glowing illuminated dots for sparse/single points
 *  - Subtle non-intrusive threshold guides
 *  - Glassmorphic custom interactive tooltip
 */

import React, { useId } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import type { TimeSeriesPoint } from '../types/metric';
import { useTheme } from '../context/ThemeContext';

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
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

function formatFullTimestamp(ts: string): string {
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return '';
  }
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
  const { theme } = useTheme();
  const isDark = theme === 'dark';
  const rawId = useId();
  const gradientId = `area-grad-${dataKey}-${rawId.replace(/[^a-zA-Z0-9]/g, '')}`;

  if (!data || data.length === 0) {
    return (
      <div className="chart-container chart-empty">
        <div className="chart-header">
          <div className="chart-title-group">
            <span className="chart-dot" style={{ background: color }} />
            <h4 className="chart-title">{label}</h4>
          </div>
        </div>
        <div className="empty-chart-notice">
          <span>Awaiting metric telemetry from EC2 instance...</span>
        </div>
      </div>
    );
  }

  const chartData = data.map((point) => ({
    timestamp: formatTimestamp(point.timestamp),
    timeFull: formatFullTimestamp(point.timestamp),
    value: point[dataKey] != null ? Number(point[dataKey]) : null,
  }));

  // Calculate live statistics for card header
  const validPoints = chartData.filter((p) => p.value !== null && !isNaN(p.value));
  const latestPoint = validPoints.length > 0 ? validPoints[validPoints.length - 1] : null;
  const latestValue = latestPoint?.value ?? null;
  const maxValue = validPoints.length > 0 ? Math.max(...validPoints.map((p) => p.value as number)) : null;

  let status: 'normal' | 'warning' | 'critical' = 'normal';
  if (latestValue != null) {
    if (criticalThreshold != null && latestValue >= criticalThreshold) {
      status = 'critical';
    } else if (warningThreshold != null && latestValue >= warningThreshold) {
      status = 'warning';
    }
  }

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const pt = payload[0].payload;
      const val = pt.value;
      const isCrit = criticalThreshold && val >= criticalThreshold;
      const isWarn = warningThreshold && val >= warningThreshold;
      const statusText = isCrit ? 'CRITICAL' : isWarn ? 'WARNING' : 'HEALTHY';
      const statusClass = isCrit ? 'tooltip-status-critical' : isWarn ? 'tooltip-status-warning' : 'tooltip-status-healthy';

      return (
        <div className="chart-tooltip-box">
          <div className="chart-tooltip-time">{pt.timeFull || pt.timestamp}</div>
          <div className="chart-tooltip-content">
            <span className="chart-tooltip-swatch" style={{ background: color }} />
            <span className="chart-tooltip-label">{label}:</span>
            <span className="chart-tooltip-val">
              {val != null ? `${Number(val).toFixed(unit === '%' ? 1 : 2)}${unit}` : '-'}
            </span>
          </div>
          {val != null && (
            <span className={`chart-tooltip-badge ${statusClass}`}>
              {statusText}
            </span>
          )}
        </div>
      );
    }
    return null;
  };

  return (
    <div className="chart-container" role="region" aria-label={`${label} Chart`}>
      {/* Sleek Chart Header with Live Metric Stats */}
      <div className="chart-header">
        <div className="chart-title-group">
          <span
            className="chart-dot"
            style={{
              background: color,
              boxShadow: `0 0 8px ${color}88`,
            }}
          />
          <h4 className="chart-title">{label}</h4>
        </div>

        <div className="chart-stats-group">
          {maxValue != null && (
            <span className="chart-stat-peak" title="Peak in time range">
              Peak: <strong>{maxValue.toFixed(unit === '%' ? 1 : 2)}{unit}</strong>
            </span>
          )}
          {latestValue != null ? (
            <span className={`chart-stat-badge stat-badge-${status}`}>
              {latestValue.toFixed(unit === '%' ? 1 : 2)}{unit}
            </span>
          ) : (
            <span className="chart-stat-badge stat-badge-empty">-</span>
          )}
        </div>
      </div>

      {/* Smooth Area Chart */}
      <div className="chart-svg-wrapper">
        <ResponsiveContainer width="100%" height={210}>
          <AreaChart data={chartData} margin={{ top: 12, right: 12, left: -16, bottom: 0 }}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity={isDark ? 0.38 : 0.28} />
                <stop offset="60%" stopColor={color} stopOpacity={isDark ? 0.12 : 0.08} />
                <stop offset="100%" stopColor={color} stopOpacity={0.00} />
              </linearGradient>
            </defs>

            {/* Clean horizontal-only grid lines (removes harsh cage appearance) */}
            <CartesianGrid
              strokeDasharray="4 4"
              stroke={isDark ? 'rgba(255, 255, 255, 0.06)' : 'rgba(0, 0, 0, 0.06)'}
              vertical={false}
            />

            <XAxis
              dataKey="timestamp"
              tick={{ fontSize: 11, fill: isDark ? '#94a3b8' : '#64748b' }}
              axisLine={false}
              tickLine={false}
              minTickGap={24}
              dy={6}
            />

            <YAxis
              domain={yDomain}
              tick={{ fontSize: 11, fill: isDark ? '#94a3b8' : '#64748b' }}
              tickFormatter={(v) => `${v}${unit}`}
              axisLine={false}
              tickLine={false}
              dx={-4}
            />

            <Tooltip content={<CustomTooltip />} />

            {/* Critical Threshold Indicator */}
            {criticalThreshold && (
              <ReferenceLine
                y={criticalThreshold}
                stroke="#ef4444"
                strokeDasharray="4 4"
                strokeWidth={1.5}
                strokeOpacity={isDark ? 0.75 : 0.65}
                label={{
                  value: `Crit: ${criticalThreshold}${unit}`,
                  position: 'insideTopRight',
                  fill: '#ef4444',
                  fontSize: 10,
                  fontWeight: 700,
                  dy: -4,
                }}
              />
            )}

            {/* Warning Threshold Indicator */}
            {warningThreshold && (
              <ReferenceLine
                y={warningThreshold}
                stroke="#f59e0b"
                strokeDasharray="4 4"
                strokeWidth={1.5}
                strokeOpacity={isDark ? 0.7 : 0.6}
                label={{
                  value: `Warn: ${warningThreshold}${unit}`,
                  position: 'insideTopRight',
                  fill: '#f59e0b',
                  fontSize: 10,
                  fontWeight: 700,
                  dy: -4,
                }}
              />
            )}

            {/* Smooth Spline Area with Dynamic Dot Rendering */}
            <Area
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={2.4}
              fill={`url(#${gradientId})`}
              connectNulls={false}
              dot={
                chartData.length <= 12
                  ? {
                      r: chartData.length === 1 ? 5.5 : 3.5,
                      fill: color,
                      stroke: isDark ? '#111827' : '#ffffff',
                      strokeWidth: 2,
                    }
                  : false
              }
              activeDot={{
                r: 6,
                fill: color,
                stroke: isDark ? '#111827' : '#ffffff',
                strokeWidth: 2.5,
              }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};
