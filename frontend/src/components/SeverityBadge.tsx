/**
 * SeverityBadge — visual severity indicator with color coding.
 */

import React from 'react';
import type { IncidentSeverity, IncidentStatus } from '../types/incident';

interface SeverityBadgeProps {
  severity?: IncidentSeverity | null;
  status?: IncidentStatus | null;
  size?: 'sm' | 'md';
}

const SEVERITY_STYLES: Record<string, string> = {
  CRITICAL: 'badge badge-critical',
  WARNING: 'badge badge-warning',
  NORMAL: 'badge badge-normal',
};

const STATUS_STYLES: Record<string, string> = {
  OPEN: 'badge badge-critical',
  INVESTIGATING: 'badge badge-warning',
  RESOLVED: 'badge badge-normal',
};

export const SeverityBadge: React.FC<SeverityBadgeProps> = ({
  severity,
  status,
  size = 'md',
}) => {
  const label = severity || status || 'UNKNOWN';
  const className = severity
    ? SEVERITY_STYLES[severity] || 'badge badge-normal'
    : STATUS_STYLES[status || ''] || 'badge badge-normal';

  return (
    <span className={`${className} ${size === 'sm' ? 'badge-sm' : ''}`}>
      {label}
    </span>
  );
};
