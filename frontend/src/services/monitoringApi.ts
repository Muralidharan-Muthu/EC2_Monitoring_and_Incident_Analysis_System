/**
 * Monitoring API client for remote EC2 operations.
 */

import api from './api';

export interface SSHStatusData {
  connected: boolean;
  hostname: string | null;
  timestamp: string;
  status: 'CONNECTED' | 'DEGRADED' | 'UNAVAILABLE';
  latency_ms: number | null;
  error: string | null;
}

export interface MonitoringResponse<T> {
  success: boolean;
  data: T;
  incident_detected?: boolean;
  incident_id?: string | null;
  error: { code: string; message: string } | null;
}

export const monitoringApi = {
  getStatus: async (): Promise<MonitoringResponse<SSHStatusData>> => {
    const response = await api.get<MonitoringResponse<SSHStatusData>>('/monitoring/status');
    return response.data;
  },

  getCurrent: async (): Promise<MonitoringResponse<any>> => {
    const response = await api.get<MonitoringResponse<any>>('/monitoring/current');
    return response.data;
  },

  collectNow: async (): Promise<MonitoringResponse<any>> => {
    const response = await api.post<MonitoringResponse<any>>('/monitoring/collect');
    return response.data;
  },
};

export default monitoringApi;
