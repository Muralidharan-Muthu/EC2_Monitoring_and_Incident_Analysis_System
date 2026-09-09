/**
 * StatusBadge — visual status indicator for EC2 SSH and System Health.
 * Uses Lucide icons for status indicators.
 */

import React from 'react';
import { CheckCircle2, AlertTriangle, XCircle, HelpCircle } from 'lucide-react';

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

  const iconSize = size === 'sm' ? 12 : size === 'lg' ? 15 : 13;

  const renderIcon = () => {
    switch (normalized) {
      case 'CONNECTED':
      case 'HEALTHY':
        return <CheckCircle2 size={iconSize} />;
      case 'DEGRADED':
      case 'WARNING':
        return <AlertTriangle size={iconSize} />;
      case 'UNAVAILABLE':
      case 'CRITICAL':
        return <XCircle size={iconSize} />;
      default:
        return <HelpCircle size={iconSize} />;
    }
  };

  return (
    <span className={`status-badge status-badge-${size} ${badgeClass}`} style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
      {renderIcon()}
      <span>{normalized}</span>
    </span>
  );
};
