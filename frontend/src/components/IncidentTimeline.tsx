/**
 * IncidentTimeline — displays chronological timeline of incident lifecycle and anomalies.
 */

import React from 'react';
import { formatDate } from '../utils/format';

interface TimelineEvent {
  title: string;
  timestamp: string;
  description?: string;
  type: 'started' | 'anomaly' | 'updated' | 'analysis' | 'resolved';
}

interface IncidentTimelineProps {
  startedAt: string;
  lastSeenAt?: string | null;
  endedAt?: string | null;
  status: string;
  anomalies?: Array<{ metric_name: string; observed_value?: number; detected_at: string }>;
  analyzedAt?: string | null;
}

export const IncidentTimeline: React.FC<IncidentTimelineProps> = ({
  startedAt,
  lastSeenAt,
  endedAt,
  status,
  anomalies = [],
}) => {
  const events: TimelineEvent[] = [
    {
      title: 'Incident Detected & Opened',
      timestamp: startedAt,
      description: 'Initial correlated anomaly threshold violation triggered incident creation.',
      type: 'started',
    },
  ];

  anomalies.slice(0, 4).forEach((a) => {
    events.push({
      title: `Anomaly: ${a.metric_name}`,
      timestamp: a.detected_at,
      description: a.observed_value != null ? `Observed value: ${a.observed_value}` : undefined,
      type: 'anomaly',
    });
  });

  if (lastSeenAt && lastSeenAt !== startedAt) {
    events.push({
      title: 'Latest Telemetry Activity',
      timestamp: lastSeenAt,
      description: 'Continuing anomalous conditions observed on remote host.',
      type: 'updated',
    });
  }

  if (status === 'RESOLVED' && endedAt) {
    events.push({
      title: 'Incident Auto-Resolved',
      timestamp: endedAt,
      description: 'System returned to healthy operating baselines.',
      type: 'resolved',
    });
  }

  return (
    <div className="timeline-container">
      <div className="timeline-track">
        {events.map((evt, idx) => (
          <div key={idx} className={`timeline-item timeline-${evt.type}`}>
            <div className="timeline-marker" />
            <div className="timeline-content">
              <div className="timeline-header">
                <span className="timeline-title font-bold">{evt.title}</span>
                <span className="timeline-time text-muted">{formatDate(evt.timestamp)}</span>
              </div>
              {evt.description && <p className="timeline-desc text-muted">{evt.description}</p>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
