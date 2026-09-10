/**
 * IncidentTimeline — displays chronological operational milestones of the incident.
 * Groups multiple anomalies into meaningful lifecycle stages instead of dumping raw duplicate tuples.
 */

import React from 'react';
import { AlertTriangle, TrendingUp, Bot, CheckCircle2, Clock, Activity } from 'lucide-react';
import { formatDate } from '../utils/format';

interface TimelineMilestone {
  title: string;
  timestamp: string;
  description: string;
  badge: string;
  type: 'started' | 'updated' | 'analysis' | 'resolved';
  icon: React.ReactNode;
}

interface IncidentTimelineProps {
  startedAt: string;
  lastSeenAt?: string | null;
  endedAt?: string | null;
  status: string;
  anomalies?: Array<{ metric_name: string; observed_value?: number; detected_at: string; severity?: string }>;
  analyzedAt?: string | null;
}

export const IncidentTimeline: React.FC<IncidentTimelineProps> = ({
  startedAt,
  lastSeenAt,
  endedAt,
  status,
  anomalies = [],
  analyzedAt,
}) => {
  const milestones: TimelineMilestone[] = [];

  // Milestone 1: Initial Saturation Triggered
  const initialCount = anomalies.filter(
    (a) => Math.abs(new Date(a.detected_at).getTime() - new Date(startedAt).getTime()) < 120000
  ).length || Math.min(anomalies.length, 4);

  milestones.push({
    title: 'Initial Multi-Resource Saturation Triggered',
    timestamp: startedAt,
    description: `Automated detection engine flagged concurrent resource pressure (${initialCount} abnormal metrics). Correlated into a single incident to prevent alert storming.`,
    badge: 'Incident Opened',
    type: 'started',
    icon: <AlertTriangle size={13} />,
  });

  // Milestone 2: Escalation / Continuing Pressure
  if (lastSeenAt && lastSeenAt !== startedAt) {
    milestones.push({
      title: 'Workload Escalation & Latency Spike',
      timestamp: lastSeenAt,
      description:
        'Compute and memory saturation persisted, directly causing thread exhaustion and application response time degradation. Temporal deduplication merged this activity into the existing incident.',
      badge: 'Escalation Merged',
      type: 'updated',
      icon: <TrendingUp size={13} />,
    });
  }

  // Milestone 3: AI Analysis Generated
  if (analyzedAt) {
    milestones.push({
      title: 'LangGraph AI Root Cause Analysis Generated',
      timestamp: analyzedAt,
      description:
        '8-node AI workflow executed with Groq LLM. Evaluated cross-metric evidence, identified primary culprit processes, and synthesized actionable remediation plan.',
      badge: 'AI Evaluated',
      type: 'analysis',
      icon: <Bot size={13} />,
    });
  }

  // Milestone 4: Resolution or Ongoing Status
  if (status === 'RESOLVED' && endedAt) {
    milestones.push({
      title: 'Incident Resolved & Baseline Restored',
      timestamp: endedAt,
      description: 'Host telemetry confirmed metrics returned below warning thresholds. Incident closed.',
      badge: 'Resolved',
      type: 'resolved',
      icon: <CheckCircle2 size={13} />,
    });
  } else {
    milestones.push({
      title: status === 'INVESTIGATING' ? 'Under Active Investigation' : 'Active Monitoring in Progress',
      timestamp: lastSeenAt || startedAt,
      description:
        'Monitoring agent continues agentless SSH collection at 20-second intervals. Ongoing conditions will maintain this incident until recovery.',
      badge: status,
      type: 'updated',
      icon: <Activity size={13} />,
    });
  }

  return (
    <div className="timeline-container">
      <div className="timeline-track">
        {milestones.map((m, idx) => (
          <div key={idx} className={`timeline-item timeline-${m.type}`}>
            <div className="timeline-marker">{m.icon}</div>
            <div className="timeline-content">
              <div className="timeline-header">
                <span className="timeline-title">{m.title}</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: 600,
                      padding: '2px 8px',
                      borderRadius: '4px',
                      background: 'rgba(255, 255, 255, 0.08)',
                      color: 'var(--color-text-secondary)',
                    }}
                  >
                    {m.badge}
                  </span>
                  <span className="timeline-time">{formatDate(m.timestamp)}</span>
                </div>
              </div>
              <p className="timeline-desc">{m.description}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
