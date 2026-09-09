/**
 * MetricCard — displays a single metric value with a label and status indicator.
 */

import React from 'react';

interface MetricCardProps {
  label: string;
  value: number | null | undefined;
  unit?: string;
  warningThreshold?: number;
  criticalThreshold?: number;
  precision?: number;
  description?: string;
}

function getStatusClass(
  value: number | null | undefined,
  warning?: number,
  critical?: number
): string {
  if (value == null) return '';
  if (critical != null && value >= critical) return 'metric-critical';
  if (warning != null && value >= warning) return 'metric-warning';
  return 'metric-normal';
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  unit = '%',
  warningThreshold,
  criticalThreshold,
  precision = 1,
  description,
}) => {
  const statusClass = getStatusClass(value, warningThreshold, criticalThreshold);
  const displayValue =
    value != null ? value.toFixed(precision) : '—';

  return (
    <div className={`metric-card ${statusClass}`} role="region" aria-label={label}>
      <div className="metric-card-label">{label}</div>
      <div className="metric-card-value">
        {displayValue}
        <span className="metric-card-unit">{unit}</span>
      </div>
      {description && <div className="metric-card-desc">{description}</div>}
      {value != null && (
        <div className="metric-card-bar">
          <div
            className={`metric-card-fill ${statusClass}`}
            style={{ width: `${Math.min(value, 100)}%` }}
            role="progressbar"
            aria-valuenow={value}
            aria-valuemin={0}
            aria-valuemax={100}
          />
        </div>
      )}
    </div>
  );
};
