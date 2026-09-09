/**
 * ProcessTable — displays top CPU and memory consumers from remote EC2 instance.
 */

import React from 'react';
import { formatMetric } from '../utils/format';

export interface ProcessItem {
  pid?: number | null;
  name?: string;
  process_name?: string;
  cpu_percent?: number | null;
  memory_percent?: number | null;
}

interface ProcessTableProps {
  processes: ProcessItem[];
  loading?: boolean;
}

export const ProcessTable: React.FC<ProcessTableProps> = ({ processes, loading }) => {
  if (loading) {
    return <div className="loading-state">Loading processes...</div>;
  }

  if (!processes || processes.length === 0) {
    return <div className="empty-state-compact">No process data available</div>;
  }

  return (
    <div className="table-responsive">
      <table className="data-table">
        <thead>
          <tr>
            <th style={{ width: '80px' }}>PID</th>
            <th>Process Name</th>
            <th style={{ width: '120px', textAlign: 'right' }}>CPU %</th>
            <th style={{ width: '120px', textAlign: 'right' }}>Memory %</th>
          </tr>
        </thead>
        <tbody>
          {processes.map((proc, idx) => {
            const pName = proc.name || proc.process_name || 'unknown';
            const isHighCpu = (proc.cpu_percent ?? 0) > 50;
            const isHighMem = (proc.memory_percent ?? 0) > 50;

            return (
              <tr key={`${proc.pid ?? idx}-${idx}`} className={isHighCpu || isHighMem ? 'row-highlight' : ''}>
                <td className="text-muted">{proc.pid ?? '-'}</td>
                <td className="font-mono text-primary font-bold">{pName}</td>
                <td style={{ textAlign: 'right' }}>
                  <span className={isHighCpu ? 'text-danger font-bold' : ''}>
                    {formatMetric(proc.cpu_percent, '%')}
                  </span>
                </td>
                <td style={{ textAlign: 'right' }}>
                  <span className={isHighMem ? 'text-danger font-bold' : ''}>
                    {formatMetric(proc.memory_percent, '%')}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
