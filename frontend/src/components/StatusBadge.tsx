/**
 * StatusBadge — visual status indicator for EC2 SSH and System Health.
 */

import React from 'react';

interface StatusBadgeProps {
  status: 'CONNECTED' | 'DEGRADED' | 'UNAVAILABLE' | 'HEALTHY' | 'WARNING' | 'CRITICAL' | string;
  size?: 'sm' | 'md' | 'lg';
}

const BADGE_CLASSES: Record<string, string> = {
  CONNECTED: 'badge-connected',
  HEALTHY: 'badge-connected',
  DEGRADED: 'badge-warning',
  WARNING: 'badge-warning',
  UNAVAILABLE: 'badge-critical',
  CRITICAL: 'badge-critical',
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const normalized = (status || 'UNAVAILABLE').toUpperCase();
  const badgeClass = BADGE_CLASSES[normalized] || 'badge-neutral';

  return (
    <span className={`status-badge status-badge-${size} ${badgeClass}`}>
      <span className="status-dot" />
      {normalized}
    </span>
  );
};
