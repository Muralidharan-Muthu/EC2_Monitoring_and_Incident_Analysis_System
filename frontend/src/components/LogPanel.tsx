/**
 * LogPanel — displays recent system journal logs with priority highlighting.
 */

import React from 'react';

export interface LogItem {
  timestamp: string;
  priority: string;
  message: string;
}

interface LogPanelProps {
  logs: LogItem[];
  loading?: boolean;
}

export const LogPanel: React.FC<LogPanelProps> = ({ logs, loading }) => {
  if (loading) {
    return <div className="loading-state">Loading logs...</div>;
  }

  if (!logs || logs.length === 0) {
    return (
      <div className="empty-state-compact">
        No recent warning/error journal entries found on remote EC2.
      </div>
    );
  }

  return (
    <div className="log-viewer">
      <div className="log-list">
        {logs.map((item, idx) => {
          const isWarn = item.priority === 'warning' || item.priority === 'err' || item.priority === 'error';
          return (
            <div key={idx} className={`log-entry ${isWarn ? 'log-entry-warn' : ''}`}>
              <span className="log-ts">{item.timestamp || '—'}</span>
              <span className={`log-badge log-badge-${item.priority}`}>{item.priority.toUpperCase()}</span>
              <span className="log-msg">{item.message}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
