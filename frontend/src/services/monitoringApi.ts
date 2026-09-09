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

export interface EC2Instance {
  instance_id: string;
  name: string;
  instance_type: string;
  public_dns: string;
  public_ip: string;
  state: string;
  region: string;
  launch_time: string | null;
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

  resetDatabase: async (): Promise<{ success: boolean; message?: string; error?: any }> => {
    const response = await api.post<{ success: boolean; message?: string; error?: any }>('/monitoring/reset-database');
    return response.data;
  },

  configureHost: async (payload: { host: string; username?: string; port?: number }): Promise<any> => {
    const response = await api.post<any>('/monitoring/configure-host', payload);
    return response.data;
  },

  /** Fetch all running EC2 instances from AWS via boto3 */
  discoverInstances: async (): Promise<{ success: boolean; instances: EC2Instance[]; count: number; region?: string; error?: any }> => {
    const response = await api.get('/monitoring/discover-instances');
    return response.data;
  },

  /** Auto-discover first running instance, connect via SSH, and ingest metrics */
  autoConnect: async (): Promise<any> => {
    const response = await api.post('/monitoring/auto-connect');
    return response.data;
  },
};

export default monitoringApi;

